import axios from 'axios';

// Backend Base URL configuration: prefer VITE_API_URL, fallback to Render in production, localhost in development
const rawUrl = (import.meta.env.VITE_API_URL || (import.meta.env.MODE === 'development' ? 'http://localhost:8000' : 'https://opti-scan.onrender.com')).replace(/\/+$/, '');

// Export both API base URL (guaranteed /api/v1) and root server URL (for static media assets)
export const API_BASE_URL = rawUrl.endsWith('/api/v1') ? rawUrl : `${rawUrl}/api/v1`;
export const SERVER_BASE_URL = rawUrl.replace(/\/api\/v1$/, '');

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
});

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('optiscan_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear token if unauthorized
      localStorage.removeItem('optiscan_token');
    }
    return Promise.reject(error);
  }
);

export default apiClient;
