/**
 * Cosmetics service for card frames and profile frames.
 */

import type { ApiResponse } from '@/domain/types';
import { api } from './api';

export interface CosmeticItem {
  id: string;
  type: 'card_frame' | 'profile_frame';
  name: string;
  description: string;
  price_sparks: number;
  css: string;
  preview_gradient: string;
  min_level: number;
  is_owned?: boolean;
  is_equipped?: boolean;
}

export interface CosmeticsCatalogResponse {
  cosmetics: CosmeticItem[];
  equipped_card_frame: string | null;
  equipped_profile_frame: string | null;
}

export const cosmeticsService = {
  /**
   * Get all available cosmetics with ownership/equipped status.
   */
  async getCatalog(lang: string = 'ru'): Promise<ApiResponse<CosmeticsCatalogResponse>> {
    return api.get(`/cosmetics?lang=${lang}`);
  },

  /**
   * Buy a cosmetic item with Sparks.
   */
  async buy(cosmeticId: string): Promise<ApiResponse<{ success: boolean; cosmetic_id: string }>> {
    return api.post('/cosmetics/buy', { cosmetic_id: cosmeticId });
  },

  /**
   * Equip a cosmetic item.
   */
  async equip(cosmeticId: string): Promise<ApiResponse<{ success: boolean; cosmetic_id: string }>> {
    return api.post('/cosmetics/equip', { cosmetic_id: cosmeticId });
  },

  /**
   * Unequip a cosmetic by type.
   */
  async unequip(type: 'card_frame' | 'profile_frame'): Promise<ApiResponse<{ success: boolean }>> {
    return api.post('/cosmetics/unequip', { type });
  },
};

export default cosmeticsService;
