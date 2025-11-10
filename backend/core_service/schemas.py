from pydantic import BaseModel, EmailStr
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