// frontend/src/pages/QuizLessonPage.js
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import apiClient from './api';

function QuizLessonPage() {
  const { lessonId } = useParams();
  const [lesson, setLesson] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);

  // Загрузка урока и вопросов
  useEffect(() => {
    const fetchQuiz = async () => {
  setLoading(true);
  try {
    const [lessonRes, questionsRes] = await Promise.all([
      apiClient.get(`/lessons/${lessonId}`),
      apiClient.get(`/lessons/${lessonId}/quiz`)
    ]);

    // --- ДОБАВЛЯЕМ ЛОГИРОВАНИЕ ---
    console.log("Lesson Response:", lessonRes.data);
    console.log("Questions Response:", questionsRes.data);
    // -----------------------------

    setLesson(lessonRes.data);
    setQuestions(questionsRes.data);

  } catch (error) {
    // --- ТАКЖЕ ЛОГИРУЕМ ОШИБКУ ---
    console.error("Failed to fetch quiz data:", error);
    // ---------------------------------
  } finally {
    setLoading(false);
  }
};
fetchQuiz();
  }, [lessonId]);

  // Обработчик выбора ответа
  const handleAnswerChange = (questionId, option) => {
    setAnswers(prev => ({ ...prev, [questionId]: option }));
  };

  // Обработчик отправки ответов
  const handleSubmit = async () => {
    const answersPayload = Object.entries(answers).map(([questionId, answer]) => ({
      question_id: parseInt(questionId),
      answer,
    }));

    try {
      const res = await apiClient.post(`/lessons/${lessonId}/quiz/submit`, answersPayload);
      setResults(res.data);
    } catch (error) {
      console.error("Failed to submit quiz", error);
    }
  };

  const handleRetry = () => {
    setAnswers({}); // Очищаем выбранные ответы
    setResults(null); // Сбрасываем результаты
  };

  if (loading) return <div>Загрузка квиза...</div>;

  return (
    <div>
      <h1>{lesson?.title}</h1>
      <p>{lesson?.content}</p>
      <hr />

      {questions.map((q) => (
        <div key={q.id} style={{ marginBottom: '20px' }}>
          <p><strong>{q.question_text}</strong></p>
          {q.details.options.map((option) => (
            <div key={option}>
              <label>
                <input
                  type="radio"
                  name={`question-${q.id}`}
                  value={option}
                  onChange={() => handleAnswerChange(q.id, option)}
                  checked={answers[q.id] === option}
                  disabled={!!results}
                />
                {option}
              </label>
              {results && results.results.find(r => r.question_id === q.id)?.is_correct && answers[q.id] === option && <span style={{ color: 'green' }}> ✔️ Верно</span>}
              {results && !results.results.find(r => r.question_id === q.id)?.is_correct && answers[q.id] === option && <span style={{ color: 'red' }}> ❌ Неверно (Правильный: {results.results.find(r => r.question_id === q.id)?.correct_answer})</span>}
            </div>
          ))}
        </div>
      ))}
      
      {/* --- ИЗМЕНЯЕМ ЛОГИКУ ОТОБРАЖЕНИЯ КНОПОК --- */}
      {!results ? (
        <button onClick={handleSubmit} disabled={Object.keys(answers).length !== questions.length}>
          Проверить
        </button>
      ) : (
        <div>
          <h3>Результат: {results.correct_count} / {results.total_count}</h3>
          {results.correct_count === results.total_count && <p style={{color: 'green'}}>Отлично! Урок пройден!</p>}
          
          {/* Добавляем кнопку "Пройти заново" */}
          <button onClick={handleRetry} style={{ marginTop: '20px' }}>
            Пройти заново
          </button>
        </div>
      )}
    </div>
  );
}

export default QuizLessonPage;