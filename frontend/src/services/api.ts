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
  profile_update: (data: object) => api.patch('/auth/profile/', data),
  changePassword: (current_password: string, new_password: string) =>
    api.post('/auth/change-password/', { current_password, new_password }),
  completeOnboarding: (data: object) =>
    api.post('/auth/complete-onboarding/', data),
}

// Categories
export const categoriesAPI = {
  list: () => api.get('/categories/'),
  create: (data: object) => api.post('/categories/', data),
  update: (id: number, data: object) => api.put(`/categories/${id}/`, data),
  delete: (id: number) => api.delete(`/categories/${id}/`),
  mergeInto: (sourceId: number, targetId: number) => api.post(`/categories/${sourceId}/merge_into/`, { target_id: targetId }),
}

// Category rules
export const categoryRulesAPI = {
  list: () => api.get('/category-rules/'),
  create: (data: object) => api.post('/category-rules/', data),
  delete: (id: number) => api.delete(`/category-rules/${id}/`),
}

// Envelopes (YNAB-style per-category budgets)
export const envelopesAPI = {
  list: (month: string) => api.get('/envelopes/', { params: { month } }),
  upsert: (category: number, month: string, allocated: number) =>
    api.post('/envelopes/upsert/', { category, month, allocated }),
}

// Transactions
export const transactionsAPI = {
  list: (params?: object) => api.get('/transactions/', { params }),
  create: (data: object) => api.post('/transactions/', data),
  update: (id: number, data: object) => api.put(`/transactions/${id}/`, data),
  patch: (id: number, data: object) => api.patch(`/transactions/${id}/`, data),
  delete: (id: number) => api.delete(`/transactions/${id}/`),
  stats: (params?: object) => api.get('/transactions/stats/', { params }),
  insights: () => api.get('/transactions/insights/'),
  recurringDetected: () => api.get('/transactions/recurring_detected/'),
  recurringList: () => api.get('/transactions/', { params: { is_recurring: 'true', page_size: 200 } }),
  scoreHistory: () => api.get('/transactions/score_history/'),
  weekdayStats: (months = 3) => api.get(`/transactions/weekday_stats/?months=${months}`),
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

// Bank Accounts
export const accountsAPI = {
  list: () => api.get('/accounts/'),
  create: (data: object) => api.post('/accounts/', data),
  update: (id: number, data: object) => api.put(`/accounts/${id}/`, data),
  delete: (id: number) => api.delete(`/accounts/${id}/`),
  summary: () => api.get('/accounts/summary/'),
  history: (id: number) => api.get(`/accounts/${id}/history/`),
}

// Notifications
export const notificationsAPI = {
  list: () => api.get('/notifications/'),
  unreadCount: () => api.get('/notifications/unread_count/'),
  markRead: (id: number) => api.post(`/notifications/${id}/mark_read/`),
  markAllRead: () => api.post('/notifications/mark_all_read/'),
}

// Forecast
export const forecastAPI = {
  budget: (months = 6) => api.get(`/forecast/budget/?months=${months}`),
  simulate: (data: { reductions: Record<string, number>; extra_savings: number }) =>
    api.post('/forecast/simulate/', data),
  wants: () => api.get('/forecast/wants/'),
  updateWantsScores: (scores: Record<string, number>) => api.post('/forecast/wants/', { scores }),
}

// Reconciliation
export const reconciliationAPI = {
  list: () => api.get('/reconciliation/'),
  start: (month: string, csv_content: string) =>
    api.post('/reconciliation/start/', { month, csv_content }),
  matchManual: (sessionId: number, entry_id: number, transaction_id: number) =>
    api.patch(`/reconciliation/${sessionId}/match_manual/`, { entry_id, transaction_id }),
  ignoreEntry: (sessionId: number, entry_id: number) =>
    api.patch(`/reconciliation/${sessionId}/ignore_entry/`, { entry_id }),
  close: (sessionId: number) =>
    api.post(`/reconciliation/${sessionId}/close/`),
}

// Documents
export const documentsAPI = {
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    // Do NOT set Content-Type manually — browser must add the multipart boundary automatically
    return api.post('/documents/upload/', form, { headers: { 'Content-Type': undefined } })
  },
  preview: (id: number) => api.get(`/documents/${id}/preview/`),
  import: (id: number, transactions: object[]) =>
    api.post(`/documents/${id}/import/`, { transactions }),
  downloadPDF: (month: string) =>
    api.get(`/documents/report/pdf/?month=${month}`, { responseType: 'blob' }),
  downloadTemplate: (month: string) =>
    api.get(`/documents/template/?month=${month}`, { responseType: 'blob' }),
}
