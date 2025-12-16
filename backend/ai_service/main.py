import pika
import json
import os
import threading
import time
import requests
import ast
from sklearn.metrics import pairwise_distances
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

    

    # 2. Отбираем для анализа только АКТУАЛЬНЫЕ (не пройденные) ошибки
    actual_errors = list(error_logs_collection.find(
        {"user_id": user_id, "lesson_id": {"$nin": list(completed_lessons_ids)}}
    ).sort("timestamp", -1).limit(30))
    
    if len(actual_errors) < 2:
        return {"type": "no_recommendation", "message": "Продолжайте учиться!"}
    
    # --- НАЧАЛО СУПЕР-ОТЛАДКИ ---
    print("\n" + "="*50, flush=True)
    print("AI CLUSTERING ANALYSIS START", flush=True)
    print("="*50, flush=True)

    # 1. Показываем, какие уроки анализируем
    print(f"Found {len(actual_errors)} actual errors for analysis:", flush=True)
    error_lessons_info = {}
    for error in actual_errors:
        lesson_id = error.get('lesson_id')
        lesson_title = error.get('lesson_context', {}).get('lesson_content', 'Unknown')[:30] + '...'
        error_lessons_info[lesson_id] = lesson_title
        print(f"  - Lesson ID: {lesson_id}, Title: '{lesson_title}'", flush=True)

    # 2. Готовим векторы
    vectors = np.array([e["lesson_context"]["content_vector"] for e in actual_errors])
    
    # 3. Вычисляем и печатаем матрицу расстояний
    # Это покажет, насколько "далеки" друг от друга описания уроков
    # Значения близки к 0 = очень похожи. Значения близки к 1 = очень разные.
    distances = pairwise_distances(vectors, metric='cosine')
    print("\nCosine Distance Matrix (0=similar, 1=different):", flush=True)
    print(distances, flush=True)

    # 4. Запускаем кластеризацию
    clustering = DBSCAN(eps=0.6, min_samples=2, metric='cosine').fit(vectors)
    labels = clustering.labels_
    print(f"\nDBSCAN Result (labels for each error): {labels}", flush=True)
    # -1 означает "шум" (не попал ни в один кластер)
    # 0, 1, 2... - это номера кластеров

    unique_labels, counts = np.unique(labels[labels != -1], return_counts=True)
    
    if len(counts) == 0:
        print("No clusters found. All errors considered noise.", flush=True)
        print("="*50 + "\n", flush=True)
        return {"type": "no_recommendation", "message": "Ваши ошибки разнообразны!"}

    # 5. Находим самый большой кластер
    largest_cluster_label = unique_labels[counts.argmax()]
    print(f"Largest cluster is label: {largest_cluster_label}", flush=True)

    cluster_error_indices = [i for i, label in enumerate(labels) if label == largest_cluster_label]
    print(f"Indices of errors in this cluster: {cluster_error_indices}", flush=True)

    cluster_errors = [actual_errors[i] for i in cluster_error_indices]
    
    cluster_lesson_ids = {e['lesson_id'] for e in cluster_errors}
    print(f"Lesson IDs in this cluster: {cluster_lesson_ids}", flush=True)
    print("="*50 + "\n", flush=True)
    # --- КОНЕЦ СУПЕР-ОТЛАДКИ ---  

    # 3. Проводим кластеризацию
    vectors = np.array([e["lesson_context"]["content_vector"] for e in actual_errors])
    clustering = DBSCAN(eps=0.6, min_samples=2, metric='cosine').fit(vectors)
    labels = clustering.labels_

    unique_labels, counts = np.unique(labels[labels != -1], return_counts=True)
    
    if len(counts) == 0:
        return {"type": "no_recommendation", "message": "Ваши ошибки разнообразны, продолжайте пробовать!"}

    largest_cluster_label = unique_labels[counts.argmax()]
    
    # 4. Получаем все записи об ошибках из самого большого кластера
    cluster_errors = [
        actual_errors[i] for i, label in enumerate(labels) if label == largest_cluster_label
    ]
    
    # --- НАЧИНАЕТСЯ ИНТЕЛЛЕКТУАЛЬНЫЙ АНАЛИЗ ---

    # 5. ПУТЬ 2: Пытаемся найти конкретную ошибку в коде (анализ AST)
    latest_error_in_cluster = cluster_errors[0]
    code_analysis = latest_error_in_cluster.get("code_analysis", {})
    lesson_context = latest_error_in_cluster.get("lesson_context", {})
    expected_constructs = lesson_context.get("expected_constructs", [])

    if expected_constructs:
        used_constructs = code_analysis.get("ast_nodes", [])
        for construct in expected_constructs:
            ast_construct_name = construct.capitalize()
            if ast_construct_name not in used_constructs:
                # НАШЛИ ОШИБКУ! Даем рекомендацию по теории
                try:
                    # Запрашиваем инфо о ТЕОРЕТИЧЕСКОМ уроке
                    res = requests.get(f"{CORE_SERVICE_URL}/internal/lessons/{latest_error_in_cluster['lesson_id']}/related-theory")
                    if res.status_code == 200:
                        theory_lesson_info = res.json()
                        # --- ИСПРАВЛЕНИЕ 1: Добавляем print и return ---
                        response_data = {
                            "type": "code_analysis_recommendation",
                            "message": f"Похоже, в этой группе задач вы не использовали ключевую конструкцию '{construct}'. Рекомендуем перечитать теорию:",
                            "lesson": theory_lesson_info
                        }
                        print(f"FINAL RESPONSE (CODE ANALYSIS): {response_data}", flush=True)
                        return response_data
                except requests.RequestException as e:
                    print(f"ERROR fetching related theory: {e}", flush=True)
                    pass # Если не удалось, просто проваливаемся в кластерную рекомендацию

    # 6. ПУТЬ 1: Если конкретных ошибок не найдено, даем общую рекомендацию по кластеру
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
    
    # --- ИСПРАВЛЕНИЕ 2: Убираем лишние переменные, добавляем print и return ---
    response_data = {
        "type": "cluster_recommendation",
        "message": "Наш AI заметил, что у вас возникают трудности с группой похожих по смыслу задач. Рекомендуем поработать над ними еще раз:",
        "lessons": problem_lessons_info
    }
    print(f"FINAL RESPONSE (CLUSTER): {response_data}", flush=True)
    return response_data