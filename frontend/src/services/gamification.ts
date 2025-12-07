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
};
