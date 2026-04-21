import axios from 'axios';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const scrapeTest = async (url) => {
  const response = await api.post('/scrape', { url });
  return response.data;
};

export const getTests = async () => {
  const response = await api.get('/tests');
  return response.data;
};

export const getTest = async (testId) => {
  const response = await api.get(`/tests/${testId}`);
  return response.data;
};

export const submitTest = async (testId, timeSpentSeconds, timeLimitSeconds, answers) => {
  const response = await api.post('/submit', {
    test_id: testId,
    time_spent_seconds: timeSpentSeconds,
    time_limit_seconds: timeLimitSeconds,
    answers,
  });
  return response.data;
};

export const getHistory = async () => {
  const response = await api.get('/history');
  return response.data;
};

export const getMistakes = async (testId = null) => {
  const url = testId ? `/mistakes?test_id=${testId}` : '/mistakes';
  const response = await api.get(url);
  return response.data;
};

export const retestMistakes = async (testId) => {
  const response = await api.post(`/retest/${testId}`);
  return response.data;
};

export default api;