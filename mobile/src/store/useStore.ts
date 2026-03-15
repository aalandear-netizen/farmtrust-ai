/**
 * Global state store using Zustand.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { authApi } from '../services/api';

interface User {
  id: string;
  email: string;
  role: string;
}

interface TrustScore {
  score: number;
  grade: string;
  confidence: number;
}

interface AppState {
  // Auth
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;

  // Trust Score
  trustScore: TrustScore | null;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setTrustScore: (score: TrustScore) => void;
  hydrate: () => Promise<void>;
}

export const useStore = create<AppState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  trustScore: null,

  login: async (email, password) => {
    const tokenResp = await authApi.login(email, password);
    const { access_token } = tokenResp.data;
    await AsyncStorage.setItem('access_token', access_token);

    const meResp = await authApi.getMe();
    set({ user: meResp.data, token: access_token, isAuthenticated: true });
  },

  logout: async () => {
    await AsyncStorage.removeItem('access_token');
    set({ user: null, token: null, isAuthenticated: false, trustScore: null });
  },

  setTrustScore: (score) => set({ trustScore: score }),

  hydrate: async () => {
    const token = await AsyncStorage.getItem('access_token');
    if (token) {
      try {
        const meResp = await authApi.getMe();
        set({ user: meResp.data, token, isAuthenticated: true });
      } catch {
        await AsyncStorage.removeItem('access_token');
      }
    }
  },
}));
