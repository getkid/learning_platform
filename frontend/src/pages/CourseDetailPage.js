import React, { useState, useEffect } from 'react';
import { useParams, Link} from 'react-router-dom'; // Хук для получения параметров из URL
import apiClient from './api';

function CourseDetailPage() {
  // useParams() вернет объект { courseId: "1" } из URL /courses/1
  const { courseId } = useParams(); 

  const [course, setCourse] = useState(null); // Состояние для хранения данных одного курса
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchCourse = async () => {
      try {
        // Делаем запрос на новый эндпоинт, используя courseId из URL
        const response = await apiClient.get(`/courses/${courseId}`);
        setCourse(response.data);
        setError('');
      } catch (err) {
        setError('Failed to fetch course details. See console for more info.');
        console.error("Error fetching course details:", err); 
      } finally {
        setLoading(false);
      }
    };

    fetchCourse();
  }, [courseId]); // Эффект будет перезапускаться, если courseId изменится

  if (loading) {
    return <div>Loading course details...</div>;
  }

  if (error) {
    return <div style={{ color: 'red' }}>{error}</div>;
  }

  // Если курс не найден (например, неверный ID в URL)
  if (!course) {
      return <div>Course not found.</div>;
  }

  return (
    <div>
      <h1>{course.title}</h1>
      <p>{course.description}</p>
      <hr />
      <h2>Modules and Lessons</h2>
      {course.modules.length > 0 ? (
        course.modules.map(module => (
          <div key={module.id} style={{ marginBottom: '20px' }}>
            <h3>{module.title}</h3>
            <ul style={{ listStyleType: 'circle', marginLeft: '20px' }}>
              {module.lessons.length > 0 ? (
                module.lessons.map(lesson => (
                  <li key={lesson.id}>
                    {lesson.lesson_type === 'practice' ? (
                        <Link to={`/practice/lessons/${lesson.id}`}>{lesson.title}</Link>
                    ) : (
                        <Link to={`/lessons/${lesson.id}`}>{lesson.title}</Link>
                    )}
                  {lesson.completed && <span style={{ marginLeft: '10px', color: 'green' }}>✔️</span>}
              </li>
          ))
              ) : (
                <li>No lessons in this module.</li>
              )}
            </ul>
          </div>
        ))
      ) : (
        <p>No modules in this course.</p>
      )}
    </div>
  );
}

export default CourseDetailPage;