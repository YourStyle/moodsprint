'use client';

import { useTonConnectUI, useTonWallet } from '@tonconnect/ui-react';
import { Wallet, LogOut } from 'lucide-react';
import { useWalletSync } from '@/hooks/useWalletSync';

interface TonConnectButtonProps {
  className?: string;
}

export function TonConnectButton({ className = '' }: TonConnectButtonProps) {
  const [tonConnectUI] = useTonConnectUI();
  const wallet = useTonWallet();

  // Sync wallet address with backend
  useWalletSync();

  const handleClick = async () => {
    if (wallet) {
      // Disconnect wallet
      await tonConnectUI.disconnect();
    } else {
      // Open connection modal
      await tonConnectUI.openModal();
    }
  };

  // Format address for display (first 4 + last 4 chars)
  const formatAddress = (address: string) => {
    if (address.length <= 10) return address;
    return `${address.slice(0, 4)}...${address.slice(-4)}`;
  };

  return (
    <button
      onClick={handleClick}
      className={`
        flex items-center gap-2 px-4 py-2 rounded-xl
        font-medium transition-all duration-200
        ${wallet
          ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-cyan-400 border border-cyan-500/30 hover:border-cyan-400/50'
          : 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white hover:from-blue-500 hover:to-cyan-500 shadow-lg shadow-blue-500/25'
        }
        ${className}
      `}
    >
      {wallet ? (
        <>
          <Wallet className="w-4 h-4" />
          <span>{formatAddress(wallet.account.address)}</span>
          <LogOut className="w-3 h-3 opacity-60" />
        </>
      ) : (
        <>
          <Wallet className="w-4 h-4" />
          <span>Connect Wallet</span>
        </>
      )}
    </button>
  );
}
