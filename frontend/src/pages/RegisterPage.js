import React, { useState } from 'react';
import apiClient from './api';

function RegisterPage() {
  // Создаем состояния для хранения email и пароля
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState(''); 

  // Функция, которая будет вызываться при отправке формы
  const handleSubmit = async (event) => {
    event.preventDefault(); 
    setMessage(''); 

    try {
      // Отправляем POST-запрос на наш backend
      const response = await apiClient.post('/users/register', {
        email: email,
        password: password,
      });

      // Если запрос успешен (статус 201), выводим сообщение
      setMessage(`User ${response.data.email} created successfully!`);
      setEmail(''); 
      setPassword('');

    } catch (error) {
      // Если сервер вернул ошибку, выводим ее
      if (error.response && error.response.data) {
        setMessage(`Error: ${error.response.data.detail}`);
      } else {
        setMessage('An unknown error occurred.');
      }
    }
  };

  return (
    <div>
      <h2>Register</h2>
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
        <button type="submit" style={{ marginTop: '10px' }}>Register</button>
      </form>

      {message && <p style={{ marginTop: '20px' }}>{message}</p>}
    </div>
  );
}

export default RegisterPage;