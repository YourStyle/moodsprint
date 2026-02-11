/**
 * Cards API service.
 */

import type { ApiResponse } from '@/domain/types';
import { api } from './api';

// Card types
export interface AbilityInfo {
  type: string;
  name: string;
  description: string;
  emoji: string;
  cooldown: number;
  current_cooldown: number;
}

export interface Card {
  id: number;
  user_id: number;
  template_id: number | null;
  name: string;
  description: string | null;
  genre: string;
  rarity: 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary';
  hp: number;
  attack: number;
  current_hp: number;
  ability: string | null;
  ability_info: AbilityInfo | null;
  image_url: string | null;
  emoji: string;
  card_level: number;
  card_xp: number;
  is_companion: boolean;
  is_showcase: boolean;
  showcase_slot: number | null;
  is_in_deck: boolean;
  is_tradeable: boolean;
  is_alive: boolean;
  is_on_cooldown: boolean;
  cooldown_remaining: number | null;
  rarity_color: string;
  created_at: string;
}

export interface CardTemplate {
  id: number;
  name: string;
  description: string | null;
  genre: string;
  base_hp: number;
  base_attack: number;
  image_url: string | null;
  emoji: string;
}

export interface Friend {
  friendship_id: number;
  friend_id: number;
  username?: string;
  first_name?: string;
  level?: number;
  since: string | null;
}

export interface FriendRequest {
  id: number;
  from_user_id: number;
  username?: string;
  first_name?: string;
  created_at: string | null;
}

export interface Trade {
  id: number;
  sender_id: number;
  receiver_id: number;
  // Single card (backward compatibility)
  sender_card: Card | null;
  receiver_card: Card | null;
  // Multi-card support
  sender_cards: Card[];
  receiver_cards: Card[];
  status: 'pending' | 'accepted' | 'rejected' | 'cancelled';
  message: string | null;
  sender_name?: string;
  receiver_name?: string;
  created_at: string | null;
}

export interface DeckStats {
  total_hp: number;
  total_attack: number;
  genres: string[];
}

// Response types
interface CardsResponse {
  cards: Card[];
  total: number;
  rarity_counts: Record<string, number>;
}

interface DeckResponse {
  deck: Card[];
  size: number;
  max_size: number;
  stats: DeckStats;
}

interface FriendsResponse {
  friends: Friend[];
  total: number;
}

interface FriendRequestsResponse {
  requests: FriendRequest[];
  total: number;
}

interface TradesResponse {
  sent: Trade[];
  received: Trade[];
}

export interface PendingReward {
  id: number;
  user_id: number;
  friend_id: number;
  friend_name: string | null;
  card: Card | null;
  is_referrer: boolean;
  is_claimed: boolean;
  created_at: string | null;
}

interface PendingRewardsResponse {
  rewards: PendingReward[];
  total: number;
}

export interface HealStatus {
  heals_today: number;
  required_tasks: number;
  completed_tasks: number;
  can_heal: boolean;
  heal_requirements: number[];
}

class CardsService {
  // Card collection
  async getCards(genre?: string, inDeck?: boolean): Promise<ApiResponse<CardsResponse>> {
    let url = '/cards';
    const params: string[] = [];
    if (genre) params.push(`genre=${genre}`);
    if (inDeck !== undefined) params.push(`in_deck=${inDeck}`);
    if (params.length > 0) url += '?' + params.join('&');
    return api.get<CardsResponse>(url);
  }

  async getCard(cardId: number): Promise<ApiResponse<{ card: Card }>> {
    return api.get<{ card: Card }>(`/cards/${cardId}`);
  }

  // Deck management
  async getDeck(): Promise<ApiResponse<DeckResponse>> {
    return api.get<DeckResponse>('/deck');
  }

  async addToDeck(cardId: number): Promise<ApiResponse<{ success: boolean; card?: Card }>> {
    return api.post<{ success: boolean; card?: Card }>('/deck/add', { card_id: cardId });
  }

  async removeFromDeck(cardId: number): Promise<ApiResponse<{ message: string }>> {
    return api.post<{ message: string }>('/deck/remove', { card_id: cardId });
  }

  // Card healing
  async getHealStatus(): Promise<ApiResponse<HealStatus>> {
    return api.get<HealStatus>('/cards/heal-status');
  }

  async healCard(cardId: number): Promise<ApiResponse<{ card: Card; message: string }>> {
    return api.post<{ card: Card; message: string }>(`/cards/${cardId}/heal`);
  }

  async healAllCards(): Promise<ApiResponse<{ healed_count: number; message: string; heals_today: number }>> {
    return api.post<{ healed_count: number; message: string; heals_today: number }>('/cards/heal-all');
  }

  // Card templates
  async getTemplates(genre?: string): Promise<ApiResponse<{ templates: CardTemplate[]; total: number }>> {
    let url = '/card-templates';
    if (genre) url += `?genre=${genre}`;
    return api.get<{ templates: CardTemplate[]; total: number }>(url);
  }

  // Friends system
  async getFriends(): Promise<ApiResponse<FriendsResponse>> {
    return api.get<FriendsResponse>('/friends');
  }

  async getFriendRequests(): Promise<ApiResponse<FriendRequestsResponse>> {
    return api.get<FriendRequestsResponse>('/friends/requests');
  }

  async sendFriendRequest(userId?: number, username?: string): Promise<ApiResponse<{ message: string }>> {
    return api.post<{ message: string }>('/friends/request', { user_id: userId, username });
  }

  async acceptFriendRequest(requestId: number): Promise<ApiResponse<{ message: string }>> {
    return api.post<{ message: string }>(`/friends/accept/${requestId}`);
  }

  async rejectFriendRequest(requestId: number): Promise<ApiResponse<{ message: string }>> {
    return api.post<{ message: string }>(`/friends/reject/${requestId}`);
  }

  async connectWithReferrer(referrerId: number): Promise<ApiResponse<{
    message: string;
    friendship: Friend;
    already_friends?: boolean;
  }>> {
    return api.post<{
      message: string;
      friendship: Friend;
      already_friends?: boolean;
    }>('/friends/connect-referral', { referrer_id: referrerId });
  }

  async getFriendCards(friendId: number): Promise<ApiResponse<{ cards: Card[]; total: number }>> {
    return api.get<{ cards: Card[]; total: number }>(`/friends/${friendId}/cards`);
  }

  // Trading system
  async getTrades(): Promise<ApiResponse<TradesResponse>> {
    return api.get<TradesResponse>('/trades');
  }

  async createTrade(
    receiverId: number,
    senderCardIds: number[],
    receiverCardIds?: number[],
    message?: string
  ): Promise<ApiResponse<{ message: string; trade: Trade }>> {
    return api.post<{ message: string; trade: Trade }>('/trades/create', {
      receiver_id: receiverId,
      sender_card_ids: senderCardIds,
      receiver_card_ids: receiverCardIds,
      message,
    });
  }

  async acceptTrade(tradeId: number): Promise<ApiResponse<{ message: string; trade: Trade }>> {
    return api.post<{ message: string; trade: Trade }>(`/trades/${tradeId}/accept`);
  }

  async rejectTrade(tradeId: number): Promise<ApiResponse<{ message: string }>> {
    return api.post<{ message: string }>(`/trades/${tradeId}/reject`);
  }

  async cancelTrade(tradeId: number): Promise<ApiResponse<{ message: string }>> {
    return api.post<{ message: string }>(`/trades/${tradeId}/cancel`);
  }

  // Image generation (async, called after card is shown)
  async generateCardImage(cardId: number): Promise<ApiResponse<{ image_url?: string; already_exists?: boolean }>> {
    return api.post<{ image_url?: string; already_exists?: boolean }>(`/cards/${cardId}/generate-image`);
  }

  // Card merging
  async mergeCards(cardId1: number, cardId2: number): Promise<ApiResponse<{
    message: string;
    card: Card;
    destroyed_cards: number[];
  }>> {
    return api.post<{
      message: string;
      card: Card;
      destroyed_cards: number[];
    }>('/cards/merge', {
      card_id_1: cardId1,
      card_id_2: cardId2,
    });
  }

  // Pending referral rewards
  async getPendingRewards(): Promise<ApiResponse<PendingRewardsResponse>> {
    return api.get<PendingRewardsResponse>('/cards/pending-rewards');
  }

  async getPendingRewardsCount(): Promise<ApiResponse<{ count: number }>> {
    return api.get<{ count: number }>('/cards/pending-rewards/count');
  }

  async claimPendingRewards(): Promise<ApiResponse<{ claimed: number; message: string }>> {
    return api.post<{ claimed: number; message: string }>('/cards/pending-rewards/claim');
  }

  // Genre unlocking
  async getUnlockedGenres(): Promise<ApiResponse<{
    unlocked_genres: string[];
    unlock_available: GenreUnlockInfo | null;
  }>> {
    return api.get<{ unlocked_genres: string[]; unlock_available: GenreUnlockInfo | null }>('/genres/unlocked');
  }

  async selectGenreUnlock(genre: string): Promise<ApiResponse<{
    success: boolean;
    unlocked_genres: string[];
    genre: string;
  }>> {
    return api.post<{ success: boolean; unlocked_genres: string[]; genre: string }>('/genres/select', { genre });
  }

  // Card leveling
  async addCardXp(cardId: number, amount: number): Promise<ApiResponse<CardXpResult>> {
    return api.post<CardXpResult>(`/cards/${cardId}/add-xp`, { amount });
  }

  // Companion system
  async setCompanion(cardId: number): Promise<ApiResponse<{ success: boolean; card: Card }>> {
    return api.post<{ success: boolean; card: Card }>(`/cards/${cardId}/companion`);
  }

  async getCompanion(): Promise<ApiResponse<{ companion: Card | null }>> {
    return api.get<{ companion: Card | null }>('/companion');
  }

  async removeCompanion(): Promise<ApiResponse<{ success: boolean }>> {
    return api.post<{ success: boolean }>('/companion/remove');
  }

  // Showcase system
  async setShowcase(cardId: number, slot: number): Promise<ApiResponse<{ success: boolean; card: Card }>> {
    return api.post<{ success: boolean; card: Card }>(`/cards/${cardId}/showcase`, { slot });
  }

  async getShowcase(): Promise<ApiResponse<{ slots: (Card | null)[] }>> {
    return api.get<{ slots: (Card | null)[] }>('/showcase');
  }

  async removeShowcase(slot: number): Promise<ApiResponse<{ success: boolean }>> {
    return api.post<{ success: boolean }>('/showcase/remove', { slot });
  }

  // Campaign energy
  async getEnergy(): Promise<ApiResponse<{ energy: number; max_energy: number }>> {
    return api.get<{ energy: number; max_energy: number }>('/energy');
  }

  // Friend profile & ranking
  async getFriendProfile(friendId: number): Promise<ApiResponse<FriendProfile>> {
    return api.get<FriendProfile>(`/friends/${friendId}/profile`);
  }

  async getFriendsRanking(): Promise<ApiResponse<{ ranking: RankingEntry[] }>> {
    return api.get<{ ranking: RankingEntry[] }>('/friends/ranking');
  }
}

// Additional types
export interface GenreUnlockInfo {
  can_unlock: boolean;
  current_count: number;
  max_count: number;
  available_genres: string[];
  user_level: number;
}

export interface CardXpResult {
  success: boolean;
  level_up: boolean;
  old_level: number;
  new_level: number;
  card_xp: number;
  xp_to_next: number;
  max_level: number;
  card: Card;
}

export interface FriendProfile {
  user_id: number;
  username: string;
  first_name: string;
  level: number;
  deck_power: number;
  showcase: (Card | null)[];
  deck: Card[];
}

export interface RankingEntry {
  user_id: number;
  username: string;
  first_name: string;
  level: number;
  deck_power: number;
  cards_count: number;
  rank: number;
  is_me?: boolean;
}

export const cardsService = new CardsService();
