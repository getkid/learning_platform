import threading
import pika
import json
import uuid
import os
from typing import List
from datetime import timedelta
import textwrap

from pydantic import BaseModel

from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import models
import schemas
import crud
import security
from config import ACCESS_TOKEN_EXPIRE_MINUTES
from database import engine, SessionLocal, get_db
from mongodb import submissions_collection
from security import get_current_user
from typing import Optional

# --- Блок 2: Создание таблиц и приложения FastAPI ---
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Core Service")

origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

# --- Блок 3: Фоновый слушатель RabbitMQ для результатов ---
def listen_for_results():
    retries = 10
    while retries > 0:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            print("Core service listener: Connected to RabbitMQ.", flush=True)
            break
        except pika.exceptions.AMQPConnectionError:
            print(f"Core service listener: Connection failed. Retrying... ({retries-1} left)", flush=True)
            retries -= 1
            time.sleep(5)
    else:
        print("Core service listener: Could not connect. Exiting thread.", flush=True)
        return

    channel = connection.channel()
    channel.queue_declare(queue='result_queue', durable=True)

    def callback(ch, method, properties, body):
        data = json.loads(body)
        submission_id = data.get('submission_id')
        print(f"--> Core service received result for {submission_id}: STATUS={data.get('status')}", flush=True)
        submissions_collection.update_one(
            {"_id": submission_id},
            {"$set": {"status": data.get('status'), "output": data.get('output')}},
            upsert=True
        )
        if data.get('status') == 'success':
            submission_data = submissions_collection.find_one({"_id": submission_id})
            if submission_data:
                user_id = submission_data.get('user_id')
                lesson_id = submission_data.get('lesson_id')
                if user_id and lesson_id:
                    db = SessionLocal()
                    crud.mark_lesson_as_completed(db, user_id=user_id, lesson_id=lesson_id)
                    db.close()
                    print(f"Lesson {lesson_id} marked as completed for user {user_id}", flush=True)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue='result_queue', on_message_callback=callback)
    print("Core service: Starting to consume results...", flush=True)
    channel.start_consuming()

@app.on_event("startup")
def startup_event():
    # --- ЧАСТЬ 1: Создание тестовых данных ---
    db = SessionLocal()
    first_course = db.query(models.Course).first()
    if not first_course:
        print("База данных курсов пуста. Создаю тестовые данные...", flush=True)
        # --- Курс Python ---
        py_course = models.Course(title="Python для начинающих", description="Изучите основы программирования на Python.")
        py_mod1 = models.Module(title="Модуль 1: Введение", course=py_course)
        py_mod2 = models.Module(title="Модуль 2: Типы данных", course=py_course)
        
        models.Lesson(title="Урок 1.1: Что такое Python?", module=py_mod1, content="Python - это высокоуровневый язык программирования...")
        models.Lesson(title="Урок 1.2: Установка", module=py_mod1, content="Для установки Python перейдите на официальный сайт python.org...")
        
        models.Lesson(
            title="Урок 2.1: Числа и строки (Практика)",
            module=py_mod2,
            content="Ваша задача: вывести на экран строку 'Привет из Python'. Используйте функцию print().",
            lesson_type="practice",
            test_code=textwrap.dedent("""
                import pytest
                from solution import get_greeting

                def test_get_greeting():
                    assert get_greeting() == 'Привет из Python', "Функция должна возвращать строку 'Привет из Python'"
            """)
        )
        # --- Курс JS ---
        js_course = models.Course(title="Продвинутый JavaScript", description="Погружение в концепции JS.")

        db.add_all([py_course, js_course])
        db.commit()
    db.close()

    # --- ЧАСТЬ 2: Запуск фонового слушателя ---
    print("Запускаем фоновый процесс для прослушки RabbitMQ...", flush=True)
    listener_thread = threading.Thread(target=listen_for_results, daemon=True)
    listener_thread.start()

# --- Блок 5: Эндпоинты ---
@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/users/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Регистрирует нового пользователя.
    """

    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    return crud.create_user(db=db, user=user)

@app.get("/users/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(security.get_current_user)):
    return current_user

@app.post("/login/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    

    user = crud.get_user_by_email(db, email=form_data.username)

    if not user or not crud.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/courses", response_model=List[schemas.CourseShort])
def read_courses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    courses = crud.get_courses(db, skip=skip, limit=limit)
    return courses

@app.get("/courses/{course_id}", response_model=schemas.CourseFull)
def read_course(
    course_id: int, 
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(security.try_get_current_user) 
):
    db_course = crud.get_course_by_id(db, course_id=course_id)
    if db_course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    completed_lessons_ids = set()
    if current_user:
        completed_lessons_ids = crud.get_completed_lessons_for_user(db, user_id=current_user.id, course_id=course_id)

    course_data = schemas.CourseFull.from_orm(db_course).model_dump()
    for module in course_data['modules']:
        for lesson in module['lessons']:
            lesson['completed'] = lesson['id'] in completed_lessons_ids

    return course_data

@app.get("/lessons/{lesson_id}", response_model=schemas.Lesson)
def read_lesson(lesson_id: int, db: Session = Depends(get_db)):
    
    db_lesson = crud.get_lesson_by_id(db, lesson_id=lesson_id)
    if db_lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return db_lesson

class SubmissionRequest(BaseModel):
    code: str

@app.post("/lessons/{lesson_id}/submit")
def submit_code(
    lesson_id: int, 
    submission: SubmissionRequest, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user) # <-- Используем зависимость
):
    db_lesson = crud.get_lesson_by_id(db, lesson_id=lesson_id)
    if db_lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()
        channel.queue_declare(queue='submission_queue', durable=True)
        
        submission_id = str(uuid.uuid4())
        submissions_collection.insert_one({
            "_id": submission_id, 
            "status": "pending",
            "user_id": current_user.id,
            "lesson_id": lesson_id
        })

        message = {
            "submission_id": submission_id,
            "lesson_id": lesson_id,
            "code": submission.code,
            "test_code": db_lesson.test_code,
        }

        channel.basic_publish(
            exchange='',
            routing_key='submission_queue',
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
        print(f"--> Task {submission_id} sent to executor", flush=True)
        return {"status": "pending", "submission_id": submission_id}
    except Exception as e:
        print(f"ERROR sending to executor: {e}", flush=True)
        raise HTTPException(status_code=500, detail="Failed to submit code to executor.")

@app.get("/submissions/{submission_id}")
def get_submission_status(submission_id: str, current_user: models.User = Depends(security.get_current_user)):
    # Защищаем и этот эндпоинт, чтобы чужие пользователи не могли смотреть результаты
    result = submissions_collection.find_one({"_id": submission_id})
    if not result:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if result.get('user_id') != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this submission")

    return {
        "submission_id": result["_id"],
        "status": result.get("status"),
        "output": result.get("output")
    }
