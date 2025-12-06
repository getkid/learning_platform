import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import apiClient from './api';

// Импортируем редактор и стили для подсветки синтаксиса
import Editor from 'react-simple-code-editor';
import { highlight, languages } from 'prismjs/components/prism-core';
import 'prismjs/components/prism-python';
import 'prismjs/themes/prism.css'; // Можно выбрать и другие темы, например, prism-okaidia

function PracticeLessonPage() {
  const { lessonId } = useParams();

  // Состояния для данных урока
  const [lesson, setLesson] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Состояние для кода, который пишет пользователь
  const [code, setCode] = useState("# Напишите функцию, которая возвращает 'Привет из Python'\ndef get_greeting():\n  # ваш код здесь\n  return \"...\"");
  
  // Состояния для процесса выполнения
  const [output, setOutput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // useRef используется для хранения ID интервала, чтобы мы могли его остановить
  const intervalRef = useRef(null);

  // Функция для проверки статуса выполнения кода на сервере
  const checkStatus = async (submissionId) => {
    try {
      const response = await apiClient.get(`/submissions/${submissionId}`);
      const { status, output } = response.data;

      if (status !== 'pending') {
        // Если задача выполнена (успешно или с ошибкой),
        // останавливаем интервал опроса
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
        // Обновляем вывод и статус кнопки
        setOutput(output);
        setIsSubmitting(false);
      }
    } catch (err) {
      // Если произошла ошибка при получении статуса, тоже останавливаем опрос
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      setOutput('Ошибка при получении результата выполнения.');
      setIsSubmitting(false);
      console.error(err);
    }
  };

  // Функция, вызываемая при нажатии на кнопку "Запустить код"
  const handleSubmitCode = async () => {
    setIsSubmitting(true);
    setOutput('Выполняется...');
    
    try {
      // Отправляем код на сервер и получаем ID задачи
      const response = await apiClient.post(`/lessons/${lessonId}/submit`, { code });
      const { submission_id } = response.data;

      // Запускаем периодический опрос статуса задачи каждые 2 секунды
      intervalRef.current = setInterval(() => {
        checkStatus(submission_id);
      }, 2000);

    } catch (err) {
      setOutput('Ошибка отправки кода на сервер.');
      setIsSubmitting(false);
      console.error(err);
    }
  };

  // Эффект для загрузки данных самого урока (описания задачи)
  useEffect(() => {
    const fetchLesson = async () => {
      setLoading(true);
      try {
        const response = await apiClient.get(`/lessons/${lessonId}`);
        setLesson(response.data);
        // Можно установить начальный код, если он будет приходить с бэкенда
        // setCode(response.data.initial_code || "# Введите ваш код здесь...");
      } catch (err) {
        setError('Не удалось загрузить урок.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchLesson();

    // Функция очистки: будет вызвана, когда пользователь уходит со страницы
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [lessonId]); // Эффект будет перезапущен, если ID урока в URL изменится

  // Отображение состояния загрузки
  if (loading) {
    return <div>Загрузка урока...</div>;
  }

  // Отображение ошибки загрузки
  if (error) {
    return <div style={{ color: 'red' }}>{error}</div>;
  }

  // Основная разметка страницы
  return (
    <div>
      <h1>{lesson?.title}</h1>
      <p>{lesson?.content}</p>
      <hr />

      <h4>Ваш код:</h4>
      <div style={{ border: '1px solid #ccc', marginBottom: '10px', background: '#fdfdfd' }}>
        <Editor
          value={code}
          onValueChange={code => setCode(code)}
          highlight={code => highlight(code, languages.python, 'python')}
          padding={10}
          style={{
            fontFamily: '"Fira code", "Fira Mono", monospace',
            fontSize: 14,
            minHeight: '150px',
          }}
        />
      </div>
      
      <button onClick={handleSubmitCode} disabled={isSubmitting}>
        {isSubmitting ? 'Выполняется...' : 'Запустить код'}
      </button>

      <h4>Вывод:</h4>
      <pre style={{ 
        background: '#f5f5f5', 
        padding: '10px', 
        border: '1px solid #ccc', 
        minHeight: '100px',
        whiteSpace: 'pre-wrap', // Для корректного переноса строк
        wordBreak: 'break-word', // Для переноса длинных строк без пробелов
      }}>
        {output || 'Нажмите "Запустить код", чтобы увидеть результат.'}
      </pre>
    </div>
  );
}

export default PracticeLessonPage;