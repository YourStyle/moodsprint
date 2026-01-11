/**
 * Domain types for MoodSprint application.
 * This file contains all TypeScript interfaces used across the app.
 */

// ============ User ============

export interface User {
  id: number;
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  photo_url: string | null;
  xp: number;
  level: number;
  xp_for_next_level: number;
  xp_progress_percent: number;
  streak_days: number;
  longest_streak: number;
  sparks: number;
  ton_wallet_address: string | null;
  created_at: string;
}

// ============ Tasks ============

export type TaskStatus = 'pending' | 'in_progress' | 'completed';
export type TaskPriority = 'low' | 'medium' | 'high';
export type TaskType =
  | 'creative'
  | 'analytical'
  | 'communication'
  | 'physical'
  | 'learning'
  | 'planning'
  | 'coding'
  | 'writing';

export interface Task {
  id: number;
  user_id: number;
  title: string;
  description: string | null;
  priority: TaskPriority;
  status: TaskStatus;
  due_date: string | null;
  task_type: TaskType | null;
  preferred_time: string | null;
  scheduled_at: string | null;
  subtasks_count: number;
  subtasks_completed: number;
  progress_percent: number;
  created_at: string;
  updated_at: string | null;
  completed_at: string | null;
  subtasks?: Subtask[];
}

export type PreferredTime = 'morning' | 'afternoon' | 'evening' | 'night';

export interface CreateTaskInput {
  title: string;
  description?: string;
  priority?: TaskPriority;
  due_date?: string;
  preferred_time?: PreferredTime;
  scheduled_at?: string;
}

export interface UpdateTaskInput {
  title?: string;
  description?: string;
  priority?: TaskPriority;
  status?: TaskStatus;
  due_date?: string;
  task_type?: TaskType;
  scheduled_at?: string | null;
}

// ============ Subtasks ============

export type SubtaskStatus = 'pending' | 'in_progress' | 'completed' | 'skipped';

export interface Subtask {
  id: number;
  task_id: number;
  title: string;
  order: number;
  estimated_minutes: number;
  status: SubtaskStatus;
  created_at: string;
  updated_at: string | null;
  completed_at: string | null;
}

export interface UpdateSubtaskInput {
  title?: string;
  status?: SubtaskStatus;
  estimated_minutes?: number;
}

export interface SubtaskSuggestion {
  subtask_id: number;
  title: string;
  estimated_minutes: number;
}

export interface TaskSuggestion {
  type: 'task' | 'subtasks';
  task_id: number;
  task_title: string;
  priority: TaskPriority;
  estimated_minutes: number;
  subtasks_count?: number;
  subtasks?: SubtaskSuggestion[];
  score: number;
  fit_quality: 'perfect' | 'good' | 'partial' | 'estimated';
}

// ============ Mood ============

export type MoodLevel = 1 | 2 | 3 | 4 | 5;
export type EnergyLevel = 1 | 2 | 3 | 4 | 5;
export type DecompositionStrategy = 'micro' | 'gentle' | 'careful' | 'standard';

export interface MoodCheck {
  id: number;
  user_id: number;
  mood: MoodLevel;
  mood_label: string;
  energy: EnergyLevel;
  energy_label: string;
  note: string | null;
  strategy: DecompositionStrategy;
  recommended_step_minutes: [number, number];
  created_at: string;
}

export interface CreateMoodInput {
  mood: MoodLevel;
  energy: EnergyLevel;
  note?: string;
}

export interface MoodHistoryDay {
  date: string;
  checks: MoodCheck[];
  average_mood: number;
  average_energy: number;
}

// ============ Focus Sessions ============

export type FocusSessionStatus = 'active' | 'completed' | 'cancelled' | 'paused';

export interface FocusSession {
  id: number;
  user_id: number;
  task_id: number | null;
  subtask_id: number | null;
  subtask_title?: string;
  task_title?: string;
  planned_duration_minutes: number;
  actual_duration_minutes: number | null;
  elapsed_minutes: number;
  remaining_minutes: number;
  is_overtime: boolean;
  status: FocusSessionStatus;
  started_at: string;
  ended_at: string | null;
}

export interface StartFocusInput {
  subtask_id?: number;
  task_id?: number;
  planned_duration_minutes?: number;
}

// ============ Gamification ============

export type AchievementCategory =
  | 'beginner'
  | 'streaks'
  | 'mood'
  | 'focus'
  | 'tasks'
  | 'levels'
  | 'daily'
  | 'special';

export interface Achievement {
  id: number;
  code: string;
  title: string;
  description: string;
  xp_reward: number;
  icon: string;
  category: AchievementCategory;
  progress_max: number | null;
  is_hidden: boolean;
}

export interface UserAchievement extends Achievement {
  progress: number;
  unlocked_at: string | null;
  is_unlocked: boolean;
}

export interface DailyGoal {
  type: 'focus_minutes' | 'subtasks' | 'mood_check';
  title: string;
  target: number;
  current: number;
  completed: boolean;
}

export interface UserStats {
  xp: number;
  level: number;
  level_name: string;
  xp_for_next_level: number;
  xp_progress_percent: number;
  streak_days: number;
  longest_streak: number;
  total_tasks_completed: number;
  total_subtasks_completed: number;
  total_focus_minutes: number;
  today: {
    tasks_completed: number;
    subtasks_completed: number;
    focus_minutes: number;
    mood_checks: number;
  };
}

export interface HourStats {
  hour: number;
  sessions: number;
  completed: number;
  success_rate?: number;
  avg_minutes?: number;
}

export interface DayStats {
  day: number;
  day_name: string;
  sessions: number;
  completed: number;
  success_rate: number;
  avg_minutes: number;
}

export interface ProductivityPatterns {
  period_days: number;
  total_sessions: number;
  total_completed: number;
  total_focus_minutes: number;
  overall_success_rate: number;
  avg_session_duration: number;
  productivity_time: 'morning' | 'afternoon' | 'evening' | 'night' | 'varies';
  best_hours: HourStats[];
  best_day: DayStats | null;
  day_distribution: DayStats[];
  hour_distribution: HourStats[];
}

export interface LeaderboardEntry {
  rank: number;
  user_id: number;
  username: string;
  first_name: string | null;
  monsters_killed: number;
  level: number;
  streak_days: number;
}

// ============ User Profile (Onboarding) ============

export type ProductivityType = 'sprinter' | 'marathoner' | 'balanced' | 'explorer';
export type WorkStyle = 'structured' | 'flexible' | 'deadline_driven' | 'creative';
export type MotivationStyle = 'gentle' | 'encouraging' | 'challenging' | 'data_driven';

export interface UserProfile {
  id: number;
  user_id: number;
  productivity_type: ProductivityType | null;
  preferred_time: string | null;
  work_style: WorkStyle | null;
  favorite_task_types: string[] | null;
  main_challenges: string[] | null;
  productivity_goals: string | null;
  preferred_session_duration: number;
  notifications_enabled: boolean;
  daily_reminder_time: string | null;
  onboarding_completed: boolean;
  onboarding_completed_at: string | null;
  gpt_analysis: GptAnalysis | null;
  // Work schedule preferences
  work_start_time: string | null;
  work_end_time: string | null;
  work_days: number[] | null;
  timezone: string | null;
  // Gamification
  favorite_genre: 'magic' | 'fantasy' | 'scifi' | 'cyberpunk' | 'anime' | null;
  // Spotlight reset (set by admin to force re-show)
  spotlight_reset_at: string | null;
}

export interface GptAnalysis {
  productivity_type: ProductivityType;
  preferred_time: string;
  work_style: WorkStyle;
  favorite_task_types: string[];
  main_challenges: string[];
  personalized_tips: string[];
  motivation_style: MotivationStyle;
  recommended_session_duration: number;
}

export interface OnboardingInput {
  productive_time: 'morning' | 'afternoon' | 'evening' | 'night' | 'varies';
  favorite_tasks: string[];
  challenges: string[];
  work_description?: string;
  goals?: string;
}

export interface ReferralRewardCard {
  id: number;
  name: string;
  description: string | null;
  genre: string;
  rarity: 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary';
  hp: number;
  attack: number;
  emoji: string;
}

export interface ReferralRewards {
  starter_deck?: ReferralRewardCard[];
  referrer_rewarded?: boolean;
  referrer_card_rarity?: string;
}

export interface OnboardingResponse {
  profile: UserProfile;
  analysis: {
    productivity_type: ProductivityType;
    work_style: WorkStyle;
    personalized_tips: string[];
    motivation_style: MotivationStyle;
    recommended_session_duration: number;
  };
  welcome_message: string;
  referral_rewards?: ReferralRewards;
}

// ============ API Responses ============

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: {
    code: string;
    message: string;
    details?: Record<string, string>;
  };
}

export interface XPReward {
  xp_earned: number;
  achievements_unlocked: Achievement[];
}

// ============ Card Abilities ============

export type CardAbility = 'heal' | 'double_strike' | 'shield' | 'poison';

export interface AbilityInfo {
  type: CardAbility;
  name: string;
  description: string;
  emoji: string;
  cooldown: number;
  current_cooldown: number;
}

export interface Card {
  id: number;
  user_id: number;
  template_id: number | null;
  name: string;
  description: string | null;
  genre: string;
  rarity: 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary';
  hp: number;
  attack: number;
  current_hp: number;
  ability: CardAbility | null;
  ability_info: AbilityInfo | null;
  image_url: string | null;
  emoji: string;
  is_in_deck: boolean;
  is_tradeable: boolean;
  is_alive: boolean;
  rarity_color: string;
  created_at: string;
}

export interface BattleCard {
  id: number | string;
  name: string;
  emoji: string;
  image_url?: string;
  hp: number;
  max_hp: number;
  attack: number;
  rarity?: string;
  genre?: string;
  alive: boolean;
  ability?: CardAbility;
  ability_info?: AbilityInfo;
  ability_cooldown?: number;
  has_shield?: boolean;
  status_effects?: StatusEffect[];
}

export interface StatusEffect {
  type: 'poison';
  damage: number;
  turns_left: number;
  source: string;
}

// ============ Merge System ============

export interface MergeChances {
  chances: Record<string, number>;
  bonuses: MergeBonus[];
  can_merge: boolean;
}

export interface MergeBonus {
  type: 'same_genre' | 'both_abilities' | 'high_attack';
  value: string;
}

export interface MergeResult {
  success: boolean;
  new_card: Card;
  merged_cards: string[];
  rarity_upgrade: boolean;
  message: string;
}

export interface MergeLog {
  id: number;
  user_id: number;
  card1_name: string;
  card1_rarity: string;
  card2_name: string;
  card2_rarity: string;
  result_card: Card | null;
  result_rarity: string;
  created_at: string;
}

// ============ Seasonal Events ============

export type EventType = 'seasonal' | 'manual' | 'special';

export interface SeasonalEvent {
  id: number;
  code: string;
  name: string;
  description: string | null;
  event_type: EventType;
  start_date: string;
  end_date: string;
  banner_url: string | null;
  theme_color: string;
  emoji: string;
  is_active: boolean;
  is_currently_active: boolean;
  xp_multiplier: number;
  days_remaining: number;
}

export interface EventMonster {
  id: number;
  event_id: number;
  monster: Monster;
  appear_day: number;
  exclusive_reward_name: string | null;
  guaranteed_rarity: string | null;
  times_defeated: number;
}

export interface UserEventProgress {
  id: number;
  user_id: number;
  event_id: number;
  monsters_defeated: number;
  bosses_defeated: number;
  exclusive_cards_earned: number;
  milestones: string[];
}

export interface EventMilestone {
  code: string;
  title: string;
  xp_reward: number;
}

// ============ Monster ============

export interface Monster {
  id: number;
  name: string;
  description: string | null;
  genre: string;
  level: number;
  hp: number;
  attack: number;
  defense: number;
  speed: number;
  xp_reward: number;
  stat_points_reward: number;
  sprite_url: string | null;
  emoji: string;
  is_boss: boolean;
}

// ============ Telegram ============

export interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  language_code?: string;
}

export interface SafeAreaInsets {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

export interface TelegramViewport {
  height: number;
  stableHeight: number;
  isExpanded: boolean;
  safeAreaInsets: () => SafeAreaInsets;
  contentSafeAreaInsets: () => SafeAreaInsets;
  safeAreaInsetTop: () => number;
  safeAreaInsetBottom: () => number;
  safeAreaInsetLeft: () => number;
  safeAreaInsetRight: () => number;
  contentSafeAreaInsetTop: () => number;
  contentSafeAreaInsetBottom: () => number;
  contentSafeAreaInsetLeft: () => number;
  contentSafeAreaInsetRight: () => number;
}

export interface TelegramWebApp {
  initData: string;
  initDataUnsafe: {
    query_id?: string;
    user?: TelegramUser;
    auth_date: number;
    hash: string;
    start_param?: string;
  };
  version: string;
  platform: string;
  colorScheme: 'light' | 'dark';
  themeParams: {
    bg_color?: string;
    text_color?: string;
    hint_color?: string;
    link_color?: string;
    button_color?: string;
    button_text_color?: string;
    secondary_bg_color?: string;
  };
  isExpanded: boolean;
  isFullscreen: boolean;
  isClosingConfirmationEnabled: boolean;
  isVerticalSwipesEnabled: boolean;
  viewportHeight: number;
  viewportStableHeight: number;
  headerColor: string;
  backgroundColor: string;
  viewport?: TelegramViewport;
  ready: () => void;
  expand: () => void;
  close: () => void;
  requestFullscreen: () => void;
  exitFullscreen: () => void;
  enableClosingConfirmation: () => void;
  disableClosingConfirmation: () => void;
  enableVerticalSwipes: () => void;
  disableVerticalSwipes: () => void;
  MainButton: {
    text: string;
    color: string;
    textColor: string;
    isVisible: boolean;
    isActive: boolean;
    isProgressVisible: boolean;
    setText: (text: string) => void;
    onClick: (callback: () => void) => void;
    offClick: (callback: () => void) => void;
    show: () => void;
    hide: () => void;
    enable: () => void;
    disable: () => void;
    showProgress: (leaveActive?: boolean) => void;
    hideProgress: () => void;
  };
  BackButton: {
    isVisible: boolean;
    onClick: (callback: () => void) => void;
    offClick: (callback: () => void) => void;
    show: () => void;
    hide: () => void;
  };
  HapticFeedback: {
    impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void;
    notificationOccurred: (type: 'error' | 'success' | 'warning') => void;
    selectionChanged: () => void;
  };
  showPopup: (params: {
    title?: string;
    message: string;
    buttons?: Array<{
      id?: string;
      type?: 'default' | 'ok' | 'close' | 'cancel' | 'destructive';
      text?: string;
    }>;
  }, callback?: (buttonId: string) => void) => void;
  showAlert: (message: string, callback?: () => void) => void;
  showConfirm: (message: string, callback?: (confirmed: boolean) => void) => void;
  onEvent: (eventType: string, callback: () => void) => void;
  offEvent: (eventType: string, callback: () => void) => void;
  openTelegramLink: (url: string) => void;
  openLink: (url: string, options?: { try_instant_view?: boolean }) => void;
  switchInlineQuery: (query: string, choose_chat_types?: ('users' | 'bots' | 'groups' | 'channels')[]) => void;
  openInvoice: (url: string, callback?: (status: 'paid' | 'cancelled' | 'failed' | 'pending') => void) => void;
}

declare global {
  interface Window {
    Telegram?: {
      WebApp: TelegramWebApp;
    };
  }
}
