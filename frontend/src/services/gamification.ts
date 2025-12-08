/**
 * Gamification service.
 */

import { api } from './api';
import type {
  UserStats,
  Achievement,
  UserAchievement,
  DailyGoal,
  LeaderboardEntry,
  ApiResponse,
} from '@/domain/types';

interface UserStatsResponse extends UserStats {}

interface AchievementsResponse {
  achievements: Achievement[];
}

interface UserAchievementsResponse {
  unlocked: UserAchievement[];
  in_progress: UserAchievement[];
}

interface DailyGoalsResponse {
  goals: DailyGoal[];
  all_completed: boolean;
  bonus_xp_available: number;
}

interface LeaderboardResponse {
  type: 'weekly' | 'all_time';
  leaderboard: LeaderboardEntry[];
}

interface DailyBonusStatusResponse {
  can_claim: boolean;
  potential_xp: number;
  streak_days: number;
  streak_multiplier: number;
  last_claimed: string | null;
}

interface DailyBonusClaimResponse {
  claimed: boolean;
  xp_earned?: number;
  streak_bonus?: number;
  streak_days?: number;
  total_xp?: number;
  level_up?: boolean;
  new_level?: number | null;
  message?: string;
  next_bonus_at?: string;
}

export const gamificationService = {
  async getUserStats(): Promise<ApiResponse<UserStatsResponse>> {
    return api.get<UserStatsResponse>('/user/stats');
  },

  async getAllAchievements(): Promise<ApiResponse<AchievementsResponse>> {
    return api.get<AchievementsResponse>('/achievements');
  },

  async getUserAchievements(): Promise<ApiResponse<UserAchievementsResponse>> {
    return api.get<UserAchievementsResponse>('/user/achievements');
  },

  async getDailyGoals(): Promise<ApiResponse<DailyGoalsResponse>> {
    return api.get<DailyGoalsResponse>('/user/daily-goals');
  },

  async getLeaderboard(
    type: 'weekly' | 'all_time' = 'weekly',
    limit: number = 10
  ): Promise<ApiResponse<LeaderboardResponse>> {
    return api.get<LeaderboardResponse>(`/leaderboard?type=${type}&limit=${limit}`);
  },

  async getDailyBonusStatus(): Promise<ApiResponse<DailyBonusStatusResponse>> {
    return api.get<DailyBonusStatusResponse>('/daily-bonus/status');
  },

  async claimDailyBonus(): Promise<ApiResponse<DailyBonusClaimResponse>> {
    return api.post<DailyBonusClaimResponse>('/daily-bonus');
  },
};
