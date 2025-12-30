'use client';

import { ReactNode } from 'react';
import { TonConnectUIProvider } from '@tonconnect/ui-react';

interface TonConnectProviderProps {
  children: ReactNode;
}

export function TonConnectProvider({ children }: TonConnectProviderProps) {
  // Use relative URL for manifest - works in both dev and prod
  const manifestUrl =
    typeof window !== 'undefined'
      ? `${window.location.origin}/tonconnect-manifest.json`
      : '/tonconnect-manifest.json';

  return (
    <TonConnectUIProvider manifestUrl={manifestUrl}>
      {children}
    </TonConnectUIProvider>
  );
}
