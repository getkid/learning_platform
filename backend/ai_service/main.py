import pika
import json
import os
import threading
import time
import requests
from fastapi import FastAPI
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
from fastapi.middleware.cors import CORSMiddleware
from sklearn.cluster import DBSCAN
import numpy as np
from scipy.spatial.distance import cosine

app = FastAPI(title="AI Service")

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. Настройки и подключения ---
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo_db:27017/")
CORE_SERVICE_URL = "http://core_service:8000"


client = MongoClient(MONGO_URL)
db = client.ai_data
error_logs_collection = db.error_logs

# --- 2. Загрузка AI Модели ---
model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
print("AI Service: Model loaded from cache successfully.", flush=True)

# --- 4. Логика обработки событий ---
def process_error_event(data: dict):
    if not model:
        print("AI Service: Model not loaded, cannot process event.", flush=True)
        return

    # --- ИСПРАВЛЕННАЯ ЛОГИКА ИЗВЛЕЧЕНИЯ ДАННЫХ ---
    user_id = data.get("user_id")
    lesson_id = data.get("lesson_id")
    user_code = data.get("user_code")
    
    lesson_context = data.get("lesson_context", {}) # Получаем вложенный объект
    lesson_content = lesson_context.get("lesson_content")
    
    if not lesson_content:
        print("AI Service: lesson_content not found in event, skipping vectorization.", flush=True)
        return
    
    # Генерируем вектор и ДОБАВЛЯЕМ его в lesson_context
    content_vector = model.encode(lesson_content).tolist()
    lesson_context['content_vector'] = content_vector # <-- ДОБАВЛЯЕМ ВЕКТОР ВНУТРЬ

    # Сохраняем новую, полную структуру
    error_logs_collection.insert_one({
        "user_id": data.get("user_id"),
        "lesson_id": data.get("lesson_id"),
        "timestamp": time.time(),
        "code_analysis": {
            "user_code": data.get("user_code")
        },
        "lesson_context": lesson_context, # <-- Сохраняем весь объект
        "test_result": data.get("test_result", {})
    })
    
    print(f"AI Service: Logged full error details for user {data.get('user_id')} on lesson {data.get('lesson_id')}", flush=True)

# --- 5. Слушатель RabbitMQ (запускается в отдельном потоке) ---
def listen_for_events():
    connection = None
    while not connection:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            print("AI Service Listener: Connected to RabbitMQ.", flush=True)
        except pika.exceptions.AMQPConnectionError:
            print("AI Service Listener: Connection failed. Retrying in 5 seconds...", flush=True)
            time.sleep(5)

    channel = connection.channel()
    channel.queue_declare(queue='ai_event_queue', durable=True)

    def callback(ch, method, properties, body):
        try:
            process_error_event(json.loads(body))
        except Exception as e:
            print(f"AI Service: Error processing message: {e}", flush=True)
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue='ai_event_queue', on_message_callback=callback)
    print("AI Service: Waiting for AI events...", flush=True)
    channel.start_consuming()

@app.on_event("startup")
def startup_event():
    listener_thread = threading.Thread(target=listen_for_events, daemon=True)
    listener_thread.start()

@app.get("/recommendations/{user_id}")
def get_recommendations(user_id: int):
    # 1. Получаем ID пройденных уроков из core_service
    completed_lessons_ids = set()
    try:
        res = requests.get(f"{CORE_SERVICE_URL}/internal/users/{user_id}/completed-lessons")
        if res.status_code == 200:
            completed_lessons_ids = set(res.json())
    except requests.RequestException:
        pass # Если core_service недоступен, просто работаем без этой информации

    # 2. Находим ВСЕ актуальные ошибки пользователя
    query = {
        "user_id": user_id,
        "lesson_id": {"$nin": list(completed_lessons_ids)}
    }
    errors = list(error_logs_collection.find(query).sort("timestamp", -1).limit(30))

    if len(errors) >= 2:
        # Возьмем два самых свежих вектора
        vector1 = np.array(errors[0]["lesson_context"]["content_vector"])
        vector2 = np.array(errors[1]["lesson_context"]["content_vector"])
        # Вычисляем косинусное расстояние (0 - идентичны, 1 - полностью разные)
        dist = cosine(vector1, vector2)
        print(f"DEBUG: Cosine distance between last two errors = {dist}", flush=True)
        print(f"DEBUG: DBSCAN 'eps' is set to 0.9. Is distance < eps? {dist < 0.9}", flush=True)
    # --- КОНЕЦ ОТЛАДОЧНОГО БЛОКА ---

    if len(errors) < 3: # Вернем порог в 3, чтобы кластеризация имела смысл
        return {"type": "no_recommendation", "message": "Продолжайте учиться!"}

    vectors = np.array([e["lesson_context"]["content_vector"] for e in errors])
    
    # Оставляем eps=0.9
    clustering = DBSCAN(eps=0.9, min_samples=2, metric='cosine').fit(vectors)
    labels = clustering.labels_

    # 5. Анализируем результаты
    # Находим самый большой кластер (исключая "шум", который DBSCAN помечает как -1)
    unique_labels, counts = np.unique(labels[labels != -1], return_counts=True)
    if len(counts) == 0:
        return {"type": "no_recommendation", "message": "Ваши ошибки разнообразны, продолжайте пробовать!"}

    largest_cluster_label = unique_labels[counts.argmax()]
    
    # Находим все уроки, которые попали в этот кластер
    problem_lesson_ids = [
        errors[i]["lesson_id"] for i, label in enumerate(labels) if label == largest_cluster_label
    ]
    
    # 6. Формируем рекомендацию
    # Для простоты возьмем первый урок из проблемного кластера
    problem_lesson_id = problem_lesson_ids[0]
    try:
        res = requests.get(f"{CORE_SERVICE_URL}/internal/lessons/{problem_lesson_id}")
        lesson_info = res.json()
        return {
            "type": "lesson_recommendation",
            "message": f"Мы заметили, что у вас возникают трудности с задачами, похожими на эту. Попробуйте повторить урок:",
            "lesson": lesson_info
        }
    except Exception:
        # Откатываемся к простому ответу, если что-то пошло не так
        return {"type": "simple_recommendation", "message": f"У вас трудности с уроком #{problem_lesson_id}"}