import apiClient from './client';

export const authAPI = {
  login: (formData) => apiClient.post('/auth/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  }),
  register: (data) => apiClient.post('/auth/register', data),
  getMe: () => apiClient.get('/auth/me'),
};

export const examsAPI = {
  list: () => apiClient.get('/exams'),
  get: (id) => apiClient.get(`/exams/${id}`),
  create: (data) => apiClient.post('/exams', data),
  update: (id, data) => apiClient.put(`/exams/${id}`, data),
  delete: (id) => apiClient.delete(`/exams/${id}`),
};

export const answerKeyAPI = {
  get: (examId) => apiClient.get(`/answer-keys/${examId}`),
  save: (data) => apiClient.post('/answer-keys', data),
  uploadJson: (formData) => apiClient.post('/answer-keys/upload-json', formData),
};

export const omrAPI = {
  uploadSingle: (formData) => apiClient.post('/omr/upload-single', formData),
  uploadBatch: (formData) => apiClient.post('/omr/upload-batch', formData),
  loadDemoSheets: (formData) => apiClient.post('/omr/demo-sheets', formData),
};

export const resultsAPI = {
  getSubmissions: (examId) => apiClient.get(`/results/${examId}`),
  getOverview: (examId) => apiClient.get(`/results/${examId}/overview`),
  getItemAnalysis: (examId) => apiClient.get(`/results/${examId}/item-analysis`),
  getExportCsvUrl: (examId) => `http://localhost:8000/api/v1/results/${examId}/export-csv`,
  getExportExcelUrl: (examId) => `http://localhost:8000/api/v1/results/${examId}/export-excel`,
  getScorecardPdfUrl: (examId, studentId) => `http://localhost:8000/api/v1/results/${examId}/scorecard/${studentId}`,
};
