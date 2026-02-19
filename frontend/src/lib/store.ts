/**
 * Global state store using Zustand.
 */

import { create } from 'zustand';
import type { User, FocusSession, MoodCheck } from '@/domain/types';

interface AppState {
  // Auth
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  authError: boolean;
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  setAuthError: (error: boolean) => void;

  // Telegram environment detection
  isTelegramEnvironment: boolean;
  setTelegramEnvironment: (isTelegram: boolean) => void;

  // Onboarding
  onboardingCompleted: boolean | null;
  setOnboardingCompleted: (completed: boolean) => void;

  // Active focus sessions (multiple)
  activeSessions: FocusSession[];
  setActiveSessions: (sessions: FocusSession[]) => void;
  addActiveSession: (session: FocusSession) => void;
  updateActiveSession: (session: FocusSession) => void;
  removeActiveSession: (sessionId: number) => void;
  getSessionForTask: (taskId: number) => FocusSession | undefined;

  // Legacy single session support (backward compatibility)
  activeSession: FocusSession | null;
  setActiveSession: (session: FocusSession | null) => void;

  // Latest mood
  latestMood: MoodCheck | null;
  setLatestMood: (mood: MoodCheck | null) => void;

  // UI
  showMoodModal: boolean;
  setShowMoodModal: (show: boolean) => void;
  hideNavigation: boolean;
  setHideNavigation: (hide: boolean) => void;

  // Spotlight onboarding state (blocks other modals when active)
  isSpotlightActive: boolean;
  setSpotlightActive: (active: boolean) => void;

  // XP toast queue (unified player + companion toasts)
  xpToastQueue: Array<{
    id: number;
    type: 'player' | 'companion';
    amount: number;
    // player fields
    currentXp?: number;
    xpForNext?: number;
    level?: number;
    // companion fields
    cardEmoji?: string;
    cardName?: string;
    cardXp?: number;
    cardXpForNext?: number;
    cardLevel?: number;
    levelUp?: boolean;
  }>;
  pushXPToast: (toast: Omit<AppState['xpToastQueue'][0], 'id'>) => void;
  shiftXPToast: () => void;

  // Legacy XP animation (kept for backward compat during migration)
  xpAnimation: { amount: number; show: boolean };
  showXPAnimation: (amount: number) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  // Auth
  user: null,
  isAuthenticated: false,
  isLoading: true,
  authError: false,
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  setLoading: (isLoading) => set({ isLoading }),
  setAuthError: (authError) => set({ authError }),

  // Telegram environment
  isTelegramEnvironment: true, // Default to true, will be set on init
  setTelegramEnvironment: (isTelegramEnvironment) => set({ isTelegramEnvironment }),

  // Onboarding
  onboardingCompleted: null,
  setOnboardingCompleted: (onboardingCompleted) => set({ onboardingCompleted }),

  // Active focus sessions (multiple)
  activeSessions: [],
  setActiveSessions: (activeSessions) => set({
    activeSessions,
    activeSession: activeSessions[0] || null
  }),
  addActiveSession: (session) => set((state) => ({
    activeSessions: [...state.activeSessions, session],
    activeSession: state.activeSessions.length === 0 ? session : state.activeSession
  })),
  updateActiveSession: (session) => set((state) => ({
    activeSessions: state.activeSessions.map(s => s.id === session.id ? session : s),
    activeSession: state.activeSession?.id === session.id ? session : state.activeSession
  })),
  removeActiveSession: (sessionId) => set((state) => {
    const newSessions = state.activeSessions.filter(s => s.id !== sessionId);
    return {
      activeSessions: newSessions,
      activeSession: state.activeSession?.id === sessionId ? (newSessions[0] || null) : state.activeSession
    };
  }),
  getSessionForTask: (taskId) => {
    const state = get();
    return state.activeSessions.find(s => s.task_id === taskId);
  },

  // Legacy single session support
  activeSession: null,
  setActiveSession: (session) => set((state) => {
    if (session) {
      // Add or update in activeSessions
      const exists = state.activeSessions.find(s => s.id === session.id);
      if (exists) {
        return {
          activeSession: session,
          activeSessions: state.activeSessions.map(s => s.id === session.id ? session : s)
        };
      } else {
        return {
          activeSession: session,
          activeSessions: [...state.activeSessions, session]
        };
      }
    } else {
      return { activeSession: null };
    }
  }),

  // Latest mood
  latestMood: null,
  setLatestMood: (latestMood) => set({ latestMood }),

  // UI
  showMoodModal: false,
  setShowMoodModal: (showMoodModal) => set({ showMoodModal }),
  hideNavigation: false,
  setHideNavigation: (hideNavigation) => set({ hideNavigation }),

  // Spotlight onboarding state
  isSpotlightActive: false,
  setSpotlightActive: (isSpotlightActive) => set({ isSpotlightActive }),

  // XP toast queue
  xpToastQueue: [],
  pushXPToast: (toast) => set((state) => ({
    xpToastQueue: [...state.xpToastQueue, { ...toast, id: Date.now() + Math.random() }],
  })),
  shiftXPToast: () => set((state) => ({
    xpToastQueue: state.xpToastQueue.slice(1),
  })),

  // Legacy XP animation (still used by focus page)
  xpAnimation: { amount: 0, show: false },
  showXPAnimation: (amount) => {
    set({ xpAnimation: { amount, show: true } });
    setTimeout(() => {
      set({ xpAnimation: { amount: 0, show: false } });
    }, 2000);
  },
}));
