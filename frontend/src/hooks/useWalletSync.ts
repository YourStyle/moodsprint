'use client';

import { useEffect } from 'react';
import { useTonWallet } from '@tonconnect/ui-react';
import { useAppStore } from '@/lib/store';
import { sparksService } from '@/services/sparks';

/**
 * Hook to sync TON wallet address with backend.
 * Should be used in a component wrapped with TonConnectUIProvider.
 */
export function useWalletSync() {
  const wallet = useTonWallet();
  const { user, setUser } = useAppStore();
  const walletAddress = wallet?.account.address;

  useEffect(() => {
    if (walletAddress && user) {
      // Save wallet address to backend
      sparksService.saveWalletAddress(walletAddress).then((result) => {
        if (result.success && result.data) {
          // Update user in store with new wallet address
          setUser({
            ...user,
            ton_wallet_address: result.data.wallet_address,
          });
        }
      }).catch((err) => {
        console.error('[Wallet] Failed to save wallet address:', err);
      });
    }
  }, [walletAddress, user, setUser]);

  return wallet;
}
