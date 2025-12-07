/**
 * Application constants.
 */

export const MOOD_LABELS: Record<number, string> = {
  1: 'Very Low',
  2: 'Low',
  3: 'Neutral',
  4: 'Good',
  5: 'Great',
};

export const ENERGY_LABELS: Record<number, string> = {
  1: 'Exhausted',
  2: 'Tired',
  3: 'Normal',
  4: 'Energized',
  5: 'Peak',
};

export const MOOD_EMOJIS: Record<number, string> = {
  1: '😔',
  2: '😕',
  3: '😐',
  4: '🙂',
  5: '😊',
};

export const ENERGY_EMOJIS: Record<number, string> = {
  1: '🔋',
  2: '🪫',
  3: '⚡',
  4: '💪',
  5: '🚀',
};

export const PRIORITY_COLORS: Record<string, string> = {
  low: 'bg-green-100 text-green-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-red-100 text-red-800',
};

export const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-800',
  in_progress: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  skipped: 'bg-gray-100 text-gray-500',
};

export const ACHIEVEMENT_ICONS: Record<string, string> = {
  trophy: '🏆',
  star: '⭐',
  crown: '👑',
  target: '🎯',
  bullseye: '🎯',
  clock: '⏰',
  fire: '🔥',
  flame: '🔥',
  medal: '🏅',
  heart: '❤️',
  brain: '🧠',
  rocket: '🚀',
  'trending-up': '📈',
  award: '🏅',
  // New icons for gentle gamification
  footsteps: '👣',
  sparkle: '✨',
  zap: '⚡',
  'heart-hand': '🫶',
  timer: '⏱️',
  'check-circle': '✅',
  layers: '📚',
  sun: '☀️',
  coffee: '☕',
  sunrise: '🌅',
  moon: '🌙',
  shield: '🛡️',
};

export const LEVEL_NAMES: Record<number, string> = {
  1: 'Beginner',
  2: 'Starter',
  3: 'Explorer',
  4: 'Achiever',
  5: 'Focused',
  6: 'Consistent',
  7: 'Dedicated',
  8: 'Skilled',
  9: 'Expert',
  10: 'Master',
  11: 'Champion',
  12: 'Legend',
  13: 'Guru',
  14: 'Sage',
  15: 'Enlightened',
};

export const getLevelName = (level: number): string => {
  if (level <= 0) return 'Novice';
  if (level > 15) return `Transcendent ${level - 15}`;
  return LEVEL_NAMES[level] || `Level ${level}`;
};

export const ACHIEVEMENT_CATEGORIES: Record<string, { label: string; icon: string }> = {
  beginner: { label: 'First Steps', icon: '👣' },
  streaks: { label: 'Streaks', icon: '🔥' },
  mood: { label: 'Mood', icon: '❤️' },
  focus: { label: 'Focus', icon: '🎯' },
  tasks: { label: 'Tasks', icon: '✅' },
  levels: { label: 'Levels', icon: '📈' },
  daily: { label: 'Daily', icon: '☀️' },
  special: { label: 'Special', icon: '✨' },
};

export const DEFAULT_FOCUS_DURATION = 25;
export const MIN_FOCUS_DURATION = 5;
export const MAX_FOCUS_DURATION = 120;

export const XP_REWARDS = {
  SUBTASK_COMPLETE: 10,
  TASK_COMPLETE: 50,
  FOCUS_SESSION: 25,
  MOOD_CHECK: 5,
  DAILY_STREAK_BASE: 20,
};
