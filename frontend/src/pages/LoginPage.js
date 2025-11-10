// frontend/src/pages/LoginPage.js

import React, { useState } from 'react';
import axios from 'axios';

function LoginPage() {
  // Состояния для email (который в форме называется username) и пароля
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();
    setMessage('');

    // ВАЖНО: FastAPI ожидает данные для OAuth2 в формате form-data,
    // а не JSON. Axios нужно настроить соответствующим образом.
    const params = new URLSearchParams();
    params.append('username', email); // Поле username содержит email
    params.append('password', password);

    try {
      // Отправляем POST-запрос на эндпоинт /login/token
      const response = await axios.post('/login/token', params, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      // В будущем мы будем сохранять этот токен
      console.log(response.data.access_token);
      setMessage('Login successful!');
      // Можно добавить перенаправление на главную страницу
      
    } catch (error) {
      if (error.response && error.response.data) {
        setMessage(`Error: ${error.response.data.detail}`);
      } else {
        setMessage('An unknown error occurred.');
      }
    }
  };

  return (
    <div>
      <h2>Login</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label>Email:</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div style={{ marginTop: '10px' }}>
          <label>Password:</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button type="submit" style={{ marginTop: '10px' }}>Login</button>
      </form>

      {message && <p style={{ marginTop: '20px' }}>{message}</p>}
    </div>
  );
}

export default LoginPage;