import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

const BASE_URL = 'http://localhost:8000/api';

const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: add Bearer token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401 with token refresh
let isRefreshing = false;
let failedQueue: Array<{ resolve: (v: unknown) => void; reject: (e: unknown) => void }> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((p) => {
    if (error) p.reject(error);
    else p.resolve(token);
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          if (originalRequest.headers) {
            originalRequest.headers['Authorization'] = `Bearer ${token}`;
          }
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        localStorage.clear();
        window.location.href = '/login';
        return Promise.reject(error);
      }

      try {
        const { data } = await axios.post(`${BASE_URL}/auth/refresh/`, { refresh: refreshToken });
        localStorage.setItem('access_token', data.access);
        api.defaults.headers.common['Authorization'] = `Bearer ${data.access}`;
        processQueue(null, data.access);
        return api(originalRequest);
      } catch (err) {
        processQueue(err, null);
        localStorage.clear();
        window.location.href = '/login';
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

// Auth
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login/', { email, password }),
  register: (email: string, password: string, password2: string, first_name: string, last_name: string) =>
    api.post('/auth/register/', { email, username: email, password, password2, first_name, last_name }),
  refresh: (refresh: string) =>
    api.post('/auth/refresh/', { refresh }),
  me: () => api.get('/auth/me/'),
};

// Categories
export const categoriesApi = {
  list: (params?: Record<string, string>) => api.get('/categories/', { params }),
  create: (data: Record<string, unknown>) => api.post('/categories/', data),
  update: (id: number, data: Record<string, unknown>) => api.put(`/categories/${id}/`, data),
  delete: (id: number) => api.delete(`/categories/${id}/`),
};

// Transactions
export const transactionsApi = {
  list: (params?: Record<string, string>) => api.get('/transactions/', { params }),
  create: (data: Record<string, unknown>) => api.post('/transactions/', data),
  update: (id: number, data: Record<string, unknown>) => api.put(`/transactions/${id}/`, data),
  delete: (id: number) => api.delete(`/transactions/${id}/`),
  stats: (params?: Record<string, string>) => api.get('/transactions/stats/', { params }),
  insights: () => api.get('/transactions/insights/'),
};

// Savings
export const savingsApi = {
  accounts: {
    list: () => api.get('/savings/accounts/'),
    create: (data: Record<string, unknown>) => api.post('/savings/accounts/', data),
    update: (id: number, data: Record<string, unknown>) => api.put(`/savings/accounts/${id}/`, data),
    delete: (id: number) => api.delete(`/savings/accounts/${id}/`),
  },
  rule: {
    get: () => api.get('/savings/rule/'),
    save: (data: Record<string, unknown>) => api.post('/savings/rule/', data),
  },
  summary: () => api.get('/savings/summary/'),
  compensation: () => api.get('/savings/compensation/'),
};

// Goals
export const goalsApi = {
  list: (params?: Record<string, string>) => api.get('/goals/', { params }),
  create: (data: Record<string, unknown>) => api.post('/goals/', data),
  update: (id: number, data: Record<string, unknown>) => api.put(`/goals/${id}/`, data),
  delete: (id: number) => api.delete(`/goals/${id}/`),
  contribute: (id: number, amount: number) => api.post(`/goals/${id}/contribute/`, { amount }),
  cashflow: () => api.get('/goals/cashflow/'),
};

// Documents
export const documentsApi = {
  upload: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/documents/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  preview: (id: number) => api.get(`/documents/${id}/preview/`),
  import: (id: number) => api.post(`/documents/${id}/import/`),
};

export default api;
