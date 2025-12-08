import React, { createContext, useState, useEffect, useContext, useCallback } from 'react'; // 1. Добавляем useCallback
import apiClient from '../pages/api';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
  }, []);
  
  // 2. Выносим fetchUser за пределы useEffect
  const fetchUser = useCallback(async () => {
    if (localStorage.getItem('token')) {
      try {
        const res = await apiClient.get('/users/me');
        setUser(res.data);
      } catch (error) {
        console.error("Невалидный токен, выход из системы");
        logout(); 
      }
    }
    setLoading(false);
  }, [logout]);

  useEffect(() => {
    fetchUser(); // 3. Просто вызываем ее здесь
  }, [fetchUser]);

  const login = async (email, password) => {
    const params = new URLSearchParams();
    params.append('username', email);
    params.append('password', password);

    try {
      const response = await apiClient.post('/login/token', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      if (response.data.access_token) {
        const token = response.data.access_token;
        setToken(token);
        localStorage.setItem('token', token);
        const userResponse = await apiClient.get('/users/me', {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        setUser(userResponse.data);
        return { success: true };
      }
    } catch (error) {
      return { success: false, message: error.response?.data?.detail || 'Login failed' };
    }
  };

  const value = {
    token,
    user,
    isAuthenticated: !!user,
    loading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  return useContext(AuthContext);
};