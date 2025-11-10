// frontend/src/pages/LoginPage.js

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext'; // Импортируем наш хук

function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  
  const { login } = useAuth(); // Получаем функцию login из контекста
  const navigate = useNavigate(); // Хук для программной навигации

  const handleSubmit = async (event) => {
    event.preventDefault();
    setMessage('');

    const result = await login(email, password); // Вызываем функцию из контекста

    if (result.success) {
      setMessage('Login successful!');
      // После успешного входа перенаправляем на главную страницу
      navigate('/');
    } else {
      setMessage(`Error: ${result.message}`);
    }
  };

  return (
    <div>
      <h2>Login</h2>
      <form onSubmit={handleSubmit}>
        {/* ... ваша JSX-разметка формы остается без изменений ... */}
        <div>
          <label>Email:</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div style={{ marginTop: '10px' }}>
          <label>Password:</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <button type="submit" style={{ marginTop: '10px' }}>Login</button>
      </form>
      {message && <p style={{ marginTop: '20px' }}>{message}</p>}
    </div>
  );
}

export default LoginPage;