from sqlalchemy.orm import Session, joinedload
import models
import schemas
from typing import List
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

def get_lesson_with_navigation(db: Session, lesson_id: int):
    """Находит урок и ID предыдущего/следующего урока в рамках всего курса."""
    current_lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
    if not current_lesson:
        return None

    # Собираем все уроки курса в правильном порядке (по ID модулей, потом по ID уроков)
    all_lessons = db.query(models.Lesson).join(models.Module)\
        .filter(models.Module.course_id == current_lesson.module.course_id)\
        .order_by(models.Module.id, models.Lesson.id).all()
    
    # Находим индекс текущего урока в этом списке
    try:
        current_index = [lesson.id for lesson in all_lessons].index(lesson_id)
    except ValueError:
        return current_lesson # Если что-то пошло не так, вернем просто урок

    # Определяем сос-дей
    prev_lesson = all_lessons[current_index - 1] if current_index > 0 else None
    next_lesson = all_lessons[current_index + 1] if current_index < len(all_lessons) - 1 else None
    
    # Добавляем навигацию к нашему объекту урока
    current_lesson.prev_lesson = prev_lesson
    current_lesson.next_lesson = next_lesson
    
    return current_lesson

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

def get_questions_for_lesson(db: Session, lesson_id: int):
    """Получить все вопросы для урока-квиза."""
    return db.query(models.Question).filter(models.Question.lesson_id == lesson_id).all()

def submit_quiz_answers(db: Session, user_id: int, answers: List[schemas.AnswerIn]):
    """Проверить ответы на квиз и сохранить их."""
    results = []
    correct_count = 0
    total_count = len(answers)

    for answer in answers:
        question = db.query(models.Question).filter(models.Question.id == answer.question_id).first()
        if not question:
            continue # Пропускаем, если вопрос не найден

        correct_answer = question.details.get("correct_answer")
        is_correct = (answer.answer == correct_answer)
        if is_correct:
            correct_count += 1
        
        # Сначала ищем существующий ответ
        db_answer = db.query(models.QuizAnswer).filter_by(
            user_id=user_id, 
            question_id=answer.question_id
        ).first()

        if db_answer:
            # Если ответ уже есть - ОБНОВЛЯЕМ его
            db_answer.selected_answer = answer.answer
            db_answer.is_correct = is_correct
        else:
            # Если ответа нет - СОЗДАЕМ новый
            db_answer = models.QuizAnswer(
                user_id=user_id,
                question_id=answer.question_id,
                selected_answer=answer.answer,
                is_correct=is_correct
            )
            db.add(db_answer)
        
        results.append({
            "question_id": answer.question_id,
            "is_correct": is_correct,
            "correct_answer": correct_answer
        })
    
    # Коммитим все изменения (и новые, и обновленные) один раз
    db.commit()
    return {"results": results, "correct_count": correct_count, "total_count": total_count}

def get_all_completed_lessons_for_user(db: Session, user_id: int):
    """Получить ID ВСЕХ пройденных уроков пользователя."""
    completed_lessons = db.query(models.UserLessonProgress.lesson_id).filter(
        models.UserLessonProgress.user_id == user_id
    ).all()
    return {lesson_id for lesson_id, in completed_lessons}