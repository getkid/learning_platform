from sqlalchemy.orm import Session, joinedload
import models
import schemas
from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_email(db: Session, email: str):
    """Найти пользователя по email."""
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    """Создать нового пользователя."""

    hashed_password = pwd_context.hash(user.password)
    
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверить, соответствует ли пароль хэшу."""
    return pwd_context.verify(plain_password, hashed_password)

def get_courses(db: Session, skip: int = 0, limit: int = 100):
    """Получить список всех курсов."""
    return db.query(models.Course).offset(skip).limit(limit).all()

def create_course(db: Session, title: str, description: str):
    """ (Вспомогательная функция) Создать тестовый курс. """
    db_course = models.Course(title=title, description=description)
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course

def get_course_by_id(db: Session, course_id: int):
    """Получить один курс по его ID со всеми модулями и уроками."""
    return db.query(models.Course).filter(models.Course.id == course_id).first()

def get_lesson_by_id(db: Session, lesson_id: int):
    """Получить один урок по его ID."""
    return db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()

def mark_lesson_as_completed(db: Session, user_id: int, lesson_id: int):
    """Отметить урок как пройденный для пользователя."""
    db_progress = db.query(models.UserLessonProgress).filter_by(user_id=user_id, lesson_id=lesson_id).first()
    if not db_progress:
        db_progress = models.UserLessonProgress(user_id=user_id, lesson_id=lesson_id)
        db.add(db_progress)
        db.commit()
        db.refresh(db_progress)
    return db_progress

def get_completed_lessons_for_user(db: Session, user_id: int, course_id: int):
    """Получить ID всех пройденных уроков пользователя в рамках одного курса."""
    completed_lessons = db.query(models.UserLessonProgress.lesson_id)\
        .join(models.Lesson)\
        .filter(
            models.UserLessonProgress.user_id == user_id,
            models.Lesson.module.has(course_id=course_id)
        ).all()
    return {lesson_id for lesson_id, in completed_lessons}