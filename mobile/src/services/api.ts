/**
 * API client for FarmTrust backend.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 – clear token and redirect to login
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      await AsyncStorage.removeItem('access_token');
    }
    return Promise.reject(error);
  },
);

// ─── Auth ─────────────────────────────────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/token', new URLSearchParams({ username: email, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  register: (email: string, password: string, role = 'farmer') =>
    api.post('/auth/register', { email, password, role }),
  getMe: () => api.get('/auth/me'),
};

// ─── Farmers ──────────────────────────────────────────────────────────────────

export const farmerApi = {
  create: (data: Record<string, unknown>) => api.post('/farmers/', data),
  getById: (id: string) => api.get(`/farmers/${id}`),
  update: (id: string, data: Record<string, unknown>) => api.put(`/farmers/${id}`, data),
};

// ─── Trust Scores ─────────────────────────────────────────────────────────────

export const trustScoreApi = {
  getLatest: (farmerId: string) => api.get(`/trust-scores/farmers/${farmerId}/latest`),
  getHistory: (farmerId: string, limit = 12) =>
    api.get(`/trust-scores/farmers/${farmerId}/history?limit=${limit}`),
};

// ─── Loans ────────────────────────────────────────────────────────────────────

export const loanApi = {
  apply: (data: Record<string, unknown>) => api.post('/loans/', data),
  list: () => api.get('/loans/'),
  getById: (id: string) => api.get(`/loans/${id}`),
  recordRepayment: (loanId: string, data: Record<string, unknown>) =>
    api.post(`/loans/${loanId}/repayments`, data),
};

// ─── Insurance ────────────────────────────────────────────────────────────────

export const insuranceApi = {
  createPolicy: (data: Record<string, unknown>) => api.post('/insurance/policies', data),
  listPolicies: () => api.get('/insurance/policies'),
  fileClaim: (policyId: string, data: Record<string, unknown>) =>
    api.post(`/insurance/policies/${policyId}/claims`, data),
};

// ─── Market ───────────────────────────────────────────────────────────────────

export const marketApi = {
  listListings: (crop?: string) => api.get(`/market/listings${crop ? `?crop=${crop}` : ''}`),
  createListing: (data: Record<string, unknown>) => api.post('/market/listings', data),
  getPrices: (crop: string, state?: string) =>
    api.get(`/market/prices?crop=${crop}${state ? `&state=${state}` : ''}`),
};

// ─── Government ───────────────────────────────────────────────────────────────

export const governmentApi = {
  listSchemes: () => api.get('/government/schemes'),
  applyToScheme: (schemeId: string) => api.post(`/government/schemes/${schemeId}/apply`),
};

// ─── Notifications ────────────────────────────────────────────────────────────

export const notificationsApi = {
  list: (unreadOnly = false) =>
    api.get(`/notifications/?unread_only=${unreadOnly}`),
  markRead: (id: string) => api.patch(`/notifications/${id}/read`),
  markAllRead: () => api.patch('/notifications/read-all'),
};

export default api;
