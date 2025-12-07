/**
 * Mood service.
 */

import { api } from './api';
import type {
  MoodCheck,
  CreateMoodInput,
  MoodHistoryDay,
  ApiResponse,
  XPReward,
} from '@/domain/types';

interface MoodCheckResponse {
  mood_check: MoodCheck | null;
}

interface MoodCheckWithXP {
  mood_check: MoodCheck;
  xp_earned: number;
  achievements_unlocked: XPReward['achievements_unlocked'];
}

interface MoodHistoryResponse {
  history: MoodHistoryDay[];
}

interface MoodStatsResponse {
  overall: {
    average_mood: number;
    average_energy: number;
    total_checks: number;
  };
  weekly: {
    average_mood: number;
    average_energy: number;
    total_checks: number;
  };
}

export const moodService = {
  async createMoodCheck(input: CreateMoodInput): Promise<ApiResponse<MoodCheckWithXP>> {
    return api.post<MoodCheckWithXP>('/mood', input);
  },

  async getLatestMood(): Promise<ApiResponse<MoodCheckResponse>> {
    return api.get<MoodCheckResponse>('/mood/latest');
  },

  async getMoodHistory(days?: number): Promise<ApiResponse<MoodHistoryResponse>> {
    const query = days ? `?days=${days}` : '';
    return api.get<MoodHistoryResponse>(`/mood/history${query}`);
  },

  async getMoodStats(): Promise<ApiResponse<MoodStatsResponse>> {
    return api.get<MoodStatsResponse>('/mood/stats');
  },
};
