/**
 * Focus sessions service.
 */

import { api } from './api';
import type {
  FocusSession,
  StartFocusInput,
  ApiResponse,
  XPReward,
  Card,
} from '@/domain/types';

interface FocusSessionResponse {
  session: FocusSession | null;
  sessions?: FocusSession[];
}

interface FocusSessionWithXP {
  session: FocusSession;
  xp_earned: number;
  achievements_unlocked: XPReward['achievements_unlocked'];
  card_earned?: Card;
  quick_completion?: boolean;
  quick_completion_message?: string;
  level_up?: boolean;
  new_level?: number;
  level_rewards?: LevelRewardPayload[];
  genre_unlock_available?: GenreUnlockPayload | null;
  streak_milestone?: {
    milestone_days: number;
    xp_bonus: number;
    card_earned?: { id: number; name: string; description: string; genre: string; rarity: string; hp: number; attack: number; emoji: string; image_url?: string | null };
  };
}

// Level-up payload returned with XP-granting responses
interface LevelRewardPayload {
  type: 'sparks' | 'energy' | 'card' | 'genre_unlock' | 'archetype_tier' | 'xp_boost';
  amount?: number;
  rarity?: string;
  slot?: number;
  tier?: string;
  card?: { id: number; name: string; emoji: string; rarity: string } | null;
  description?: string;
}

interface GenreUnlockPayload {
  can_unlock: boolean;
  available_genres: string[];
  suggested_genres?: string[];
}

interface FocusHistoryResponse {
  sessions: FocusSession[];
  total: number;
  total_minutes: number;
}

interface TodayFocusResponse {
  sessions_count: number;
  total_minutes: number;
  sessions: FocusSession[];
}

export const focusService = {
  async startSession(input: StartFocusInput): Promise<ApiResponse<{ session: FocusSession }>> {
    return api.post<{ session: FocusSession }>('/focus/start', input);
  },

  async getActiveSession(): Promise<ApiResponse<FocusSessionResponse>> {
    return api.get<FocusSessionResponse>('/focus/active');
  },

  async completeSession(
    sessionId?: number,
    completeSubtask: boolean = false
  ): Promise<ApiResponse<FocusSessionWithXP>> {
    return api.post<FocusSessionWithXP>('/focus/complete', {
      session_id: sessionId,
      complete_subtask: completeSubtask,
    });
  },

  async cancelSession(sessionId?: number, reason?: string): Promise<ApiResponse<FocusSessionResponse>> {
    return api.post<FocusSessionResponse>('/focus/cancel', {
      session_id: sessionId,
      reason,
    });
  },

  async pauseSession(): Promise<ApiResponse<FocusSessionResponse>> {
    return api.post<FocusSessionResponse>('/focus/pause');
  },

  async resumeSession(): Promise<ApiResponse<FocusSessionResponse>> {
    return api.post<FocusSessionResponse>('/focus/resume');
  },

  async getHistory(params?: {
    limit?: number;
    offset?: number;
  }): Promise<ApiResponse<FocusHistoryResponse>> {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.offset) searchParams.set('offset', params.offset.toString());

    const query = searchParams.toString();
    return api.get<FocusHistoryResponse>(`/focus/history${query ? `?${query}` : ''}`);
  },

  async getTodayFocus(): Promise<ApiResponse<TodayFocusResponse>> {
    return api.get<TodayFocusResponse>('/focus/today');
  },

  async extendSession(minutes: number): Promise<ApiResponse<FocusSessionResponse>> {
    return api.post<FocusSessionResponse>('/focus/extend', {
      minutes,
    });
  },
};
