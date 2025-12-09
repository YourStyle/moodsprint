/**
 * Application constants.
 */

export const MOOD_LABELS: Record<number, string> = {
  1: 'Очень плохо',
  2: 'Плохо',
  3: 'Нормально',
  4: 'Хорошо',
  5: 'Отлично',
};

export const ENERGY_LABELS: Record<number, string> = {
  1: 'Истощён',
  2: 'Устал',
  3: 'Норма',
  4: 'Энергичный',
  5: 'На пике',
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
  low: 'bg-green-500/20 text-green-400 border border-green-500/30',
  medium: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  high: 'bg-red-500/20 text-red-400 border border-red-500/30',
};

export const TASK_TYPE_EMOJIS: Record<string, string> = {
  creative: '🎨',
  analytical: '📊',
  communication: '💬',
  physical: '💪',
  learning: '📚',
  planning: '📋',
  coding: '💻',
  writing: '✍️',
};

export const TASK_TYPE_LABELS: Record<string, string> = {
  creative: 'Творческая',
  analytical: 'Аналитическая',
  communication: 'Общение',
  physical: 'Физическая',
  learning: 'Обучение',
  planning: 'Планирование',
  coding: 'Программирование',
  writing: 'Письмо',
};

export const TASK_TYPE_COLORS: Record<string, string> = {
  creative: 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
  analytical: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  communication: 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30',
  physical: 'bg-orange-500/20 text-orange-400 border border-orange-500/30',
  learning: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  planning: 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30',
  coding: 'bg-pink-500/20 text-pink-400 border border-pink-500/30',
  writing: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
};

export const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-gray-500/20 text-gray-400 border border-gray-500/30',
  in_progress: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  completed: 'bg-green-500/20 text-green-400 border border-green-500/30',
  skipped: 'bg-gray-500/20 text-gray-500 border border-gray-500/30',
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
  1: 'Новичок',
  2: 'Стартер',
  3: 'Исследователь',
  4: 'Достигатор',
  5: 'Сфокусированный',
  6: 'Стабильный',
  7: 'Преданный',
  8: 'Опытный',
  9: 'Эксперт',
  10: 'Мастер',
  11: 'Чемпион',
  12: 'Легенда',
  13: 'Гуру',
  14: 'Мудрец',
  15: 'Просветлённый',
};

export const getLevelName = (level: number): string => {
  if (level <= 0) return 'Ученик';
  if (level > 15) return `Трансцендент ${level - 15}`;
  return LEVEL_NAMES[level] || `Уровень ${level}`;
};

export const ACHIEVEMENT_CATEGORIES: Record<string, { label: string; icon: string }> = {
  beginner: { label: 'Первые шаги', icon: '👣' },
  streaks: { label: 'Серии', icon: '🔥' },
  mood: { label: 'Настроение', icon: '❤️' },
  focus: { label: 'Фокус', icon: '🎯' },
  tasks: { label: 'Задачи', icon: '✅' },
  levels: { label: 'Уровни', icon: '📈' },
  daily: { label: 'Ежедневно', icon: '☀️' },
  special: { label: 'Особые', icon: '✨' },
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
