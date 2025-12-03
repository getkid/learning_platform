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
        from_attributes = True 

class Lesson(BaseModel):
    id: int
    title: str
    content: Optional[str] = None
    lesson_type: str
    completed: bool = False
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