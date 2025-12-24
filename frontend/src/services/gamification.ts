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
  ProductivityPatterns,
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

// Genre types
export type Genre = 'magic' | 'fantasy' | 'scifi' | 'cyberpunk' | 'anime';

export interface GenreInfo {
  id: Genre;
  name: string;
  description: string;
  emoji: string;
}

interface GenresResponse {
  genres: GenreInfo[];
}

// Quest types
export interface DailyQuest {
  id: number;
  quest_type: string;
  title: string;
  description: string;
  themed_description: string;
  target_count: number;
  current_count: number;
  progress_percent: number;
  xp_reward: number;
  stat_points_reward: number;
  date: string;
  completed: boolean;
  completed_at: string | null;
  claimed: boolean;
}

interface QuestsResponse {
  quests: DailyQuest[];
}

interface QuestRewardResponse {
  success: boolean;
  reward?: {
    xp: number;
    stat_points: number;
    xp_info?: {
      level_up?: boolean;
      new_level?: number;
    };
  };
}

// Character types
export interface CharacterStats {
  id: number;
  user_id: number;
  strength: number;
  agility: number;
  intelligence: number;
  max_hp: number;
  current_hp: number;
  attack_power: number;
  defense: number;
  speed: number;
  battles_won: number;
  battles_lost: number;
  available_stat_points: number;
  total_stats: number;
}

interface CharacterResponse {
  character: CharacterStats;
}

interface DistributeStatResponse {
  success: boolean;
  character?: CharacterStats;
  error?: string;
  available?: number;
}

// Monster types
export interface Monster {
  id: number;
  name: string;
  description?: string;
  genre: string;
  level: number;
  hp: number;
  attack: number;
  defense: number;
  speed: number;
  xp_reward: number;
  stat_points_reward: number;
  sprite_url: string | null;
  emoji: string;
  is_boss: boolean;
  // Event monster fields
  is_event_monster?: boolean;
  event_id?: number;
  event_name?: string;
  event_emoji?: string;
  guaranteed_rarity?: string;
  required_cards?: {
    min_cards: number;
    max_cards: number;
    min_genres?: number;
    same_genre_bonus: boolean;
    description: string;
  };
}

// Card types for battle
export interface BattleCard {
  id: number;
  name: string;
  description?: string;
  genre: string;
  rarity: string;
  hp: number;
  attack: number;
  current_hp: number;
  emoji: string;
  image_url?: string;
  rarity_color: string;
  is_in_deck: boolean;
}

interface MonstersResponse {
  monsters: Monster[];
  deck: BattleCard[];
  deck_size: number;
}

// Battle types
export interface BattleLogEntry {
  round?: number;
  actor: 'player' | 'monster' | 'system';
  action?: 'attack' | 'critical' | 'card_destroyed';
  damage?: number;
  is_critical?: boolean;
  message?: string;
  card_id?: number | string;
  card_name?: string;
  card_emoji?: string;
  target_id?: number | string;
  target_name?: string;
  target_emoji?: string;
}

export interface CardBattleState {
  id: number | string;
  name: string;
  emoji?: string;
  image_url?: string;
  hp: number;
  max_hp: number;
  attack: number;
  rarity?: string;
  genre?: string;
  alive: boolean;
}

// Monster card in battle
export interface MonsterCardState {
  id: string;
  name: string;
  emoji: string;
  hp: number;
  max_hp: number;
  attack: number;
  alive: boolean;
}

// Active battle state
export interface ActiveBattle {
  id: number;
  user_id: number;
  monster_id: number;
  monster: Monster | null;
  state: {
    player_cards: CardBattleState[];
    monster_cards: MonsterCardState[];
    current_turn: 'player' | 'monster';
    battle_log: BattleLogEntry[];
    damage_dealt: number;
    damage_taken: number;
    scaled_stats: {
      hp: number;
      attack: number;
      defense: number;
      xp_reward: number;
      stat_points_reward: number;
    };
  };
  status: 'active' | 'won' | 'lost';
  current_round: number;
  created_at: string;
}

// Start battle response
export interface StartBattleResponse {
  success: boolean;
  battle: ActiveBattle;
  message?: string;
  error?: string;
}

// Turn result response
export interface TurnResult {
  success: boolean;
  battle: ActiveBattle;
  turn_log: BattleLogEntry[];
  status: 'continue' | 'won' | 'lost';
  result?: {
    won: boolean;
    rounds: number;
    damage_dealt: number;
    damage_taken: number;
    xp_earned: number;
    stat_points_earned: number;
    level_up: boolean;
    cards_lost: number[];
    reward_card?: BattleCard | null;
  };
}

// Legacy battle result for backwards compatibility
export interface BattleResult {
  won: boolean;
  rounds: number;
  damage_dealt: number;
  damage_taken: number;
  battle_log: BattleLogEntry[];
  xp_earned: number;
  stat_points_earned: number;
  level_up: boolean;
  cards_used: BattleCard[];
  cards_lost: number[];
  cards_remaining: CardBattleState[];
  monster: Monster;
  reward_card?: BattleCard | null;
}

export interface BattleHistory {
  id: number;
  monster: Monster | null;
  won: boolean;
  rounds: number;
  damage_dealt: number;
  damage_taken: number;
  xp_earned: number;
  stat_points_earned: number;
  created_at: string;
}

interface BattleHistoryResponse {
  battles: BattleHistory[];
}

// Boss task types
export interface BossTaskInfo {
  is_boss: boolean;
  reason?: string;
  xp_multiplier?: number;
  bonus_stat_points?: number;
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

  async getProductivityPatterns(): Promise<ApiResponse<ProductivityPatterns>> {
    return api.get<ProductivityPatterns>('/user/productivity-patterns');
  },

  // Genre endpoints
  async getGenres(): Promise<ApiResponse<GenresResponse>> {
    return api.get<GenresResponse>('/genres');
  },

  async setGenre(genre: Genre): Promise<ApiResponse<{ success: boolean; genre: Genre }>> {
    return api.put<{ success: boolean; genre: Genre }>('/profile/genre', { genre });
  },

  // Quest endpoints
  async getQuests(): Promise<ApiResponse<QuestsResponse>> {
    return api.get<QuestsResponse>('/quests');
  },

  async claimQuestReward(questId: number): Promise<ApiResponse<QuestRewardResponse>> {
    return api.post<QuestRewardResponse>(`/quests/${questId}/claim`);
  },

  // Character endpoints
  async getCharacter(): Promise<ApiResponse<CharacterResponse>> {
    return api.get<CharacterResponse>('/character');
  },

  async distributeStat(
    stat: 'strength' | 'agility' | 'intelligence',
    points: number
  ): Promise<ApiResponse<DistributeStatResponse>> {
    return api.post<DistributeStatResponse>('/character/distribute', { stat, points });
  },

  async healCharacter(full?: boolean): Promise<ApiResponse<CharacterResponse>> {
    return api.post<CharacterResponse>('/character/heal', { full: full ?? true });
  },

  // Arena endpoints
  async getMonsters(): Promise<ApiResponse<MonstersResponse>> {
    return api.get<MonstersResponse>('/arena/monsters');
  },

  // Start a new turn-based battle
  async startBattle(monsterId: number, cardIds: number[]): Promise<ApiResponse<StartBattleResponse>> {
    return api.post<StartBattleResponse>('/arena/battle', { monster_id: monsterId, card_ids: cardIds });
  },

  // Get active battle if any
  async getActiveBattle(): Promise<ApiResponse<{ battle: ActiveBattle | null }>> {
    return api.get<{ battle: ActiveBattle | null }>('/arena/battle/active');
  },

  // Execute a turn in battle
  async executeTurn(playerCardId: number, targetCardId: string): Promise<ApiResponse<TurnResult>> {
    return api.post<TurnResult>('/arena/battle/turn', {
      player_card_id: playerCardId,
      target_card_id: targetCardId,
    });
  },

  // Forfeit the current battle
  async forfeitBattle(): Promise<ApiResponse<TurnResult>> {
    return api.post<TurnResult>('/arena/battle/forfeit');
  },

  // Legacy battle method (for backwards compatibility)
  async battle(monsterId: number, cardIds: number[]): Promise<ApiResponse<BattleResult>> {
    return api.post<BattleResult>('/arena/battle', { monster_id: monsterId, card_ids: cardIds });
  },

  async getBattleHistory(limit: number = 10): Promise<ApiResponse<BattleHistoryResponse>> {
    return api.get<BattleHistoryResponse>(`/arena/history?limit=${limit}`);
  },

  // Boss task info
  async getBossTaskInfo(taskId: number): Promise<ApiResponse<BossTaskInfo>> {
    return api.get<BossTaskInfo>(`/tasks/${taskId}/boss-info`);
  },

  // Admin endpoints
  async getAdminUsers(): Promise<ApiResponse<AdminUsersResponse>> {
    return api.get<AdminUsersResponse>('/admin/users');
  },

  async getUserActivity(userId: number): Promise<ApiResponse<UserActivityResponse>> {
    return api.get<UserActivityResponse>(`/admin/activity/${userId}`);
  },

  async removeFriend(userId: number, friendId: number): Promise<ApiResponse<{ message: string }>> {
    return api.post<{ message: string }>('/admin/remove-friend', { user_id: userId, friend_id: friendId });
  },
};

interface AdminUsersResponse {
  users: {
    id: number;
    telegram_id: number;
    username: string | null;
    first_name: string | null;
    level: number;
    xp: number;
    created_at: string | null;
  }[];
}

interface UserActivityResponse {
  user_id: number;
  username: string | null;
  first_name: string | null;
  activity: Record<string, number>;
}
