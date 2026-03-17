import axios, { AxiosError } from 'axios'

const BASE_URL = '/api'

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT access token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-refresh on 401
let isRefreshing = false
let failedQueue: Array<{ resolve: (v: string) => void; reject: (e: unknown) => void }> = []

const processQueue = (error: unknown, token: string | null) => {
  failedQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token!)))
  failedQueue = []
}

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as typeof error.config & { _retry?: boolean }
    if (error.response?.status === 401 && !original?._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          original!.headers!['Authorization'] = `Bearer ${token}`
          return api(original!)
        })
      }
      original!._retry = true
      isRefreshing = true
      const refresh = localStorage.getItem('refresh_token')
      if (!refresh) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(error)
      }
      try {
        const { data } = await axios.post(`${BASE_URL}/auth/refresh/`, { refresh })
        localStorage.setItem('access_token', data.access)
        if (data.refresh) localStorage.setItem('refresh_token', data.refresh)
        processQueue(null, data.access)
        original!.headers!['Authorization'] = `Bearer ${data.access}`
        return api(original!)
      } catch (err) {
        processQueue(err, null)
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(err)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  }
)

// Auth
export const authAPI = {
  register: (data: { username: string; email: string; password: string }) =>
    api.post('/auth/register/', data),
  login: (data: { username: string; password: string }) =>
    api.post('/auth/login/', data),
  profile: () => api.get('/auth/profile/'),
}

// Categories
export const categoriesAPI = {
  list: () => api.get('/categories/'),
  create: (data: object) => api.post('/categories/', data),
  update: (id: number, data: object) => api.put(`/categories/${id}/`, data),
  delete: (id: number) => api.delete(`/categories/${id}/`),
}

// Transactions
export const transactionsAPI = {
  list: (params?: object) => api.get('/transactions/', { params }),
  create: (data: object) => api.post('/transactions/', data),
  update: (id: number, data: object) => api.put(`/transactions/${id}/`, data),
  delete: (id: number) => api.delete(`/transactions/${id}/`),
  stats: (params?: object) => api.get('/transactions/stats/', { params }),
  insights: () => api.get('/transactions/insights/'),
}

// Savings
export const savingsAPI = {
  accounts: {
    list: () => api.get('/savings/accounts/'),
    create: (data: object) => api.post('/savings/accounts/', data),
    update: (id: number, data: object) => api.put(`/savings/accounts/${id}/`, data),
    delete: (id: number) => api.delete(`/savings/accounts/${id}/`),
  },
  rule: {
    get: () => api.get('/savings/rule/'),
    save: (data: object) => api.post('/savings/rule/', data),
  },
  summary: (params?: object) => api.get('/savings/summary/', { params }),
  compensation: (params?: object) => api.get('/savings/compensation/', { params }),
}

// Goals
export const goalsAPI = {
  list: (params?: object) => api.get('/goals/', { params }),
  create: (data: object) => api.post('/goals/', data),
  update: (id: number, data: object) => api.put(`/goals/${id}/`, data),
  delete: (id: number) => api.delete(`/goals/${id}/`),
  contribute: (id: number, amount: number) => api.post(`/goals/${id}/contribute/`, { amount }),
  cashflow: (months?: number) => api.get('/goals/cashflow/', { params: { months } }),
}

// Documents
export const documentsAPI = {
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/documents/upload/', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  preview: (id: number) => api.get(`/documents/${id}/preview/`),
  import: (id: number, transactions: object[]) =>
    api.post(`/documents/${id}/import/`, { transactions }),
}
