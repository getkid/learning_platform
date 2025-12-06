from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime.datetime
    class Config:
        from_attributes = True 

class Lesson(BaseModel):
    id: int
    title: str
    content: Optional[str] = None
    lesson_type: str
    completed: bool = False
    test_code: Optional[str] = None 
    class Config:
        from_attributes = True 

class Module(BaseModel):
    id: int
    title: str
    lessons: List[Lesson] = []
    class Config:
        from_attributes = True

class CourseShort(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    class Config:
        from_attributes = True 

class CourseFull(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    modules: List[Module] = []
    class Config:
        from_attributes = True 

# Схема для вариантов ответа
class QuestionOptions(BaseModel):
    options: List[str]

# Схема для вопроса, которую мы отдаем (без правильного ответа!)
class QuestionOut(BaseModel):
    id: int
    question_text: str
    details: QuestionOptions # Используем вложенную схему
    class Config:
        from_attributes = True

# Схема для результата проверки одного ответа
class AnswerResult(BaseModel):
    question_id: int
    is_correct: bool
    correct_answer: str

class AnswerIn(BaseModel):
    question_id: int
    answer: str