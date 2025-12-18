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
  is_in_deck: boolean;
  is_tradeable: boolean;
  is_alive: boolean;
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
  sender_card: Card | null;
  receiver_card: Card | null;
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
  async healCard(cardId: number): Promise<ApiResponse<{ card: Card; message: string }>> {
    return api.post<{ card: Card; message: string }>(`/cards/${cardId}/heal`);
  }

  async healAllCards(): Promise<ApiResponse<{ healed_count: number; message: string }>> {
    return api.post<{ healed_count: number; message: string }>('/cards/heal-all');
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

  async getFriendCards(friendId: number): Promise<ApiResponse<{ cards: Card[]; total: number }>> {
    return api.get<{ cards: Card[]; total: number }>(`/friends/${friendId}/cards`);
  }

  // Trading system
  async getTrades(): Promise<ApiResponse<TradesResponse>> {
    return api.get<TradesResponse>('/trades');
  }

  async createTrade(
    receiverId: number,
    senderCardId: number,
    receiverCardId?: number,
    message?: string
  ): Promise<ApiResponse<{ message: string; trade: Trade }>> {
    return api.post<{ message: string; trade: Trade }>('/trades/create', {
      receiver_id: receiverId,
      sender_card_id: senderCardId,
      receiver_card_id: receiverCardId,
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
}

export const cardsService = new CardsService();
