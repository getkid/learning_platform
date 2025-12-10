// frontend/src/components/Recommendations.js

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

const aiApiClient = axios.create({ baseURL: 'http://localhost:8002' });

function Recommendations() {
    const { user } = useAuth();
    const [recommendation, setRecommendation] = useState(null);

    useEffect(() => {
        if (user && user.id) {
            const fetchRecs = async () => {
                try {
                    const res = await aiApiClient.get(`/recommendations/${user.id}`);
                    console.log("ОТВЕТ ОТ AI SERVICE:", res.data);
                    setRecommendation(res.data);
                } catch (err) {
                    console.error("Не удалось загрузить рекомендации:", err);
                }
            };
            fetchRecs();
        }
    }, [user]);

    if (!recommendation || recommendation.type === 'no_recommendation') {
        return null;
    }

    // --- НОВАЯ УНИВЕРСАЛЬНАЯ ЛОГИКА ---
    const { message } = recommendation;
    // Превращаем оба типа рекомендаций в единый массив уроков
    const lessons = recommendation.type === 'cluster_recommendation' 
        ? recommendation.lessons 
        : [recommendation.lesson]; // Если тип 'lesson_recommendation', создаем массив из одного урока

    // Проверяем, что уроки вообще есть
    if (!lessons || lessons.length === 0) {
        return null;
    }
    // ------------------------------------

    return (
        <div style={{ border: '1px solid orange', padding: '15px', marginTop: '20px', backgroundColor: '#fffbeb', borderRadius: '5px' }}>
            <strong> Рекомендация от AI:</strong>
            <p style={{ margin: '5px 0' }}>{message}</p>
            <ul style={{ margin: '10px 0 0 20px', padding: 0 }}>
                {lessons.map(lesson => {
                    if (!lesson) return null; // Защита от пустых элементов
                    
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