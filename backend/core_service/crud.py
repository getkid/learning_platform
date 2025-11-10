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