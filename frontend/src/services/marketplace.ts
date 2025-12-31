/**
 * Marketplace API service for Sparks trading.
 */

import type { ApiResponse } from '@/domain/types';
import { api } from './api';

export interface MarketListing {
  id: number;
  seller_id: number;
  seller_name?: string;
  card_id: number;
  card: {
    id: number;
    name: string;
    description?: string;
    emoji: string;
    image_url?: string;
    rarity: string;
    genre: string;
    hp: number;
    attack: number;
  };
  price: number;  // Price in Sparks
  price_stars?: number;  // Legacy, for backward compatibility
  status: 'active' | 'sold' | 'cancelled';
  created_at: string;
  sold_at?: string;
}

export interface SparksBalance {
  sparks: number;
}

export interface SparksTransaction {
  id: number;
  amount: number;
  type: string;
  reference_type?: string;
  reference_id?: number;
  description?: string;
  created_at: string;
}

class MarketplaceService {
  async browseListings(params?: {
    page?: number;
    per_page?: number;
    rarity?: string;
    genre?: string;
    min_price?: number;
    max_price?: number;
    sort_by?: 'newest' | 'price_low' | 'price_high';
  }): Promise<ApiResponse<{
    listings: MarketListing[];
    total: number;
    page: number;
    pages: number;
  }>> {
    const query = new URLSearchParams();
    if (params?.page) query.set('page', params.page.toString());
    if (params?.per_page) query.set('per_page', params.per_page.toString());
    if (params?.rarity) query.set('rarity', params.rarity);
    if (params?.genre) query.set('genre', params.genre);
    if (params?.min_price) query.set('min_price', params.min_price.toString());
    if (params?.max_price) query.set('max_price', params.max_price.toString());
    if (params?.sort_by) query.set('sort_by', params.sort_by);
    return api.get(`/marketplace?${query}`);
  }

  async getListing(listingId: number): Promise<ApiResponse<{ listing: MarketListing }>> {
    return api.get(`/marketplace/${listingId}`);
  }

  async createListing(data: {
    card_id: number;
    price: number;
  }): Promise<ApiResponse<{ listing: MarketListing }>> {
    return api.post('/marketplace', data);
  }

  async cancelListing(listingId: number): Promise<ApiResponse<void>> {
    return api.delete(`/marketplace/${listingId}`);
  }

  async getMyListings(): Promise<ApiResponse<{
    listings: MarketListing[];
    total: number;
  }>> {
    return api.get('/marketplace/my-listings');
  }

  /**
   * Purchase a card with Sparks.
   * Directly deducts Sparks from balance.
   */
  async purchaseWithSparks(listingId: number): Promise<ApiResponse<{
    card: {
      id: number;
      name: string;
      rarity: string;
    };
    price_paid: number;
    seller_revenue: number;
  }>> {
    return api.post(`/marketplace/${listingId}/buy`);
  }

  /**
   * Skip card cooldown by paying Sparks.
   */
  async skipCardCooldown(cardId: number): Promise<ApiResponse<{
    card: {
      id: number;
      name: string;
    };
    price_paid: number;
  }>> {
    return api.post(`/cards/${cardId}/skip-cooldown`);
  }

  async getBalance(): Promise<ApiResponse<SparksBalance>> {
    return api.get('/marketplace/balance');
  }

  async getTransactions(params?: {
    page?: number;
    per_page?: number;
  }): Promise<ApiResponse<{
    transactions: SparksTransaction[];
    total: number;
    page: number;
    pages: number;
  }>> {
    const query = new URLSearchParams();
    if (params?.page) query.set('page', params.page.toString());
    if (params?.per_page) query.set('per_page', params.per_page.toString());
    return api.get(`/marketplace/transactions?${query}`);
  }
}

export const marketplaceService = new MarketplaceService();
