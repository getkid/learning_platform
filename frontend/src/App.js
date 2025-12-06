import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import { useAuth } from './context/AuthContext';

import RegisterPage from './pages/RegisterPage';
import LoginPage from './pages/LoginPage';
import CourseListPage from './pages/CourseListPage'; 
import CourseDetailPage from './pages/CourseDetailPage';
import LessonPage from './pages/LessonPage';
import PracticeLessonPage from './pages/PracticeLessonPage';
import QuizLessonPage from './pages/QuizLessonPage';

const HomePage = () => <h1>Home Page</h1>;
const ProfilePage = () => <h1>User Profile Page</h1>;

function App() {
  const { isAuthenticated, logout, user } = useAuth();

  return (
    <div>
      <nav style={{ padding: '10px', background: '#eee' }}>
        <Link to="/">Главная</Link> | {" "}
        <Link to="/courses">Курсы</Link> | {" "}
        {isAuthenticated ? (
          <>
            <span style={{ margin: '0 10px' }}>Привет, {user ? user.email : '...'}!</span> | {" "}
            <Link to="/profile">Профиль</Link> | {" "}
            <button onClick={logout}>Выйти</button>
          </>
        ) : (
          <>
            <Link to="/register">Регистрация</Link> | {" "}
            <Link to="/login">Войти</Link>
          </>
        )}
      </nav>
      <hr />
      <div style={{ padding: '20px' }}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/courses" element={<CourseListPage />} />
          <Route path="/courses/:courseId" element={<CourseDetailPage />} />
          <Route path="/lessons/:lessonId" element={<LessonPage />} />
          <Route path="/practice/lessons/:lessonId" element={<PracticeLessonPage />} />
          <Route path="/quiz/lessons/:lessonId" element={<QuizLessonPage />} /> 
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;