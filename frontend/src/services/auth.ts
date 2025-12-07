/**
 * Authentication service.
 */

import { api } from './api';
import type { User, ApiResponse } from '@/domain/types';

interface AuthResponse {
  user: User;
  token: string;
}

export const authService = {
  async authenticateTelegram(initData: string): Promise<ApiResponse<AuthResponse>> {
    const response = await api.post<AuthResponse>('/auth/telegram', {
      init_data: initData,
    });

    if (response.success && response.data) {
      api.setToken(response.data.token);
    }

    return response;
  },

  async devAuthenticate(telegramId?: number, username?: string): Promise<ApiResponse<AuthResponse>> {
    const response = await api.post<AuthResponse>('/auth/dev', {
      telegram_id: telegramId || 12345,
      username: username || 'dev_user',
    });

    if (response.success && response.data) {
      api.setToken(response.data.token);
    }

    return response;
  },

  async getCurrentUser(): Promise<ApiResponse<{ user: User }>> {
    return api.get<{ user: User }>('/auth/me');
  },

  logout() {
    api.setToken(null);
  },

  isAuthenticated(): boolean {
    return !!api.getToken();
  },
};
