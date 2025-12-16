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

        if data.get('status') == 'error':
            submission_data = submissions_collection.find_one({"_id": submission_id})
            if submission_data:
                user_id = submission_data.get('user_id')
                lesson_id = submission_data.get('lesson_id')
                user_code = submission_data.get('code') # Получаем код пользователя

                if all([user_id, lesson_id, user_code]):
                    db = SessionLocal()
                    db_lesson = crud.get_lesson_by_id(db, lesson_id=lesson_id)
                    if db_lesson:
                        try:
                            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
                            channel = connection.channel()
                            channel.queue_declare(queue='ai_event_queue', durable=True)
                            
                            ai_message = {
                                "user_id": user_id,
                                "lesson_id": lesson_id,
                                "user_code": user_code,
                                "test_result": { # <-- Передаем результат теста
                                    "output_log": data.get('output')
                                },
                                "lesson_context": { # <-- Передаем контекст урока
                                    "lesson_content": db_lesson.content,
                                    "test_code": db_lesson.test_code,
                                    "expected_constructs": db_lesson.expected_constructs
                                }
                            }
                            
                            channel.basic_publish(
                                exchange='',
                                routing_key='ai_event_queue',
                                body=json.dumps(ai_message),
                                properties=pika.BasicProperties(delivery_mode=2)
                            )
                            connection.close()
                            print(f"Event sent to AI service for user {user_id}, lesson {lesson_id}", flush=True)
                        except Exception as e:
                            print(f"Failed to send event to AI service: {e}", flush=True)
                    db.close()

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
    db = SessionLocal()
    first_course = db.query(models.Course).first()

    if not first_course:
        print("База данных курсов пуста. Создаю тестовые данные...", flush=True)
        
        print("База данных курсов пуста. Создаю расширенный набор тестовых данных...", flush=True)
        
        
        # =================================================================
        # === КУРС 1: PYTHON ДЛЯ НАЧИНАЮЩИХ ===============================
        # =================================================================
        py_course = models.Course(
            title="Python: от новичка до специалиста", 
            description="Комплексный курс, который проведет вас через все основы языка Python, от самых азов до написания собственных сложных функций и работы со структурами данных."
        )

        # --- Модуль 1: Первые шаги и вывод данных ---
        py_mod1 = models.Module(title="Модуль 1: Первые шаги и консольный вывод", course=py_course)
        
        lesson_m1_t1 = models.Lesson(title="Урок 1.1: Что такое Python?", module=py_mod1, content="...", lesson_type="text")
        lesson_m1_t2 = models.Lesson(title="Урок 1.2: Функция print()", module=py_mod1, content="...", lesson_type="text")
        
        lesson_m1_p1 = models.Lesson(
            title="Урок 1.3: Практика - 'Hello, World!'",
            module=py_mod1, content="Напишите программу, которая выводит на экран точную строку 'Hello, Python!'",
            lesson_type="practice", test_code="# test_type: stdout\n# expected_output: Hello, Python!",
            starter_code="# Ваш первый код на Python!\nprint('...')", expected_constructs=["print"]
        )
        
        lesson_m1_p2 = models.Lesson(
            title="Урок 1.4: Практика - Знакомство",
            module=py_mod1, content="Создайте переменную `name` со своим именем и выведите на экран фразу 'Меня зовут [ваше имя]'.",
            lesson_type="practice", test_code="# test_type: stdout\n# expected_output: Меня зовут Алексей",
            starter_code="name = 'Алексей'\nprint(f'Меня зовут {name}')", expected_constructs=["print"]
        )

        quiz_m1 = models.Lesson(title="Урок 1.5: Квиз по основам", module=py_mod1, content="Проверьте свои знания по базовому синтаксису.", lesson_type="quiz")

        # --- Модуль 2: Переменные и типы данных ---
        py_mod2 = models.Module(title="Модуль 2: Переменные и типы данных", course=py_course)
        
        lesson_m2_t1 = models.Lesson(title="Урок 2.1: Числа (int, float) и строки (str)", module=py_mod2, content="...", lesson_type="text")
        
        lesson_m2_p1 = models.Lesson(
            title="Урок 2.2: Практика - Калькулятор возраста",
            module=py_mod2, content="Создайте переменные `current_year = 2025` и `birth_year = 1995`. Вычислите и выведите на экран возраст.",
            lesson_type="practice", test_code="# test_type: stdout\n# expected_output: 30",
            starter_code="current_year = 2025\nbirth_year = 1995\n# Ваш код здесь\nage = ...\nprint(age)"
        )

        quiz_m2 = models.Lesson(title="Урок 2.3: Квиз по типам данных", module=py_mod2, content="Проверьте, как вы разбираетесь в типах.", lesson_type="quiz")

        # --- Модуль 3: Условия (if/else) ---
        py_mod3 = models.Module(title="Модуль 3: Логические условия", course=py_course)

        lesson_m3_t1 = models.Lesson(title="Урок 3.1: Конструкция if-elif-else", module=py_mod3, content="...", lesson_type="text")
        
        # Задача 1 на условия
        practice_m3_p1 = models.Lesson(
            title="Урок 3.2: Практика - Проверка на совершеннолетие",
            module=py_mod3, content="Напишите функцию `check_age`, которая принимает возраст `age` и возвращает строку 'Доступ разрешен', если возраст 18 или больше, и 'Доступ запрещен' в противном случае.",
            lesson_type="practice",
            test_code=textwrap.dedent("""
                import pytest
                from solution import check_age
                def test_check_age():
                    assert check_age(20) == 'Доступ разрешен'
                    assert check_age(18) == 'Доступ разрешен'
                    assert check_age(17) == 'Доступ запрещен'
            """),
            expected_constructs=["if", "return"],
            starter_code="def check_age(age):\n  if age >= 18:\n    # ...\n  else:\n    # ..."
        )

        # Задача 2 на условия (похожая)
        practice_m3_p2 = models.Lesson(
            title="Урок 3.3: Практика - Определение сезона",
            module=py_mod3, content="Создайте функцию `get_season`, которая принимает номер месяца (от 1 до 12) и возвращает строку: 'Зима', 'Весна', 'Лето' или 'Осень'.",
            lesson_type="practice",
            test_code=textwrap.dedent("""
                import pytest
                from solution import get_season
                def test_get_season():
                    assert get_season(1) == 'Зима'
                    assert get_season(4) == 'Весна'
                    assert get_season(7) == 'Лето'
                    assert get_season(10) == 'Осень'
            """),
            expected_constructs=["if", "elif", "return"],
            starter_code="def get_season(month):\n  # Ваш код здесь\n  return '...'"
        )

        # --- Модуль 4: Функции и return (для AI) ---
        py_mod4 = models.Module(title="Модуль 4: Продвинутые функции", course=py_course)
        
        lesson_m4_t1 = models.Lesson(title="Урок 4.1: Основы функций и return", module=py_mod4, content="...", lesson_type="text")
        
        practice_m4_p1 = models.Lesson(
            title="Урок 4.2: Практика - Возврат приветствия",
            module=py_mod4,
            content="Напишите функцию `get_greeting`, которая принимает `name` и ВОЗВРАЩАЕТ строку 'Привет, {name}!'.",
            lesson_type="practice",
            # --- ВОЗВРАЩАЕМ КОД ТЕСТА ---
            test_code=textwrap.dedent("""
                import pytest
                from solution import get_greeting
                def test_greeting():
                    assert get_greeting('Мир') == 'Привет, Мир!'
            """), 
            expected_constructs=["return"],
            starter_code="def get_greeting(name):\n  return f'Привет, {name}!'"
        )

        # Задача 2 на pytest (похожая)
        practice_m4_p2 = models.Lesson(
            title="Урок 4.3: Практика - Сумма чисел",
            module=py_mod4,
            content="Напишите функцию `calculate_sum`, которая принимает список чисел и ВОЗВРАЩАЕТ их сумму.",
            lesson_type="practice",
            # --- ВОЗВРАЩАЕМ КОД ТЕСТА ---
            test_code=textwrap.dedent("""
                import pytest
                from solution import calculate_sum
                def test_sum():
                    assert calculate_sum([1, 2, 3]) == 6
            """), 
            expected_constructs=["return", "for"],
            starter_code="def calculate_sum(numbers):\n  # Ваш код здесь\n  return 0"
        )
        
        # --- Сборка и сохранение ---
        db.add_all([
            py_course, py_mod1, py_mod2, py_mod3, py_mod4,
            lesson_m1_t1, lesson_m1_t2, lesson_m1_p1, lesson_m1_p2, quiz_m1,
            lesson_m2_t1, lesson_m2_p1, quiz_m2,
            lesson_m3_t1, practice_m3_p1, practice_m3_p2,
            lesson_m4_t1, practice_m4_p1, practice_m4_p2
        ])
        db.flush() 

        # --- Вопросы для квизов ---
        # Квиз 1
        db.add_all([
            models.Question(lesson_id=quiz_m1.id, question_text="Какой командой вывести текст?", details={"options": ["print()", "console.log()", "#"], "correct_answer": "print()"}),
            models.Question(lesson_id=quiz_m1.id, question_text="Какой символ для комментария?", details={"options": ["//", "#", "/* */"], "correct_answer": "#"})
        ])
        # Квиз 2
        db.add_all([
            models.Question(lesson_id=quiz_m2.id, question_text="Тип переменной x = 5.0?", details={"options": ["int", "str", "float"], "correct_answer": "float"}),
            models.Question(lesson_id=quiz_m2.id, question_text="Результат '1' + '2'?", details={"options": ["3", "12", "Error"], "correct_answer": "12"})
        ])
        
        db.commit()
    db.close()

    # Запускаем фоновый слушатель
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
    # Используем новую функцию
    db_lesson = crud.get_lesson_with_navigation(db, lesson_id=lesson_id)
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
            "lesson_id": lesson_id,
            "code": submission.code
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

@app.get("/lessons/{lesson_id}/quiz", response_model=List[schemas.QuestionOut])
def get_quiz_questions(lesson_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_lesson = crud.get_lesson_by_id(db, lesson_id=lesson_id)
    if not db_lesson or db_lesson.lesson_type != 'quiz':
        raise HTTPException(status_code=404, detail="Quiz lesson not found")
    return crud.get_questions_for_lesson(db, lesson_id=lesson_id)

@app.post("/lessons/{lesson_id}/quiz/submit")
def submit_quiz(lesson_id: int, answers: List[schemas.AnswerIn], db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Проверяем ответы
    result_data = crud.submit_quiz_answers(db, user_id=current_user.id, answers=answers)
    
    # Если все ответы правильные, считаем урок пройденным
    if result_data["correct_count"] == result_data["total_count"] and result_data["total_count"] > 0:
        crud.mark_lesson_as_completed(db, user_id=current_user.id, lesson_id=lesson_id)
        print(f"Quiz Lesson {lesson_id} marked as completed for user {current_user.id}", flush=True)

    return result_data


@app.get("/internal/lessons/{lesson_id}", response_model=schemas.LessonInfoForAI)
def get_lesson_info_for_internal_use(lesson_id: int, db: Session = Depends(get_db)):
    db_lesson = crud.get_lesson_by_id(db, lesson_id=lesson_id)
    if not db_lesson:
        raise HTTPException(404, "Lesson not found")
    
    return {
        "id": db_lesson.id,
        "title": db_lesson.title,
        "course_id": db_lesson.module.course_id,
        "lesson_type": db_lesson.lesson_type
    }


@app.get("/internal/users/{user_id}/completed-lessons", response_model=List[int])
def get_user_completed_lessons(user_id: int, db: Session = Depends(get_db)):
    completed_ids = crud.get_all_completed_lessons_for_user(db, user_id=user_id)
    return list(completed_ids)