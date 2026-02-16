'use client';

import { ReactNode, useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAppStore } from '@/lib/store';
import { authService, moodService, focusService, onboardingService, cardsService } from '@/services';
import type { ReferralRewards } from '@/services/auth';
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
  isMobileApp,
} from '@/lib/telegram';
import { XPPopup } from '@/components/gamification';
import { GenreSelectionModal } from '@/components/GenreSelectionModal';
import { ReferralRewardModal, CardEarnedModal, type EarnedCard } from '@/components/cards';
import { LanguageProvider, useLanguage } from '@/lib/i18n';
import { TonConnectProvider } from '@/components/TonConnectProvider';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60,
      retry: 1,
    },
  },
});

interface ReferralRewardData {
  friendName?: string;
  friendId?: number;
  isReferrer: boolean;
  cards: Array<{
    id: number;
    name: string;
    description?: string;
    genre: string;
    rarity: string;
    hp: number;
    attack: number;
    emoji: string;
    image_url?: string | null;
  }>;
}

function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const {
    user,
    setUser,
    setLoading,
    setLatestMood,
    setActiveSessions,
    setOnboardingCompleted,
    setTelegramEnvironment,
    setAuthError,
    isSpotlightActive,
    onboardingCompleted,
    isLoading,
  } = useAppStore();

  const { t } = useLanguage();
  const [referralRewards, setReferralRewards] = useState<ReferralRewardData[]>([]);
  const [showReferralModal, setShowReferralModal] = useState(false);
  const [pendingReferralRewards, setPendingReferralRewards] = useState<ReferralRewardData[]>([]);
  const [comebackCard, setComebackCard] = useState<EarnedCard | null>(null);
  const [showComebackModal, setShowComebackModal] = useState(false);

  // Show pending referral rewards after BOTH main onboarding AND spotlight complete
  useEffect(() => {
    // Wait for: main onboarding done + spotlight done + have pending rewards + not already showing
    if (onboardingCompleted && !isSpotlightActive && pendingReferralRewards.length > 0 && !showReferralModal) {
      setReferralRewards(prev => [...prev, ...pendingReferralRewards]);
      setPendingReferralRewards([]);
      setTimeout(() => setShowReferralModal(true), 500);
    }
  }, [onboardingCompleted, isSpotlightActive, pendingReferralRewards, showReferralModal]);

  // Check for pending referral rewards in background (non-blocking)
  const checkPendingRewardsInBackground = () => {
    // Fire and forget - don't await
    (async () => {
      try {
        const pendingResult = await cardsService.getPendingRewards();
        if (pendingResult.success && pendingResult.data && pendingResult.data.rewards.length > 0) {
          const rewards = pendingResult.data.rewards;
          // Group rewards - each reward is one friend invitation
          const rewardsToShow: ReferralRewardData[] = rewards
            .filter(r => r.card) // Only show if card exists
            .map(r => ({
              isReferrer: r.is_referrer,
              friendName: r.friend_name || undefined,
              friendId: r.friend_id,
              cards: r.card ? [{
                id: r.card.id,
                name: r.card.name,
                description: r.card.description || undefined,
                genre: r.card.genre,
                rarity: r.card.rarity,
                hp: r.card.hp,
                attack: r.card.attack,
                emoji: r.card.emoji,
                image_url: r.card.image_url,
              }] : [],
            }));

          if (rewardsToShow.length > 0) {
            // Check if spotlight is active (first visit) - if so, queue rewards for later
            const isFirstVisit = !localStorage.getItem('first_visit_completed');
            if (isFirstVisit) {
              // Queue rewards to show after spotlight completes
              setPendingReferralRewards(prev => [...prev, ...rewardsToShow]);
            } else {
              // Show immediately for returning users
              setReferralRewards(prev => [...prev, ...rewardsToShow]);
              setTimeout(() => setShowReferralModal(true), 800);
            }
            // Mark rewards as claimed
            await cardsService.claimPendingRewards();
          }
        }
      } catch (err) {
        console.log('[Referral] Failed to fetch pending rewards:', err);
      }
    })();
  };

  useEffect(() => {
    const initAuth = async () => {
      // Check for dev mode via URL parameter (allows non-TG login)
      const urlParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
      const isDevMode = urlParams?.get('dev') === 'true';

      // Detect Telegram environment
      const isTg = isTelegramWebApp();
      const isTelegramEnv = isTg && !isDevMode;
      setTelegramEnvironment(isTelegramEnv);

      // Add/remove telegram-env class for safe-area CSS
      if (isTelegramEnv) {
        document.body.classList.add('telegram-env');
      } else {
        document.body.classList.remove('telegram-env');
      }

      // Initialize Telegram WebApp
      if (isTg) {
        readyTelegramWebApp();

        // Dynamic safe area: read actual values from Telegram WebApp API
        const updateSafeArea = () => {
          const webApp = (window as any).Telegram?.WebApp;
          if (!webApp) return;
          const systemTop = webApp.safeAreaInset?.top ?? 0;
          const contentTop = webApp.contentSafeAreaInset?.top ?? 0;
          const totalTop = systemTop + contentTop;
          if (totalTop > 0) {
            document.documentElement.style.setProperty('--tg-safe-area-top', `${totalTop}px`);
          }
        };
        updateSafeArea();
        // Re-check after expand/fullscreen since values may change
        setTimeout(updateSafeArea, 200);
        setTimeout(updateSafeArea, 500);
        const webAppRef = (window as any).Telegram?.WebApp;
        if (webAppRef?.onEvent) {
          webAppRef.onEvent('viewportChanged', updateSafeArea);
          webAppRef.onEvent('safeAreaChanged', updateSafeArea);
          webAppRef.onEvent('contentSafeAreaChanged', updateSafeArea);
        }

        // Expand immediately and retry after delays
        // This is needed because keyboard buttons may open in compact mode
        expandTelegramWebApp();
        setTimeout(() => expandTelegramWebApp(), 50);
        setTimeout(() => expandTelegramWebApp(), 150);

        enableClosingConfirmation();

        // Full screen and disable swipes only for mobile devices
        if (isMobileDevice()) {
          disableVerticalSwipes();
          // Delay requestFullscreen to ensure WebApp is fully initialized
          // This helps when opening from keyboard buttons on Android
          setTimeout(() => {
            expandTelegramWebApp();
            requestFullscreen();
          }, 100);
          // Extra retry for stubborn cases
          setTimeout(() => {
            expandTelegramWebApp();
            requestFullscreen();
          }, 300);
        }

      }

      try {
        // Try to authenticate
        const initData = getTelegramInitData();

        console.log('[Auth] isTelegramWebApp:', isTg);
        console.log('[Auth] initData exists:', !!initData);
        console.log('[Auth] isDevMode:', isDevMode);

        // Parse referrer from startParam before authentication
        const startParam = getStartParam();
        console.log('[Referral] startParam:', startParam);
        console.log('[Referral] URL:', typeof window !== 'undefined' ? window.location.href : 'SSR');

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

        if (initData && !isDevMode) {
          // Authenticate with Telegram (pass referrer_id for new users)
          console.log('[Auth] Authenticating with Telegram...');
          const result = await authService.authenticateTelegram(initData, referrerId);
          console.log('[Auth] Result:', result.success, result.error);
          if (result.success && result.data) {
            setUser(result.data.user);
            authenticated = true;
            isNewUser = result.data.is_new_user || false;

            // Handle referral rewards for invitee (after joining via invite)
            if (result.data.friendship_created && result.data.referral_rewards) {
              const rewards = result.data.referral_rewards;
              const cards = rewards.invitee_starter_deck || [];
              if (cards.length > 0) {
                const rewardData: ReferralRewardData = {
                  isReferrer: false,
                  friendName: rewards.referrer_name,
                  cards: cards,
                };
                // New users will have spotlight - queue rewards for after completion
                setPendingReferralRewards(prev => [...prev, rewardData]);
              }
            }

            // Handle comeback card for returning users
            if (result.data.comeback_card) {
              setComebackCard(result.data.comeback_card);
              setTimeout(() => setShowComebackModal(true), 1000);
            }

            // Check for pending referral rewards in background (non-blocking)
            checkPendingRewardsInBackground();
          }
        } else if (process.env.NODE_ENV === 'development' || isDevMode) {
          // Dev mode: use dev auth (also available in production via ?dev=true&secret=XXX)
          console.log('[Auth] Using dev authentication...');
          const devSecret = urlParams?.get('secret') || undefined;
          const result = await authService.devAuthenticate(undefined, undefined, devSecret);
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

            // Check if spotlight should be reset (admin triggered)
            const profile = onboardingResult.data.profile;
            if (profile?.spotlight_reset_at) {
              const serverResetAt = new Date(profile.spotlight_reset_at).getTime();
              const localResetAt = parseInt(
                localStorage.getItem('spotlight_last_reset') || '0',
                10
              );

              if (serverResetAt > localResetAt) {
                // Clear all spotlight onboarding localStorage entries
                const keysToRemove: string[] = [];
                for (let i = 0; i < localStorage.length; i++) {
                  const key = localStorage.key(i);
                  if (key?.startsWith('onboarding_')) {
                    keysToRemove.push(key);
                  }
                }
                keysToRemove.forEach(key => localStorage.removeItem(key));
                // Store the new reset timestamp
                localStorage.setItem('spotlight_last_reset', serverResetAt.toString());
                console.log('[Spotlight] Reset triggered by admin, cleared localStorage');
              }
            }

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

          // Handle guild invite deep link
          if (startParam && startParam.startsWith('guild_')) {
            const guildId = parseInt(startParam.replace('guild_', ''), 10);
            if (!isNaN(guildId) && guildId > 0) {
              const guildHandledKey = `guild_invite_handled_${guildId}`;
              const alreadyHandled = sessionStorage.getItem(guildHandledKey);

              if (!alreadyHandled) {
                console.log('[Deeplink] Guild invite:', guildId);
                sessionStorage.setItem(guildHandledKey, 'true');

                // Redirect to guilds page with invite guild parameter
                router.push(`/guilds?invite_guild=${guildId}`);
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
        setAuthError(true);
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, [
    setUser,
    setLoading,
    setAuthError,
    setLatestMood,
    setActiveSessions,
    setOnboardingCompleted,
    router,
    pathname,
  ]);

  // Check onboarding status when user logs in via website (after initAuth completed)
  // This handles the case where user authenticates via email/password from landing page
  useEffect(() => {
    const checkOnboardingAfterWebLogin = async () => {
      // Only run if: user exists, loading is done, and onboardingCompleted is still null (not checked yet)
      if (user && !isLoading && onboardingCompleted === null) {
        try {
          const onboardingResult = await onboardingService.getStatus();
          if (onboardingResult.success && onboardingResult.data) {
            const completed = onboardingResult.data.completed;
            setOnboardingCompleted(completed);

            // Redirect to onboarding if not completed
            if (!completed && pathname !== '/onboarding') {
              router.push('/onboarding');
            }
          }
        } catch (err) {
          console.error('[WebLogin] Failed to check onboarding status:', err);
        }
      }
    };

    checkOnboardingAfterWebLogin();
  }, [user, isLoading, onboardingCompleted, setOnboardingCompleted, pathname, router]);

  return (
    <>
      {children}
      <ReferralRewardModal
        isOpen={showReferralModal}
        rewards={referralRewards}
        onClose={() => {
          setShowReferralModal(false);
          setReferralRewards([]);
        }}
      />
      <CardEarnedModal
        isOpen={showComebackModal}
        card={comebackCard}
        onClose={() => {
          setShowComebackModal(false);
          setComebackCard(null);
        }}
        t={t}
      />
    </>
  );
}

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <TonConnectProvider>
        <LanguageProvider>
          <AuthProvider>
            {children}
            <XPPopup />
            <GenreSelectionModal />
          </AuthProvider>
        </LanguageProvider>
      </TonConnectProvider>
    </QueryClientProvider>
  );
}
