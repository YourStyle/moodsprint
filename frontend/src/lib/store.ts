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

  // Active focus session
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

export const useAppStore = create<AppState>((set) => ({
  // Auth
  user: null,
  isAuthenticated: false,
  isLoading: true,
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  setLoading: (isLoading) => set({ isLoading }),

  // Active focus session
  activeSession: null,
  setActiveSession: (activeSession) => set({ activeSession }),

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
