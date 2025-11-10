// frontend/src/context/AuthContext.js

import React, { createContext, useState, useContext } from 'react';
import axios from 'axios';

// 1. Создаем сам контекст
const AuthContext = createContext();

// 2. Создаем "Провайдер" - компонент, который будет предоставлять данные контекста
export const AuthProvider = ({ children }) => {
  // Храним токен в состоянии. Начальное значение берем из localStorage,
  // чтобы пользователь оставался залогиненным после перезагрузки страницы.
  const [token, setToken] = useState(localStorage.getItem('token'));

  // Функция для логина
  const login = async (email, password) => {
    const params = new URLSearchParams();
    params.append('username', email);
    params.append('password', password);

    try {
      const response = await axios.post('/login/token', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      if (response.data.access_token) {
        // Если токен получен, сохраняем его в состоянии и в localStorage
        setToken(response.data.access_token);
        localStorage.setItem('token', response.data.access_token);
        return { success: true };
      }
    } catch (error) {
      // В случае ошибки возвращаем текст ошибки
      return { success: false, message: error.response?.data?.detail || 'Login failed' };
    }
  };

  // Функция для выхода из системы
  const logout = () => {
    // Просто удаляем токен из состояния и localStorage
    setToken(null);
    localStorage.removeItem('token');
  };

  // Значение, которое будет доступно всем дочерним компонентам
  const value = {
    token,
    isAuthenticated: !!token, // Простая проверка: если токен есть, пользователь аутентифицирован
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// 3. Создаем кастомный хук для удобного использования контекста
export const useAuth = () => {
  return useContext(AuthContext);
};