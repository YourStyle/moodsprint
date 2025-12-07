'use client';

import { ReactNode, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAppStore } from '@/lib/store';
import { authService, moodService, focusService } from '@/services';
import {
  getTelegramInitData,
  isTelegramWebApp,
  readyTelegramWebApp,
  expandTelegramWebApp,
} from '@/lib/telegram';
import { XPPopup } from '@/components/gamification';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60,
      retry: 1,
    },
  },
});

function AuthProvider({ children }: { children: ReactNode }) {
  const { setUser, setLoading, setLatestMood, setActiveSession } = useAppStore();

  useEffect(() => {
    const initAuth = async () => {
      // Initialize Telegram WebApp
      if (isTelegramWebApp()) {
        readyTelegramWebApp();
        expandTelegramWebApp();
      }

      try {
        // Try to authenticate
        const initData = getTelegramInitData();

        if (initData) {
          // Authenticate with Telegram
          const result = await authService.authenticateTelegram(initData);
          if (result.success && result.data) {
            setUser(result.data.user);
          }
        } else if (process.env.NODE_ENV === 'development') {
          // Dev mode: use dev auth
          const result = await authService.devAuthenticate();
          if (result.success && result.data) {
            setUser(result.data.user);
          }
        } else {
          // Try existing token
          const result = await authService.getCurrentUser();
          if (result.success && result.data) {
            setUser(result.data.user);
          }
        }

        // Load initial data
        const [moodResult, focusResult] = await Promise.all([
          moodService.getLatestMood(),
          focusService.getActiveSession(),
        ]);

        if (moodResult.success && moodResult.data?.mood_check) {
          setLatestMood(moodResult.data.mood_check);
        }

        if (focusResult.success && focusResult.data?.session) {
          setActiveSession(focusResult.data.session);
        }
      } catch (error) {
        console.error('Auth initialization failed:', error);
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, [setUser, setLoading, setLatestMood, setActiveSession]);

  return <>{children}</>;
}

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        {children}
        <XPPopup />
      </AuthProvider>
    </QueryClientProvider>
  );
}
