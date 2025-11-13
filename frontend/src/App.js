// frontend/src/App.js

import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import { useAuth } from './context/AuthContext';

import RegisterPage from './pages/RegisterPage';
import LoginPage from './pages/LoginPage';
import CourseListPage from './pages/CourseListPage'; 
import CourseDetailPage from './pages/CourseDetailPage';
import LessonPage from './pages/LessonPage';

const HomePage = () => <h1>Home Page</h1>;
const ProfilePage = () => <h1>User Profile Page</h1>;

function App() {
  const { isAuthenticated, logout } = useAuth();

  return (
    <div>
      <nav>
        <Link to="/">Home</Link> | {" "}
        <Link to="/courses">Courses</Link> | {" "} {/* <-- 2. Добавляем ссылку */}
        {isAuthenticated ? (
          <>
            <Link to="/profile">Profile</Link> | {" "}
            <button onClick={logout}>Logout</button>
          </>
        ) : (
          <>
            <Link to="/register">Register</Link> | {" "}
            <Link to="/login">Login</Link>
          </>
        )}
      </nav>
      <hr />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/courses" element={<CourseListPage />} /> {/* <-- 3. Добавляем маршрут */}
        <Route path="/courses/:courseId" element={<CourseDetailPage />} /> {/* Маршрут для будущей страницы курса */}
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/lessons/:lessonId" element={<LessonPage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Routes>
    </div>
  );
}

export default App;