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
    
    test_result = data.get("test_result", {})
    output_log = test_result.get("output_log")
    # ------------------------------------------------

    if not all([user_id, lesson_id, user_code, lesson_content]):
        print(f"AI Service: Received incomplete data from core_service, skipping.", flush=True)
        return

    # Превращаем описание урока в вектор (эмбеддинг)
    content_vector = model.encode(lesson_content).tolist()

    # Сохраняем ВСЮ информацию об ошибке в MongoDB
    error_logs_collection.insert_one({
        "user_id": user_id,
        "lesson_id": lesson_id,
        "timestamp": time.time(),
        "code_analysis": {
            "user_code": user_code
            # В будущем здесь будет анализ AST
        },
        "lesson_context": lesson_context,
        "test_result": test_result,
    })
    print(f"AI Service: Logged full error details for user {user_id} on lesson {lesson_id}", flush=True)

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

    if len(errors) < 3: # Если ошибок слишком мало, кластеризация бессмысленна
        return {"type": "no_recommendation", "message": "Продолжайте учиться!"}

    # 3. Готовим данные для кластеризации
    vectors = np.array([e["lesson_context"]["content_vector"] for e in errors])
    
    # 4. Запускаем DBSCAN
    # eps - максимальное расстояние между точками в кластере. Подбирается экспериментально.
    # min_samples - минимальное количество точек для образования кластера.
    clustering = DBSCAN(eps=0.5, min_samples=2, metric='cosine').fit(vectors)
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