# backend/core_service/schemas.py

from pydantic import BaseModel, EmailStr
from typing import List, Optional
import datetime

# ===================================================================
# --- Схемы для Пользователя ---
# ===================================================================

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime.datetime

    class Config:
        orm_mode = True

# ===================================================================
# --- схемы для Курсов, Модулей и Уроков ---
# ===================================================================

# --- Схема для одного Урока ---
# Используется внутри схемы Модуля
class Lesson(BaseModel):
    id: int
    title: str
    content: Optional[str] = None # <-- ДОБАВЛЕНО
    class Config:
        orm_mode = True


# --- Схема для одного Модуля ---
# Включает в себя список уроков. Используется внутри полной схемы Курса.
class Module(BaseModel):
    id: int
    title: str
    lessons: List[Lesson] = [] # <-- Здесь список уроков по схеме Lesson

    class Config:
        orm_mode = True


# --- Схема для вывода списка Курсов (краткая информация) ---
# Используется в эндпоинте GET /courses
class CourseShort(BaseModel):
    id: int
    title: str
    description: Optional[str] = None

    class Config:
        orm_mode = True


# --- Схема для вывода одного Курса (полная информация) ---
# Используется в эндпоинте GET /courses/{course_id}
class CourseFull(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    modules: List[Module] = [] # <-- Здесь список модулей по схеме Module (которая включает уроки)

    class Config:
        orm_mode = True