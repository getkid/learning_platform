from sqlalchemy.orm import Session
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