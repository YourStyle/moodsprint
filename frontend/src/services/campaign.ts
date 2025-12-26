/**
 * Campaign/Story mode API service.
 */

import type { ApiResponse } from '@/domain/types';
import { api } from './api';

export interface CampaignChapter {
  id: number;
  number: number;
  name: string;
  genre: string;
  description?: string;
  story_intro?: string;
  story_outro?: string;
  emoji: string;
  background_color: string;
  required_power: number;
  xp_reward: number;
  guaranteed_card_rarity: string;
  is_unlocked: boolean;
  is_completed: boolean;
  levels_completed: number;
  total_levels: number;
  stars_earned: number;
  max_stars: number;
}

export interface CampaignLevel {
  id: number;
  chapter_id: number;
  number: number;
  is_boss: boolean;
  title?: string;
  dialogue_before?: Array<{ speaker: string; text: string }>;
  dialogue_after?: Array<{ speaker: string; text: string }>;
  difficulty_multiplier: number;
  required_power: number;
  xp_reward: number;
  stars_max: number;
  is_unlocked: boolean;
  is_completed: boolean;
  stars_earned: number;
  best_rounds?: number;
  attempts: number;
}

export interface CampaignProgress {
  id: number;
  user_id: number;
  current_chapter: number;
  current_level: number;
  chapters_completed: number[];
  total_stars_earned: number;
  bosses_defeated: number;
}

export interface CampaignReward {
  id: number;
  chapter_id: number;
  reward_type: 'card' | 'xp' | 'title';
  reward_data: Record<string, unknown>;
  name?: string;
  description?: string;
  emoji: string;
}

export interface LevelStartData {
  level: CampaignLevel;
  dialogue_before?: Array<{ speaker: string; text: string }>;
  monster_id: number;
  difficulty_multiplier: number;
}

export interface LevelBattleConfig {
  monster_id: number;
  monster_name: string;
  is_boss: boolean;
  scaled_stats: {
    hp: number;
    attack: number;
    defense: number;
    xp_reward: number;
  };
}

export interface LevelCompletionResult {
  won: boolean;
  stars_earned?: number;
  xp_earned?: number;
  is_new_completion?: boolean;
  chapter_completed?: boolean;
  rewards?: Array<{
    type: string;
    name?: string;
    amount?: number;
    card?: unknown;
  }>;
  dialogue_after?: Array<{ speaker: string; text: string }>;
  story_outro?: string;
  message?: string;
}

class CampaignService {
  async getCampaignOverview(): Promise<ApiResponse<{
    progress: CampaignProgress;
    chapters: CampaignChapter[];
  }>> {
    return api.get('/campaign');
  }

  async getProgress(): Promise<ApiResponse<{ progress: CampaignProgress }>> {
    return api.get('/campaign/progress');
  }

  async getChapterDetails(chapterNumber: number): Promise<ApiResponse<{
    chapter: CampaignChapter;
    levels: CampaignLevel[];
    rewards: CampaignReward[];
    story_intro?: string;
  }>> {
    return api.get(`/campaign/chapters/${chapterNumber}`);
  }

  async startLevel(levelId: number): Promise<ApiResponse<LevelStartData>> {
    return api.post(`/campaign/levels/${levelId}/start`);
  }

  async completeLevel(
    levelId: number,
    data: {
      won: boolean;
      rounds: number;
      hp_remaining: number;
      cards_lost: number;
    }
  ): Promise<ApiResponse<LevelCompletionResult>> {
    return api.post(`/campaign/levels/${levelId}/complete`, data);
  }

  async getLevelBattleConfig(levelId: number): Promise<ApiResponse<LevelBattleConfig>> {
    return api.get(`/campaign/levels/${levelId}/battle-config`);
  }

  async seedCampaign(): Promise<ApiResponse<void>> {
    return api.post('/campaign/seed');
  }
}

export const campaignService = new CampaignService();
