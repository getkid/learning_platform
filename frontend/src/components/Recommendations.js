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

            // Запрашиваем рекомендации ОДИН раз при загрузке
            fetchRecs();
        }
    }, [user]); // Зависимость только от user

    if (!recommendation || recommendation.type !== 'lesson_recommendation') {
        return null;
    }

    const { lesson } = recommendation;
    
    let lessonUrl = `/lessons/${lesson.id}`;
    if (lesson.lesson_type === 'practice') {
        lessonUrl = `/practice/lessons/${lesson.id}`;
    } else if (lesson.lesson_type === 'quiz') {
        lessonUrl = `/quiz/lessons/${lesson.id}`;
    }

    return (
        <div style={{ border: '1px solid orange', padding: '15px', marginTop: '20px', backgroundColor: '#fffbeb' }}>
            <strong> Рекомендация от AI:</strong>
            <p style={{ margin: '5px 0 0 0' }}>
                {recommendation.message} <Link to={lessonUrl}>"{lesson.title}"</Link>
            </p>
        </div>
    );
}

export default Recommendations;