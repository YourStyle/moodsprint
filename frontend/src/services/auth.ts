/**
 * Authentication service.
 */

import { api } from './api';
import type { User, ApiResponse } from '@/domain/types';

interface AuthResponse {
  user: User;
  token: string;
  is_new_user?: boolean;
}

export const authService = {
  async authenticateTelegram(initData: string, referrerId?: number): Promise<ApiResponse<AuthResponse>> {
    const payload: Record<string, unknown> = {
      init_data: initData,
    };
    if (referrerId) {
      payload.referrer_id = referrerId;
    }

    const response = await api.post<AuthResponse>('/auth/telegram', payload);

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
