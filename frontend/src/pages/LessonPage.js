// frontend/src/pages/LessonPage.js

import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';

function LessonPage() {
  // Получаем lessonId из URL (например, "1" из /lessons/1)
  const { lessonId } = useParams();

  const [lesson, setLesson] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchLesson = async () => {
      try {
        // Запрашиваем данные для конкретного урока
        const response = await axios.get(`/lessons/${lessonId}`);
        setLesson(response.data);
        setError('');
      } catch (err) {
        setError('Failed to fetch the lesson.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchLesson();
  }, [lessonId]); // Эффект перезапустится, если мы перейдем на другой урок

  if (loading) {
    return <div>Loading lesson...</div>;
  }

  if (error) {
    return <div style={{ color: 'red' }}>{error}</div>;
  }

  if (!lesson) {
    return <div>Lesson not found.</div>;
  }

  return (
    <div>
      <h1>{lesson.title}</h1>
      <hr />
      {/* Здесь мы отображаем содержимое урока */}
      <div style={{ marginTop: '20px', lineHeight: '1.6' }}>
        <p>{lesson.content}</p>
      </div>
    </div>
  );
}

export default LessonPage;