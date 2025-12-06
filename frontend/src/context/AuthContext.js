import React, { createContext, useState, useContext, useEffect } from 'react';
import apiClient from '../pages/api';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {

  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null);

  const fetchUser = async () => {
    try {
      const response = await apiClient.get('/users/me');
      setUser(response.data);
    } catch (error) {
      // Если токен невалидный, выходим из системы
      logout();
    }
  };

  // Функция для логина
  const login = async (email, password) => {
    const params = new URLSearchParams();
    params.append('username', email);
    params.append('password', password);

    try {
      const response = await apiClient.post('/login/token', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      if (response.data.access_token) {
        setToken(response.data.access_token);
        localStorage.setItem('token', response.data.access_token);
        await fetchUser();
        return { success: true };
      }
    } catch (error) {
      return { success: false, message: error.response?.data?.detail || 'Login failed' };
    }
  };

  // Функция для выхода из системы
  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
  };

  useEffect(() => {
    if (token) {
      fetchUser();
    }
  }, [token]);

  // Значение, которое будет доступно всем дочерним компонентам
  const value = {
    token,
    user,
    isAuthenticated: !!token, // Простая проверка: если токен есть, пользователь аутентифицирован
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};


export const useAuth = () => {
  return useContext(AuthContext);
};