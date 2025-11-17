import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// User API
export const userAPI = {
  getUser: () => api.get('/user'),
  updateUser: (data) => api.put('/user', data),
};

// Income API
export const incomeAPI = {
  getAll: () => api.get('/income'),
  add: (data) => api.post('/income', data),
  update: (id, data) => api.put(`/income/${id}`, data),
  delete: (id) => api.delete(`/income/${id}`),
};

// Expense API
export const expenseAPI = {
  getAll: () => api.get('/expenses'),
  add: (data) => api.post('/expenses', data),
  update: (id, data) => api.put(`/expenses/${id}`, data),
  delete: (id) => api.delete(`/expenses/${id}`),
};

// Debt API
export const debtAPI = {
  getAll: () => api.get('/debts'),
  add: (data) => api.post('/debts', data),
  update: (id, data) => api.put(`/debts/${id}`, data),
  delete: (id) => api.delete(`/debts/${id}`),
};

// Savings Goals API
export const savingsGoalsAPI = {
  getAll: () => api.get('/savings-goals'),
  add: (data) => api.post('/savings-goals', data),
  update: (id, data) => api.put(`/savings-goals/${id}`, data),
  delete: (id) => api.delete(`/savings-goals/${id}`),
};

// Analysis API
export const analysisAPI = {
  getBudgetAnalysis: () => api.get('/analyze/budget'),
  getInvestmentRecommendations: () => api.get('/analyze/investments'),
  getSavingsForecast: () => api.get('/analyze/savings-forecast'),
  getDebtAnalysis: (extraPayment = 0) => 
    api.get(`/analyze/debt-management?extra_payment=${extraPayment}`),
};

// Dashboard API
export const dashboardAPI = {
  getSummary: () => api.get('/dashboard'),
};

// Report API
export const reportAPI = {
  generateReport: (type = 'monthly') => 
    api.get(`/generate-report?type=${type}`, { responseType: 'blob' }),
};

// Statement API
export const statementAPI = {
  uploadStatement: (formData) => 
    api.post('/statement/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }),
  importTransactions: (transactions) => 
    api.post('/statement/import', { transactions }),
};

export default api;
