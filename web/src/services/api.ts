/**
 * Centralised API client for the Next.js web dashboard.
 */
import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Attach stored token (browser only)
if (typeof window !== 'undefined') {
  api.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  });
}

export const farmerApi = {
  list: (params?: Record<string, string | number>) =>
    api.get('/farmers/', { params }),
  getById: (id: string) => api.get(`/farmers/${id}`),
};

export const trustScoreApi = {
  getLatest: (farmerId: string) =>
    api.get(`/trust-scores/farmers/${farmerId}/latest`),
  compute: (farmerId: string) =>
    api.post(`/trust-scores/farmers/${farmerId}/compute`),
  getHistory: (farmerId: string) =>
    api.get(`/trust-scores/farmers/${farmerId}/history`),
};

export const loanApi = {
  list: (params?: Record<string, string | number>) =>
    api.get('/loans/', { params }),
  updateStatus: (loanId: string, status: string) =>
    api.patch(`/loans/${loanId}/status?new_status=${status}`),
};

export const auditApi = {
  getLogs: (params?: Record<string, string | number>) =>
    api.get('/audit/logs', { params }),
};
