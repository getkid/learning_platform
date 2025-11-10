// frontend/src/App.js

import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import { useAuth } from './context/AuthContext'; // Импортируем хук

import RegisterPage from './pages/RegisterPage';
import LoginPage from './pages/LoginPage';

const HomePage = () => <h1>Home Page</h1>;
const ProfilePage = () => <h1>User Profile Page</h1>; // Добавим заглушку для профиля

function App() {
  const { isAuthenticated, logout } = useAuth(); // Получаем статус и функцию logout

  return (
    <div>
      <nav>
        <Link to="/">Home</Link> | {" "}
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
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Routes>
    </div>
  );
}

export default App;