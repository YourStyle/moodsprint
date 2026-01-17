/**
 * Authentication service.
 */

import { api } from './api';
import type { User, ApiResponse } from '@/domain/types';

interface ReferralCard {
  id: number;
  name: string;
  description?: string;
  genre: string;
  rarity: string;
  hp: number;
  attack: number;
  emoji: string;
  image_url?: string | null;
}

interface ReferralRewards {
  referrer_rewarded?: boolean;
  referrer_card?: ReferralCard;
  invitee_starter_deck?: ReferralCard[];
  referrer_name?: string;
}

interface AuthResponse {
  user: User;
  token: string;
  is_new_user?: boolean;
  friendship_created?: boolean;
  referral_rewards?: ReferralRewards;
}

export type { ReferralCard, ReferralRewards, AuthResponse };

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

  async devAuthenticate(telegramId?: number, username?: string, devSecret?: string): Promise<ApiResponse<AuthResponse>> {
    const payload: Record<string, unknown> = {
      telegram_id: telegramId || 12345,
      username: username || 'dev_user',
    };

    // Add dev_secret if provided (for production dev mode)
    if (devSecret) {
      payload.dev_secret = devSecret;
    }

    const response = await api.post<AuthResponse>('/auth/dev', payload);

    if (response.success && response.data) {
      api.setToken(response.data.token);
    }

    return response;
  },

  async register(email: string, password: string, firstName: string): Promise<ApiResponse<AuthResponse>> {
    const response = await api.post<AuthResponse>('/auth/register', {
      email,
      password,
      first_name: firstName,
    });

    if (response.success && response.data) {
      api.setToken(response.data.token);
    }

    return response;
  },

  async login(email: string, password: string): Promise<ApiResponse<AuthResponse>> {
    const response = await api.post<AuthResponse>('/auth/login', {
      email,
      password,
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
