'use client';

import { ReactNode, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAppStore } from '@/lib/store';
import { authService, moodService, focusService, onboardingService, cardsService } from '@/services';
import {
  getTelegramInitData,
  isTelegramWebApp,
  readyTelegramWebApp,
  expandTelegramWebApp,
  requestFullscreen,
  enableClosingConfirmation,
  disableVerticalSwipes,
  isMobileDevice,
  isIOSDevice,
  getStartParam,
} from '@/lib/telegram';
import { XPPopup } from '@/components/gamification';
import { GenreSelectionModal } from '@/components/GenreSelectionModal';
import { LanguageProvider } from '@/lib/i18n';

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
    setActiveSessions,
    setOnboardingCompleted,
  } = useAppStore();

  useEffect(() => {
    const initAuth = async () => {
      // Initialize Telegram WebApp
      if (isTelegramWebApp()) {
        readyTelegramWebApp();
        expandTelegramWebApp();
        enableClosingConfirmation();

        // Full screen and disable swipes only for mobile devices
        if (isMobileDevice()) {
          requestFullscreen();
          disableVerticalSwipes();
        }

        // Set safe area only for iOS (Android doesn't need it)
        if (!isIOSDevice()) {
          document.documentElement.style.setProperty('--safe-area-top', '0px');
        }
      }

      try {
        // Try to authenticate
        const initData = getTelegramInitData();
        const isTg = isTelegramWebApp();

        console.log('[Auth] isTelegramWebApp:', isTg);
        console.log('[Auth] initData exists:', !!initData);

        // Parse referrer from startParam before authentication
        const startParam = getStartParam();
        let referrerId: number | undefined;
        if (startParam && startParam.startsWith('invite_')) {
          referrerId = parseInt(startParam.replace('invite_', ''), 10);
          if (isNaN(referrerId) || referrerId <= 0) {
            referrerId = undefined;
          } else {
            console.log('[Referral] Found referrer:', referrerId);
          }
        }

        let authenticated = false;
        let isNewUser = false;

        if (initData) {
          // Authenticate with Telegram (pass referrer_id for new users)
          console.log('[Auth] Authenticating with Telegram...');
          const result = await authService.authenticateTelegram(initData, referrerId);
          console.log('[Auth] Result:', result.success, result.error);
          if (result.success && result.data) {
            setUser(result.data.user);
            authenticated = true;
            isNewUser = result.data.is_new_user || false;
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

          // For existing users who clicked invite link, auto-connect with referrer
          // Only do this once per session (check sessionStorage)
          if (!isNewUser && referrerId) {
            const referralHandledKey = `referral_handled_${referrerId}`;
            const alreadyHandled = sessionStorage.getItem(referralHandledKey);

            if (!alreadyHandled) {
              console.log('[Deeplink] Existing user, connecting with referrer:', referrerId);
              sessionStorage.setItem(referralHandledKey, 'true');

              try {
                const result = await cardsService.connectWithReferrer(referrerId);
                if (result.success) {
                  console.log('[Deeplink] Connected with referrer:', result.data?.message);
                  // Only redirect to friends if onboarding is completed and not already there
                  const onboardingResult = await onboardingService.getStatus();
                  if (onboardingResult.data?.completed && pathname !== '/friends') {
                    router.push('/friends');
                  }
                }
              } catch (err) {
                console.log('[Deeplink] Failed to connect with referrer:', err);
              }
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

        if (focusResult.success && focusResult.data?.sessions) {
          setActiveSessions(focusResult.data.sessions);
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
    setActiveSessions,
    setOnboardingCompleted,
    router,
    pathname,
  ]);

  return <>{children}</>;
}

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <LanguageProvider>
        <AuthProvider>
          {children}
          <XPPopup />
          <GenreSelectionModal />
        </AuthProvider>
      </LanguageProvider>
    </QueryClientProvider>
  );
}
