// frontend/src/components/Recommendations.js

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

// Создаем отдельный экземпляр axios для AI сервиса
const aiApiClient = axios.create({ baseURL: 'http://localhost:8002' });

function Recommendations() {
    const { user } = useAuth();
    const [recommendation, setRecommendation] = useState(null);

    // Этот useEffect будет отвечать за загрузку данных
    useEffect(() => {
        // Устанавливаем флаг, что компонент активен.
        // Это предотвратит обновление состояния, если пользователь уйдет со страницы
        // до того, как придет ответ от сервера.
        let isMounted = true;

        const fetchRecs = async () => {
            if (user && user.id) {
                try {
                    const res = await aiApiClient.get(`/recommendations/${user.id}`);
                    
                    // Обновляем состояние, только если компонент все еще "жив"
                    if (isMounted) {
                        console.log("ОТВЕТ ОТ AI SERVICE:", res.data);
                        setRecommendation(res.data);
                    }
                } catch (err) {
                    if (isMounted) {
                        console.error("Не удалось загрузить рекомендации:", err);
                    }
                }
            } else {
                // Если пользователя нет, сбрасываем рекомендации
                if (isMounted) {
                    setRecommendation(null);
                }
            }
        };

        fetchRecs();

        // Функция очистки: будет вызвана, когда компонент исчезнет с экрана
        return () => {
            isMounted = false;
        };
    }, [user]); // Запускаем эффект каждый раз, когда меняется объект user

    // --- Логика рендеринга ---

    // 1. Если нет рекомендации или тип 'no_recommendation', ничего не показываем
    if (!recommendation || recommendation.type === 'no_recommendation') {
        return null;
    }

    // 2. Объявляем переменные для универсального рендеринга
    let message;
    let lessonsToRender;

    // 3. Обрабатываем разные типы рекомендаций
    if (recommendation.type === 'cluster_recommendation') {
        message = recommendation.message;
        lessonsToRender = recommendation.lessons;
    } else if (recommendation.type === 'code_analysis_recommendation') {
        message = recommendation.message;
        lessonsToRender = [recommendation.lesson]; // Превращаем один урок в массив
    } else {
        // Если пришел неизвестный тип, ничего не показываем
        return null;
    }

    // 4. Проверяем, что в массиве уроков что-то есть
    if (!lessonsToRender || lessonsToRender.length === 0) {
        return null;
    }
    
    // 5. Возвращаем JSX
    return (
        <div style={{ 
            border: '1px solid orange', 
            padding: '15px', 
            marginTop: '20px', 
            marginBottom: '20px',
            backgroundColor: '#fffbeb',
            borderRadius: '5px' 
        }}>
            <strong>🤖 Рекомендация от AI:</strong>
            <p style={{ margin: '5px 0' }}>{message}</p>
            <ul style={{ margin: '10px 0 0 20px', padding: 0 }}>
                {lessonsToRender.map(lesson => {
                    // Защита от пустых или невалидных данных в массиве
                    if (!lesson || !lesson.id) return null; 
                    
                    // Строим правильную ссылку для каждого урока
                    let lessonUrl = `/lessons/${lesson.id}`;
                    if (lesson.lesson_type === 'practice') {
                        lessonUrl = `/practice/lessons/${lesson.id}`;
                    } else if (lesson.lesson_type === 'quiz') {
                        lessonUrl = `/quiz/lessons/${lesson.id}`;
                    }
                    
                    return (
                        <li key={lesson.id}>
                            <Link to={lessonUrl}>"{lesson.title}"</Link>
                        </li>
                    );
                })}
            </ul>
        </div>
    );
}

export default Recommendations;