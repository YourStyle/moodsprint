/**
 * Merge service for card merging functionality.
 */

import type {
  ApiResponse,
  Card,
  MergeLog,
  MergeResult,
} from '@/domain/types';
import { api } from './api';

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
    return api.post('/cards/merge/preview', { card1_id: card1Id, card2_id: card2Id });
  },

  /**
   * Merge two cards into a new random card.
   * WARNING: This will destroy both input cards!
   */
  async mergeCards(
    card1Id: number,
    card2Id: number
  ): Promise<ApiResponse<MergeResult>> {
    return api.post('/cards/merge', { card1_id: card1Id, card2_id: card2Id });
  },

  /**
   * Get recent merge history.
   */
  async getMergeHistory(
    limit: number = 10
  ): Promise<ApiResponse<{ merges: MergeLog[] }>> {
    return api.get(`/cards/merge/history?limit=${limit}`);
  },
};

export default mergeService;
