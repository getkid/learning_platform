from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    modules = relationship("Module", back_populates="course")

class Module(Base):
    __tablename__ = "modules"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"))
    course = relationship("Course", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module")

class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=True) # Здесь будет теория или описание задачи
    lesson_type = Column(String, default="text") # Например, 'text', 'video', 'quiz'
    test_code = Column(Text, nullable=True)
    expected_constructs = Column(JSONB, nullable=True)
    starter_code = Column(Text, nullable=True)
    module_id = Column(Integer, ForeignKey("modules.id"))
    module = relationship("Module", back_populates="lessons")

class UserLessonProgress(Base):
    __tablename__ = 'user_lesson_progress'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    lesson_id = Column(Integer, ForeignKey('lessons.id'))
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    lesson = relationship("Lesson")
    
    # Гарантируем, что пара (user_id, lesson_id) будет уникальной
    __table_args__ = (UniqueConstraint('user_id', 'lesson_id', name='_user_lesson_uc'),)

class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey('lessons.id'))
    question_text = Column(Text, nullable=False)
    # Храним варианты ответа и правильный ответ в формате JSON
    # Пример: {"options": ["A", "B", "C"], "correct_answer": "A"}
    details = Column(JSONB, nullable=False)
    
    lesson = relationship("Lesson")

class QuizAnswer(Base):
    __tablename__ = 'quiz_answers'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    question_id = Column(Integer, ForeignKey('questions.id'))
    selected_answer = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=False)

    user = relationship("User")
    question = relationship("Question")
    __table_args__ = (UniqueConstraint('user_id', 'question_id', name='_user_question_uc'),)