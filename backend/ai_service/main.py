import pika
import json
import os
import threading
import time
import requests
import ast
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

def analyze_code_with_ast(code: str) -> dict:
    """Анализирует код и извлекает из него синтаксические конструкции."""
    analysis = {
        "ast_nodes": set(),
        "has_return": False,
        "has_loops": False,
        "imports": set()
    }
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            node_type = type(node).__name__
            analysis["ast_nodes"].add(node_type)
            
            if isinstance(node, ast.Return):
                analysis["has_return"] = True
            if isinstance(node, (ast.For, ast.While)):
                analysis["has_loops"] = True
            if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    analysis["imports"].add(alias.name)

    except SyntaxError as e:
        analysis["parse_error"] = str(e)
    
    analysis["ast_nodes"] = list(analysis["ast_nodes"])
    analysis["imports"] = list(analysis["imports"])
    
    return analysis

def process_error_event(data: dict):
    if not model:
        print("AI Service: Model not loaded, cannot process event.", flush=True)
        return

    # 1. Извлекаем все данные из входящего сообщения
    user_id = data.get("user_id")
    lesson_id = data.get("lesson_id")
    user_code = data.get("user_code")
    lesson_context = data.get("lesson_context", {})
    lesson_content = lesson_context.get("lesson_content")
    
    # 2. Проверяем, что все критически важные данные на месте
    if not all([user_id, lesson_id, user_code, lesson_content]):
        print(f"AI Service: Received incomplete data from core_service, skipping.", flush=True)
        return

    # 3. Выполняем анализ кода с помощью AST
    code_analysis_results = analyze_code_with_ast(user_code)
    
    # 4. Генерируем вектор для описания урока
    content_vector = model.encode(lesson_content).tolist()
    lesson_context['content_vector'] = content_vector

    # 5. Сохраняем в MongoDB полную, обогащенную структуру
    error_logs_collection.insert_one({
        "user_id": user_id,
        "lesson_id": lesson_id,
        "timestamp": time.time(),
        "code_analysis": code_analysis_results,  # <-- Результаты AST-анализа
        "lesson_context": lesson_context,        # <-- Контекст урока с вектором
        "test_result": data.get("test_result", {}) # <-- Результаты теста
    })
    
    print(f"AI Service: Logged full error details with AST analysis for user {user_id} on lesson {lesson_id}", flush=True)

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

# backend/ai_service/main.py

@app.get("/recommendations/{user_id}")
def get_recommendations(user_id: int):
    # 1. Получаем ID пройденных уроков
    completed_lessons_ids = set()
    try:
        res = requests.get(f"{CORE_SERVICE_URL}/internal/users/{user_id}/completed-lessons")
        if res.status_code == 200:
            completed_lessons_ids = set(res.json())
    except requests.RequestException as e:
        print(f"AI Service: Could not fetch completed lessons. Error: {e}", flush=True)

    # 2. Находим ВСЕ недавние ошибки пользователя
    all_recent_errors = list(error_logs_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(30))

    # 3. Отбираем для анализа только АКТУАЛЬНЫЕ (не пройденные) ошибки
    actual_errors = [e for e in all_recent_errors if e.get('lesson_id') not in completed_lessons_ids]
    
    if len(actual_errors) < 2:
        return {"type": "no_recommendation", "message": "Продолжайте учиться!"}

    # 4. Проводим кластеризацию
    vectors = np.array([e["lesson_context"]["content_vector"] for e in actual_errors])
    clustering = DBSCAN(eps=0.9, min_samples=2, metric='cosine').fit(vectors)
    labels = clustering.labels_

    unique_labels, counts = np.unique(labels[labels != -1], return_counts=True)
    
    if len(counts) == 0:
        return {"type": "no_recommendation", "message": "Ваши ошибки разнообразны, продолжайте пробовать!"}

    largest_cluster_label = unique_labels[counts.argmax()]
    
    # 5. Получаем все записи об ошибках из самого большого кластера
    cluster_errors = [
        actual_errors[i] for i, label in enumerate(labels) if label == largest_cluster_label
    ]
    
    # --- НАЧАЛО ОТЛАДОЧНОГО БЛОКА ---
    print("\n--- AI DEBUG START ---", flush=True)
    
    latest_error_in_cluster = cluster_errors[0]
    print(f"Latest error in cluster is for lesson ID: {latest_error_in_cluster.get('lesson_id')}", flush=True)

    code_analysis = latest_error_in_cluster.get("code_analysis", {})
    lesson_context = latest_error_in_cluster.get("lesson_context", {})
    expected_constructs = lesson_context.get("expected_constructs", [])
    used_constructs = code_analysis.get("ast_nodes", [])

    print(f"Expected constructs: {expected_constructs}", flush=True)
    print(f"Used constructs (from AST): {used_constructs}", flush=True)
    # --- КОНЕЦ ОТЛАДОЧНОГО БЛОКА ---

    # 6. ПУТЬ 2: Пытаемся найти конкретную ошибку в коде (анализ AST)
    if expected_constructs:
        found_specific_error = False
        for construct in expected_constructs:
            ast_construct_name = construct.capitalize()
            
            print(f"Checking for '{ast_construct_name}'... Is it in used constructs? {'Yes' if ast_construct_name in used_constructs else 'NO!'}", flush=True)

            if ast_construct_name not in used_constructs:
                found_specific_error = True
                print(f"FOUND SPECIFIC ERROR: User did not use '{construct}'", flush=True)
                try:
                    print("Attempting to fetch related theory...", flush=True)
                    res = requests.get(f"{CORE_SERVICE_URL}/internal/lessons/{latest_error_in_cluster['lesson_id']}")
                    print(f"Core service response status: {res.status_code}", flush=True)
                    if res.status_code == 200:
                        theory_lesson_info = res.json()
                        print("--- AI DEBUG END ---\n", flush=True)
                        return {
                            "type": "code_analysis_recommendation",
                            "message": f"Похоже, в этой группе задач вы не использовали ключевую конструкцию '{construct}'. Рекомендуем перечитать теорию:",
                            "lesson": theory_lesson_info
                        }
                except requests.RequestException:
                    pass # Если не удалось, просто проваливаемся в кластерную рекомендацию
                break # Выходим из цикла, так как нашли первую ошибку
        
        if not found_specific_error:
            print("No specific code error found. Falling back to cluster recommendation.", flush=True)

    print("--- AI DEBUG END ---\n", flush=True)
    # -------------------------------------

    # 7. ПУТЬ 1: Если конкретных ошибок не найдено, даем общую рекомендацию по кластеру
    problem_lesson_ids = {e["lesson_id"] for e in cluster_errors}
    
    problem_lessons_info = []
    for lesson_id in problem_lesson_ids:
        try:
            res = requests.get(f"{CORE_SERVICE_URL}/internal/lessons/{lesson_id}")
            if res.status_code == 200:
                problem_lessons_info.append(res.json())
        except requests.RequestException:
            continue
    
    if not problem_lessons_info:
         return {"type": "no_recommendation", "message": "Не удалось получить детали проблемных уроков."}
    
    response_data = {
        "type": "cluster_recommendation",
        "message": "Мы заметили...",
        "lessons": problem_lessons_info
    }

    print(f"FINAL RESPONSE: {response_data}", flush=True)

    return response_data