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

    // Если нет рекомендации или тип 'no_recommendation', ничего не рендерим
    if (!recommendation || recommendation.type === 'no_recommendation') {
        return null;
    }

    // --- УНИВЕРСАЛЬНАЯ ЛОГИКА ---
    const { message } = recommendation;
    // Приводим оба типа рекомендаций к единому формату - массиву уроков
    const lessonsToRender = recommendation.type === 'cluster_recommendation' 
        ? recommendation.lessons 
        : [recommendation.lesson];

    if (!lessonsToRender || lessonsToRender.length === 0) {
        return null;
    }
    
    // --- JSX-разметка ---
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
                if (!lesson || !lesson.id) return null;
                
                // --- УПРОЩЕННАЯ И ПРАВИЛЬНАЯ ЛОГИКА ---
                // Просто строим ссылку на основе типа урока, который пришел
                let lessonUrl;
                if (lesson.lesson_type === 'practice') {
                    lessonUrl = `/practice/lessons/${lesson.id}`;
                } else if (lesson.lesson_type === 'quiz') {
                    lessonUrl = `/quiz/lessons/${lesson.id}`;
                } else {
                    lessonUrl = `/lessons/${lesson.id}`;
                }
                // -----------------------------------------
                
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