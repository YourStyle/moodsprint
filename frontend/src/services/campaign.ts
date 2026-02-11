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

export interface DialogueChoice {
  text: string;
  next?: string; // '' = continue, '_end' = end, '_battle' = start battle, '_skip' = skip battle
}

export interface DialogueLine {
  speaker: string;
  text: string;
  emoji?: string;
  event?: 'start_battle' | 'skip_battle' | 'buff_player' | 'debuff_monster' | 'bonus_xp' | 'heal_cards';
  choices?: DialogueChoice[];
}

export interface CampaignMonster {
  id: number;
  name: string;
  description?: string;
  genre: string;
  emoji: string;
  sprite_url?: string;
  is_boss?: boolean;
}

export interface CampaignLevel {
  id: number;
  chapter_id: number;
  number: number;
  is_boss: boolean;
  title?: string;
  dialogue_before?: DialogueLine[];
  dialogue_after?: DialogueLine[];
  difficulty_multiplier: number;
  required_power: number;
  xp_reward: number;
  stars_max: number;
  is_unlocked: boolean;
  is_completed: boolean;
  stars_earned: number;
  best_rounds?: number;
  attempts: number;
  monster_id?: number;
  monster?: CampaignMonster;
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
  reward_type: 'card' | 'xp' | 'title' | 'sparks';
  reward_data: {
    amount?: number;
    rarity?: string;
    title?: string;
  };
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
  sparks_earned?: number;
  is_new_completion?: boolean;
  chapter_completed?: boolean;
  rewards?: Array<{
    type: string;
    name?: string;
    amount?: number;
    card?: unknown;
  }>;
  dialogue_after?: DialogueLine[];
  story_outro?: string;
  message?: string;
}

export interface DialogueChoiceResult {
  action: string;
  message: string;
  skipped?: boolean;
  completion?: LevelCompletionResult;
  buff?: { type: string; multiplier: number };
  debuff?: { type: string; multiplier: number };
  xp_bonus?: number;
  heal_cards?: boolean;
}

class CampaignService {
  async getCampaignOverview(): Promise<ApiResponse<{
    progress: CampaignProgress;
    chapters: CampaignChapter[];
    energy: number;
    max_energy: number;
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

  async processDialogueChoice(
    levelId: number,
    action: string
  ): Promise<ApiResponse<DialogueChoiceResult>> {
    return api.post(`/campaign/levels/${levelId}/dialogue-choice`, { action });
  }

  async seedCampaign(): Promise<ApiResponse<void>> {
    return api.post('/campaign/seed');
  }
}

export const campaignService = new CampaignService();
