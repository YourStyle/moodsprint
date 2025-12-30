/**
 * Sparks currency API service.
 */

import { apiClient } from './api';
import type { ApiResponse } from './api';

export interface SparksPack {
  id: string;
  sparks: number;
  price_stars: number;
  price_ton: number;
}

export interface SparksTransaction {
  id: number;
  user_id: number;
  amount: number;
  type: string;
  reference_type?: string;
  reference_id?: number;
  description?: string;
  created_at: string;
}

export interface TonDeposit {
  id: number;
  user_id?: number;
  tx_hash: string;
  sender_address: string;
  amount_nano: number;
  amount_ton: number;
  memo?: string;
  status: string;
  sparks_credited?: number;
  created_at: string;
  processed_at?: string;
}

export interface DepositInfo {
  deposit_address: string;
  memo: string;
  instructions: string;
  rates: Record<string, number>;
}

export const sparksService = {
  /**
   * Get current sparks balance and recent transactions.
   */
  async getBalance(): Promise<
    ApiResponse<{
      sparks: number;
      recent_transactions: SparksTransaction[];
    }>
  > {
    return apiClient.get('/sparks/balance');
  },

  /**
   * Get available sparks packs for purchase.
   */
  async getPacks(): Promise<ApiResponse<{ packs: SparksPack[] }>> {
    return apiClient.get('/sparks/packs');
  },

  /**
   * Save TON wallet address.
   */
  async saveWalletAddress(
    walletAddress: string
  ): Promise<ApiResponse<{ wallet_address: string; message: string }>> {
    return apiClient.post('/sparks/wallet', { wallet_address: walletAddress });
  },

  /**
   * Disconnect TON wallet.
   */
  async disconnectWallet(): Promise<ApiResponse<{ message: string }>> {
    return apiClient.delete('/sparks/wallet');
  },

  /**
   * Get deposit info for TON deposits.
   */
  async getDepositInfo(): Promise<ApiResponse<DepositInfo>> {
    return apiClient.get('/sparks/deposit-info');
  },

  /**
   * Get TON deposit history.
   */
  async getDeposits(): Promise<ApiResponse<{ deposits: TonDeposit[] }>> {
    return apiClient.get('/sparks/deposits');
  },

  /**
   * Get sparks transaction history.
   */
  async getTransactions(
    page = 1,
    perPage = 20
  ): Promise<
    ApiResponse<{
      transactions: SparksTransaction[];
      total: number;
      pages: number;
      current_page: number;
    }>
  > {
    return apiClient.get(`/sparks/transactions?page=${page}&per_page=${perPage}`);
  },
};
