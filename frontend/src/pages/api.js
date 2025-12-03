import axios from 'axios';


const apiClient = axios.create({
    baseURL: 'http://localhost:8000', 
  });

// Создаем "перехватчик" запросов
apiClient.interceptors.request.use(
  (config) => {
    console.log('Starting Request', config);
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    console.error('Request Error', error);
    return Promise.reject(error);
  }
);

export default apiClient;