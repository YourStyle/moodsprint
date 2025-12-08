'use client';

import { ReactNode, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAppStore } from '@/lib/store';
import { authService, moodService, focusService, onboardingService } from '@/services';
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
  const router = useRouter();
  const pathname = usePathname();
  const {
    setUser,
    setLoading,
    setLatestMood,
    setActiveSession,
    setOnboardingCompleted,
  } = useAppStore();

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
        const isTg = isTelegramWebApp();

        console.log('[Auth] isTelegramWebApp:', isTg);
        console.log('[Auth] initData exists:', !!initData);

        let authenticated = false;

        if (initData) {
          // Authenticate with Telegram
          console.log('[Auth] Authenticating with Telegram...');
          const result = await authService.authenticateTelegram(initData);
          console.log('[Auth] Result:', result.success, result.error);
          if (result.success && result.data) {
            setUser(result.data.user);
            authenticated = true;
          }
        } else if (process.env.NODE_ENV === 'development') {
          // Dev mode: use dev auth
          const result = await authService.devAuthenticate();
          if (result.success && result.data) {
            setUser(result.data.user);
            authenticated = true;
          }
        } else {
          // Try existing token
          const result = await authService.getCurrentUser();
          if (result.success && result.data) {
            setUser(result.data.user);
            authenticated = true;
          }
        }

        // Check onboarding status if authenticated
        if (authenticated) {
          const onboardingResult = await onboardingService.getStatus();
          if (onboardingResult.success && onboardingResult.data) {
            const completed = onboardingResult.data.completed;
            setOnboardingCompleted(completed);

            // Redirect to onboarding if not completed and not already there
            if (!completed && pathname !== '/onboarding') {
              router.push('/onboarding');
            }
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
  }, [
    setUser,
    setLoading,
    setLatestMood,
    setActiveSession,
    setOnboardingCompleted,
    router,
    pathname,
  ]);

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
