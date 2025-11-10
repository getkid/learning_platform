from pydantic import BaseModel, EmailStr
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
        orm_mode = True 

class LessonBase(BaseModel):
    id: int
    title: str
    class Config:
        orm_mode = True

class ModuleBase(BaseModel):
    id: int
    title: str
    class Config:
        orm_mode = True
        
class CourseBase(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    class Config:
        orm_mode = True

# Полные схемы с вложенными данными
class Module(ModuleBase):
    lessons: List[LessonBase] = []

class Course(CourseBase):
    modules: List[ModuleBase] = []