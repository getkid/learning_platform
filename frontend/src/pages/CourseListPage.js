import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';

function CourseListPage() {
  // Состояние для хранения списка курсов
  const [courses, setCourses] = useState([]);
  // Состояние для отслеживания загрузки
  const [loading, setLoading] = useState(true);
  // Состояние для хранения возможных ошибок
  const [error, setError] = useState('');

  // useEffect будет выполнен один раз после первого рендера компонента
  useEffect(() => {
    const fetchCourses = async () => {
      try {
        // Отправляем GET-запрос на наш backend
        // Мы не используем прокси, так как это простой GET-запрос.
        // Но лучше сразу привыкать к единому стилю
        const response = await axios.get('/courses');
        setCourses(response.data); // Сохраняем полученные данные в состоянии
        setError('');
      } catch (err) {
        setError('Failed to fetch courses.');
        console.error(err);
      } finally {
        setLoading(false); // Устанавливаем, что загрузка завершена
      }
    };

    fetchCourses();
  }, []); // Пустой массив зависимостей означает, что эффект выполнится только один раз

  // Условный рендеринг в зависимости от состояния
  if (loading) {
    return <div>Loading courses...</div>;
  }

  if (error) {
    return <div style={{ color: 'red' }}>{error}</div>;
  }

  return (
    <div>
      <h2>Available Courses</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        {courses.length > 0 ? (
          courses.map(course => (
            <div key={course.id} style={{ border: '1px solid #ccc', padding: '10px', borderRadius: '5px' }}>
              <h3>
                {/* В будущем ссылка будет вести на страницу курса */}
                <Link to={`/courses/${course.id}`}>{course.title}</Link>
              </h3>
              <p>{course.description}</p>
            </div>
          ))
        ) : (
          <p>No courses available at the moment.</p>
        )}
      </div>
    </div>
  );
}

export default CourseListPage;