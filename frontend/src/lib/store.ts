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
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;

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

  // XP animation
  xpAnimation: { amount: number; show: boolean };
  showXPAnimation: (amount: number) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  // Auth
  user: null,
  isAuthenticated: false,
  isLoading: true,
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  setLoading: (isLoading) => set({ isLoading }),

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

  // XP animation
  xpAnimation: { amount: 0, show: false },
  showXPAnimation: (amount) => {
    set({ xpAnimation: { amount, show: true } });
    setTimeout(() => {
      set({ xpAnimation: { amount: 0, show: false } });
    }, 2000);
  },
}));
