import React from 'react';
import { Link, useNavigate } from 'react-router-dom';

// Функция для построения правильной ссылки
const getLessonUrl = (lesson) => {
    if (!lesson) return null;
    if (lesson.lesson_type === 'practice') return `/practice/lessons/${lesson.id}`;
    if (lesson.lesson_type === 'quiz') return `/quiz/lessons/${lesson.id}`;
    return `/lessons/${lesson.id}`;
};

function LessonNavigation({ prevLesson, nextLesson, courseId }) {
    const navigate = useNavigate();
    
    const prevUrl = getLessonUrl(prevLesson);
    const nextUrl = getLessonUrl(nextLesson);

    return (
        <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            marginTop: '40px', 
            borderTop: '1px solid #eee', 
            paddingTop: '20px' 
        }}>
            {prevUrl ? (
                <Link to={prevUrl}>&larr; Предыдущий урок</Link>
            ) : (
                // Если предыдущего урока нет, ссылка ведет на страницу курса
                <Link to={`/courses/${courseId}`}>&larr; К списку уроков</Link>
            )}

            {nextUrl ? (
                <Link to={nextUrl}>Следующий урок &rarr;</Link>
            ) : (
                // Если следующего урока нет
                <span>Это последний урок!</span>
            )}
        </div>
    );
}
export default LessonNavigation;