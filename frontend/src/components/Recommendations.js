import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

// Создаем отдельный экземпляр axios для AI сервиса.
// Прокси тут не поможет, так как он настроен только на один backend.
const aiApiClient = axios.create({ baseURL: 'http://localhost:8002' });

function Recommendations() {
    // Мы предполагаем, что в AuthContext будет храниться объект user
    const { user } = useAuth();
    const [recommendation, setRecommendation] = useState(null);
    console.log("Recommendations component rendered. User:", user);

    useEffect(() => {
        console.log("useEffect triggered. User:", user);
        // Запрашиваем рекомендации, только если пользователь залогинен
        if (user && user.id) {
            const fetchRecs = async () => {
                console.log(`Fetching recommendations for user ID: ${user.id}`);
                try {
                    const res = await aiApiClient.get(`/recommendations/${user.id}`);
                    console.log("Received recommendation data:", res.data);
                    setRecommendation(res.data);
                } catch (err) {
                    console.error("Не удалось загрузить рекомендации:", err);
                }
            };
            fetchRecs();
        } else {
            console.log("useEffect skipped: no user or user.id");
        }
    }, [user]); // Эффект будет перезапускаться при изменении пользователя (логин/logout)

    console.log("Current recommendation state:", recommendation);

    // Если рекомендаций нет или тип не тот - ничего не показываем
    if (!recommendation || recommendation.type !== 'lesson_recommendation') {
        console.log("Not rendering recommendation block. Reason:", {rec: recommendation});
        return null;
    }

    const { lesson } = recommendation;

    let lessonUrl;
    if (lesson.lesson_type === 'practice') {
        lessonUrl = `/practice/lessons/${lesson.id}`;
    } else if (lesson.lesson_type === 'quiz') {
        lessonUrl = `/quiz/lessons/${lesson.id}`;
    } else {
        lessonUrl = `/lessons/${lesson.id}`;
    }

    return (
        <div style={{ 
            border: '1px solid orange', 
            padding: '15px', 
            marginTop: '20px', 
            backgroundColor: '#fffbeb' 
        }}>
            <strong>Рекомендация:</strong>
            <p style={{ margin: '5px 0 0 0' }}>
                {recommendation.message} <Link to={lessonUrl}>"{lesson.title}"</Link>
            </p>
        </div>
    );
}

export default Recommendations;