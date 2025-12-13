/**
 * Merge service for card merging functionality.
 */

import type {
  ApiResponse,
  Card,
  MergeChances,
  MergeLog,
  MergeResult,
} from '@/domain/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

async function fetchWithAuth<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const token = localStorage.getItem('token');

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  return response.json();
}

export const mergeService = {
  /**
   * Preview merge chances for two cards.
   */
  async previewMerge(
    card1Id: number,
    card2Id: number
  ): Promise<
    ApiResponse<{
      card1: Card;
      card2: Card;
      chances: Record<string, number>;
      bonuses: { type: string; value: string }[];
      can_merge: boolean;
    }>
  > {
    return fetchWithAuth('/cards/merge/preview', {
      method: 'POST',
      body: JSON.stringify({ card1_id: card1Id, card2_id: card2Id }),
    });
  },

  /**
   * Merge two cards into a new random card.
   * WARNING: This will destroy both input cards!
   */
  async mergeCards(
    card1Id: number,
    card2Id: number
  ): Promise<ApiResponse<MergeResult>> {
    return fetchWithAuth('/cards/merge', {
      method: 'POST',
      body: JSON.stringify({ card1_id: card1Id, card2_id: card2Id }),
    });
  },

  /**
   * Get recent merge history.
   */
  async getMergeHistory(
    limit: number = 10
  ): Promise<ApiResponse<{ merges: MergeLog[] }>> {
    return fetchWithAuth(`/cards/merge/history?limit=${limit}`);
  },
};

export default mergeService;
