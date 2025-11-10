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

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    courses = crud.get_courses(db)
    if not courses:
        print("База данных курсов пуста. Создаю тестовые данные...")
        crud.create_course(db, title="Python for Beginners", description="Learn the basics of Python programming.")
        crud.create_course(db, title="Advanced JavaScript", description="Deep dive into JS concepts.")
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

@app.get("/courses", response_model=List[schemas.Course])
def read_courses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Возвращает список всех доступных курсов.
    """
    courses = crud.get_courses(db, skip=skip, limit=limit)
    return courses