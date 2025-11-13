import os
import pika
import json
import uuid
from pydantic import BaseModel

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm 
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta
from typing import List


import models
import schemas
import crud
from database import SessionLocal, engine, get_db
import security
from config import ACCESS_TOKEN_EXPIRE_MINUTES

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Core Service")

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

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    courses = crud.get_courses(db)
    if not courses:
        print("База данных курсов пуста. Создаю тестовые данные...")
        # Создаем курс Python
        py_course = models.Course(title="Python for Beginners", description="Learn the basics of Python programming.")
        # Создаем модули для него
        py_mod1 = models.Module(title="Module 1: Introduction", course=py_course)
        py_mod2 = models.Module(title="Module 2: Data Types", course=py_course)
        # Создаем уроки для модулей
        py_mod3 = models.Module(title="Module 3: Practice", course=py_course)
        models.Lesson(title="Lesson 1.1: What is Python?", module=py_mod1, content="Python is a high-level, interpreted programming language...")
        models.Lesson(title="Lesson 1.2: Installation", module=py_mod1, content="To install Python, go to the official website python.org...")
        models.Lesson(title="Lesson 2.1: Numbers and Strings", module=py_mod2, content="Python supports various data types, including integers, floats, and strings...")
        models.Lesson(title="Lesson 3.1: First Program", module=py_mod3, lesson_type="practice", content="Write a program that prints 'Hello, World!' to the console.")
        # Создаем курс JS
        js_course = models.Course(title="Advanced JavaScript", description="Deep dive into JS concepts.")

        db.add_all([py_course, js_course])
        db.commit()
    db.close()

@app.get("/health")
def health_check():
    """Простая проверка, что сервис жив."""
    return {"status": "ok", "service": "Core Service"}


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


@app.post("/login/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """
    Аутентифицирует пользователя и возвращает токен доступа.
    """

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
def read_course(course_id: int, db: Session = Depends(get_db)):
    """
    Возвращает полную информацию о курсе по его ID.
    """
    db_course = crud.get_course_by_id(db, course_id=course_id)
    if db_course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return db_course

@app.get("/lessons/{lesson_id}", response_model=schemas.Lesson)
def read_lesson(lesson_id: int, db: Session = Depends(get_db)):
    """
    Возвращает полную информацию об уроке по его ID.
    """
    db_lesson = crud.get_lesson_by_id(db, lesson_id=lesson_id)
    if db_lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return db_lesson

class SubmissionRequest(BaseModel):
    code: str

@app.post("/lessons/{lesson_id}/submit")
def submit_code(lesson_id: int, submission: SubmissionRequest, db: Session = Depends(get_db)):
    db_lesson = crud.get_lesson_by_id(db, lesson_id=lesson_id)
    if db_lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")

    try:
        # Подключаемся к RabbitMQ
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()

        # Объявляем очередь (если ее нет, она создастся)
        channel.queue_declare(queue='submission_queue', durable=True)

        # Формируем сообщение
        submission_id = str(uuid.uuid4())
        message = {
            "submission_id": submission_id,
            "lesson_id": lesson_id,
            "code": submission.code,
        }

        # Отправляем сообщение в очередь
        channel.basic_publish(
            exchange='',
            routing_key='submission_queue',
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE) # Делаем сообщение персистентным
        )
        connection.close()

        # Возвращаем ID отправки, чтобы frontend мог отслеживать результат
        return {"status": "pending", "submission_id": submission_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit code: {e}")