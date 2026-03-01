'use client';

import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { Plus, Sparkles, Play, ArrowUp, X, Smile, CheckCircle2, Search, ChevronDown, ChevronRight, List, LayoutGrid, Loader2, Archive, RotateCcw, Share2, Flame, Users } from 'lucide-react';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { Button, Card, Modal, ScrollBackdrop } from '@/components/ui';
import { MoodSelector } from '@/components/mood';
import { TaskForm } from '@/components/tasks';
import { DailyBonus, LevelUpModal, EnergyLimitModal, EventBanner, type LevelRewardItem } from '@/components/gamification';
import { StreakIndicator } from '@/components/gamification/StreakIndicator';
import { StreakMilestoneModal } from '@/components/gamification/StreakMilestoneModal';
import { CardEarnedModal, CardTutorial, shouldShowCardTutorial, SharedRewardsModal, type EarnedCard } from '@/components/cards';
import { SpotlightOnboarding, type OnboardingStep } from '@/components/SpotlightOnboarding';
import { LandingPage } from '@/components/LandingPage';
import { useAppStore } from '@/lib/store';
import { tasksService, moodService, focusService } from '@/services';
import type { SharedTaskRecord, SharedTaskReward } from '@/services/tasks';
import { cardsService } from '@/services/cards';
import { hapticFeedback, isMobileApp } from '@/lib/telegram';
import { MOOD_EMOJIS } from '@/domain/constants';
import { useLanguage, TranslationKey } from '@/lib/i18n';
import type { MoodLevel, EnergyLevel, FocusSession, TaskStatus } from '@/domain/types';
import { formatDateForAPI, formatDateDisplay } from '@/lib/dateUtils';
import { WeekCalendar } from '@/components/tasks/WeekCalendar';
import { MiniTimer } from '@/components/focus/MiniTimer';
import { TaskCardCompact } from '@/components/tasks/TaskCardCompact';

// TODO: Re-enable spotlight onboarding later
const ONBOARDING_STEPS: OnboardingStep[] = [
  // Temporarily disabled
  // {
  //   id: 'create-task',
  //   targetSelector: '[data-onboarding="create-task"]',
  //   title: 'Создание задачи',
  //   description: 'Нажми сюда, чтобы создать новую задачу. AI разобьёт её на маленькие шаги с учётом твоего настроения!',
  //   position: 'bottom',
  // },
  // {
  //   id: 'mood-check',
  //   targetSelector: '[data-onboarding="mood-check"]',
  //   title: 'Проверка настроения',
  //   description: 'Здесь ты можешь отслеживать своё настроение. От него зависит как задачи будут разбиты на шаги.',
  //   position: 'bottom',
  // },
  // {
  //   id: 'nav-deck',
  //   targetSelector: '[data-onboarding="nav-deck"]',
  //   title: 'Твоя колода карт',
  //   description: 'За выполнение задач ты получаешь карты! Собирай колоду, обменивайся с друзьями и сражайся на арене.',
  //   position: 'top',
  // },
];

function getDeadlineInfo(dueDate: string | null | undefined, t: (key: TranslationKey) => string) {
  if (!dueDate) return null;
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const due = new Date(dueDate + 'T00:00:00');
  const diffMs = due.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return { label: t('overdue'), color: 'text-red-400', bg: 'bg-red-500/20' };
  if (diffDays <= 1) return { label: diffDays === 0 ? t('today') : `1${t('daysShort')}`, color: 'text-red-400', bg: 'bg-red-500/20' };
  if (diffDays <= 3) return { label: `${diffDays}${t('daysShort')}`, color: 'text-orange-400', bg: 'bg-orange-500/20' };
  if (diffDays <= 7) return { label: `${diffDays}${t('daysShort')}`, color: 'text-yellow-400', bg: 'bg-yellow-500/20' };
  return { label: `${diffDays}${t('daysShort')}`, color: 'text-gray-400', bg: 'bg-gray-700/50' };
}

type FilterStatus = TaskStatus | 'all' | 'archived';

export default function HomePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { t, language } = useLanguage();
  const { user, isLoading, authError, latestMood, setLatestMood, showMoodModal, setShowMoodModal, showXPAnimation, pushXPToast, setActiveSession, setActiveSessions, activeSessions, removeActiveSession, updateActiveSession, isTelegramEnvironment, isSpotlightActive } = useAppStore();
  const [moodLoading, setMoodLoading] = useState(false);

  // Modal phase queue: ensures modals show one at a time
  // catchup → dailyBonus → mood → done
  const [modalPhase, setModalPhase] = useState<'catchup' | 'dailyBonus' | 'mood' | 'done'>('catchup');

  // Fetch active focus sessions so timers survive page navigation
  const { data: activeSessionsData } = useQuery({
    queryKey: ['focus', 'active'],
    queryFn: () => focusService.getActiveSession(),
    enabled: !!user,
    refetchInterval: 30000, // Sync every 30s
  });

  useEffect(() => {
    if (activeSessionsData?.data?.sessions) {
      setActiveSessions(activeSessionsData.data.sessions);
    }
  }, [activeSessionsData, setActiveSessions]);

  // Retroactive level rewards catch-up (one-shot on first load)
  const catchUpCheckedRef = useRef(false);
  useEffect(() => {
    if (!user || catchUpCheckedRef.current) return;
    catchUpCheckedRef.current = true;
    cardsService.claimLevelCatchUp().then((result) => {
      // Store energy limit increase if present (will show after level-up modal)
      if (result.data?.energy_limit_increased) {
        setEnergyLimitData({
          old_max: result.data.energy_limit_increased.old_max,
          new_max: result.data.energy_limit_increased.new_max,
        });
      }

      if (result.success && result.data?.has_rewards) {
        setLevelUpData({
          newLevel: result.data.new_level || 0,
          rewards: result.data.rewards,
          genreUnlockAvailable: result.data.genre_unlock_available || null,
        });
        setShowLevelUpModal(true);
        // Phase advances when level-up modal closes (see onClose handler)
      } else if (result.data?.energy_limit_increased) {
        // No regular rewards but energy limit increased — show dedicated modal
        setShowEnergyLimitModal(true);
      } else {
        // No catch-up rewards — check if user has pending genre unlocks
        cardsService.getUnlockedGenres().then((genreResult) => {
          if (genreResult.success && genreResult.data?.unlock_available?.can_unlock) {
            setLevelUpData({
              newLevel: user.level || 0,
              rewards: [],
              genreUnlockAvailable: genreResult.data.unlock_available,
            });
            setShowLevelUpModal(true);
          } else {
            // No level-up to show → advance to daily bonus phase
            setModalPhase('dailyBonus');
          }
        }).catch(() => {
          setModalPhase('dailyBonus');
        });
      }
    }).catch(() => {
      catchUpCheckedRef.current = false;
      setModalPhase('dailyBonus');
    });
  }, [user]);

  // Date selection with smart focus:
  // - If last visit was today: restore last selected date
  // - If last visit was another day: focus on today
  const [selectedDate, setSelectedDate] = useState(() => {
    if (typeof window === 'undefined') return new Date();

    const today = formatDateForAPI(new Date());
    const lastVisitDate = localStorage.getItem('moodsprint_last_visit_date');
    const lastSelectedDate = localStorage.getItem('moodsprint_last_selected_date');

    if (lastVisitDate === today && lastSelectedDate) {
      // Same day visit - restore last selected date
      const parsed = new Date(lastSelectedDate);
      if (!isNaN(parsed.getTime())) {
        return parsed;
      }
    }

    // New day or first visit - use today
    return new Date();
  });

  // Save last visit date and selected date to localStorage
  useEffect(() => {
    const today = formatDateForAPI(new Date());
    localStorage.setItem('moodsprint_last_visit_date', today);
  }, []);

  // Save selected date when it changes
  useEffect(() => {
    localStorage.setItem('moodsprint_last_selected_date', formatDateForAPI(selectedDate));
  }, [selectedDate]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [postponeNotificationDismissed, setPostponeNotificationDismissed] = useState(false);
  const [filterStatus, setFilterStatus] = useState<FilterStatus>(() => {
    if (typeof window === 'undefined') return 'pending';
    const stored = localStorage.getItem('moodsprint_filter_status');
    if (stored === 'pending' || stored === 'in_progress' || stored === 'completed' || stored === 'all' || stored === 'archived') {
      return stored as FilterStatus;
    }
    return 'pending';
  });
  // Persist filter status
  useEffect(() => {
    localStorage.setItem('moodsprint_filter_status', filterStatus);
  }, [filterStatus]);

  const [earnedCard, setEarnedCard] = useState<EarnedCard | null>(null);
  const [showCardModal, setShowCardModal] = useState(false);
  const [showCardTutorial, setShowCardTutorial] = useState(false);
  const [showLevelUpModal, setShowLevelUpModal] = useState(false);
  const [levelUpData, setLevelUpData] = useState<{
    newLevel: number;
    rewards: LevelRewardItem[];
    genreUnlockAvailable?: { can_unlock: boolean; available_genres: string[]; suggested_genres?: string[] } | null;
  } | null>(null);
  const [showEnergyLimitModal, setShowEnergyLimitModal] = useState(false);
  const [energyLimitData, setEnergyLimitData] = useState<{ old_max: number; new_max: number } | null>(null);
  const [showStreakMilestoneModal, setShowStreakMilestoneModal] = useState(false);
  const [streakMilestoneData, setStreakMilestoneData] = useState<{ milestone_days: number; xp_bonus: number; card_earned?: { id: number; name: string; emoji: string; rarity: string } } | null>(null);
  const [quickTaskTitle, setQuickTaskTitle] = useState('');
  const [quickTaskPending, setQuickTaskPending] = useState<string | null>(null);
  const [previewSharedTask, setPreviewSharedTask] = useState<SharedTaskRecord | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isCompactMode, setIsCompactMode] = useState(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('taskListCompact');
      // Default to compact mode if not explicitly set to 'false'
      return stored !== 'false';
    }
    return true;
  });
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});
  const [isScrolled, setIsScrolled] = useState(false);

  // NEW tag: track task IDs created in this session
  const [newTaskIds, setNewTaskIds] = useState<Set<number>>(() => {
    if (typeof window === 'undefined') return new Set();
    const stored = sessionStorage.getItem('moodsprint_new_task_ids');
    if (stored) {
      try { return new Set(JSON.parse(stored) as number[]); } catch { return new Set(); }
    }
    return new Set();
  });

  // Persist new task IDs to sessionStorage
  useEffect(() => {
    sessionStorage.setItem('moodsprint_new_task_ids', JSON.stringify(Array.from(newTaskIds)));
  }, [newTaskIds]);

  const markTaskSeen = useCallback((taskId: number) => {
    setNewTaskIds(prev => {
      if (!prev.has(taskId)) return prev;
      const next = new Set(prev);
      next.delete(taskId);
      return next;
    });
  }, []);
  // Track if this is user's first visit (to skip daily bonus & mood on first login)
  const [isFirstVisit, setIsFirstVisit] = useState(() => {
    if (typeof window !== 'undefined') {
      return !localStorage.getItem('first_visit_completed');
    }
    return false;
  });

  // Check if this is the first day - skip mood check on first day entirely
  const isFirstDay = typeof window !== 'undefined' && (() => {
    const firstLoginDate = localStorage.getItem('first_login_date');
    if (!firstLoginDate) return true; // No date set = first day
    return firstLoginDate === new Date().toDateString();
  })();

  const selectedDateStr = formatDateForAPI(selectedDate);

  // Calculate date range for calendar task count badges (must match WeekCalendar's range: -7..+30)
  const calendarDateRange = useMemo(() => {
    const today = new Date();
    const from = new Date(today);
    from.setDate(today.getDate() - 7);
    const to = new Date(today);
    to.setDate(today.getDate() + 30);
    return { from: formatDateForAPI(from), to: formatDateForAPI(to) };
  }, []);

  // Check if we should show mood modal — only when modal queue reaches 'mood' phase
  useEffect(() => {
    if (modalPhase !== 'mood') return;
    if (user && !latestMood && !isFirstVisit && !isFirstDay && !isSpotlightActive) {
      moodService.getLatestMood().then((result) => {
        if (result.success && result.data?.mood_check) {
          setLatestMood(result.data.mood_check);
        } else {
          setShowMoodModal(true);
        }
      });
    }
    setModalPhase('done');
  }, [modalPhase, user, latestMood, setLatestMood, setShowMoodModal, isFirstVisit, isFirstDay, isSpotlightActive]);

  // Fallback: mark first visit as completed if spotlight isn't showing
  // (This handles edge case where onboarding_home is set but first_visit_completed isn't)
  useEffect(() => {
    if (isFirstVisit && user && !isSpotlightActive) {
      // If spotlight isn't active after 2 seconds, mark first visit as done
      const timer = setTimeout(() => {
        localStorage.setItem('first_visit_completed', 'true');
        setIsFirstVisit(false);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [isFirstVisit, user, isSpotlightActive]);

  // Track scroll for header overlay
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Query tasks for selected date with status filter
  const { data: tasksData, isLoading: tasksLoading, isFetching } = useQuery({
    queryKey: ['tasks', 'by_date', selectedDateStr, filterStatus],
    queryFn: () => tasksService.getTasks({
      // Archived tasks aren't date-bound — fetch all of them
      ...(filterStatus !== 'archived' && { due_date: selectedDateStr }),
      ...(filterStatus !== 'all' && { status: filterStatus }),
      limit: 100,
    }),
    enabled: !!user,
    placeholderData: keepPreviousData,
  });

  // Query all tasks for selected date to calculate status counts
  const { data: allTasksForCounts } = useQuery({
    queryKey: ['tasks', 'by_date', selectedDateStr, 'all'],
    queryFn: () => tasksService.getTasks({
      due_date: selectedDateStr,
      limit: 100,
    }),
    enabled: !!user,
    staleTime: 1000 * 30, // 30 seconds
  });

  // Calculate status counts for badges
  const statusCounts = useMemo(() => {
    const tasks = allTasksForCounts?.data?.tasks || [];
    return {
      pending: tasks.filter(t => t.status === 'pending').length,
      in_progress: tasks.filter(t => t.status === 'in_progress').length,
      completed: tasks.filter(t => t.status === 'completed').length,
    };
  }, [allTasksForCounts]);

  // Query tasks for full calendar range badges (-7..+30 days)
  const { data: weekTasksData } = useQuery({
    queryKey: ['tasks', 'calendar', calendarDateRange.from, calendarDateRange.to],
    queryFn: () => tasksService.getTasks({
      due_date_from: calendarDateRange.from,
      due_date_to: calendarDateRange.to,
      limit: 200,
    }),
    enabled: !!user,
    staleTime: 1000 * 60 * 5,
  });

  // Calculate task counts per day for the week
  const taskCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    const allTasks = weekTasksData?.data?.tasks || [];
    for (const task of allTasks) {
      if (task.due_date && task.status !== 'completed') {
        counts[task.due_date] = (counts[task.due_date] || 0) + 1;
      }
    }
    return counts;
  }, [weekTasksData]);

  const createMutation = useMutation({
    mutationFn: async (input: { title: string; description: string; due_date: string; scheduled_at?: string; autoDecompose?: boolean; subtasks?: string[] }) => {
      const result = await tasksService.createTask(input);
      if (result.success && result.data?.task) {
        const taskId = result.data.task.id;
        // Create manual subtasks if provided
        if (input.subtasks && input.subtasks.length > 0) {
          for (const subtaskTitle of input.subtasks) {
            try {
              await tasksService.createSubtask(taskId, { title: subtaskTitle.trim() });
            } catch (err) {
              console.error('[CreateSubtask] Failed:', err);
            }
          }
        }
        // Auto-decompose the task after creation (only if no manual subtasks)
        if (input.autoDecompose && (!input.subtasks || input.subtasks.length === 0)) {
          try {
            const decomposeResult = await tasksService.decomposeTask(taskId, latestMood?.id);
            if (decomposeResult.success) {
              queryClient.invalidateQueries({ queryKey: ['tasks'] });
            }
          } catch (err) {
            console.error('[AutoDecompose] Failed:', err);
          }
        }
      }
      return result;
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setShowCreateModal(false);
      hapticFeedback('success');
      // Track new task for "NEW" badge
      if (result.data?.task?.id) {
        setNewTaskIds(prev => {
          const next = new Set(prev);
          next.add(result.data!.task.id);
          return next;
        });
      }
    },
  });

  const startFocusMutation = useMutation({
    mutationFn: (taskId: number) =>
      focusService.startSession({
        task_id: taskId,
        planned_duration_minutes: 25,
      }),
    onSuccess: (result) => {
      if (result.success && result.data) {
        setActiveSession(result.data.session);
        queryClient.invalidateQueries({ queryKey: ['tasks'] });
        hapticFeedback('success');
      }
    },
  });

  const pauseSessionMutation = useMutation({
    mutationFn: (sessionId: number) => focusService.pauseSession(sessionId),
    onSuccess: (result) => {
      if (result.success && result.data?.session) {
        updateActiveSession(result.data.session);
        queryClient.invalidateQueries({ queryKey: ['focus', 'active'] });
      }
    },
  });

  const resumeSessionMutation = useMutation({
    mutationFn: (sessionId: number) => focusService.resumeSession(sessionId),
    onSuccess: (result) => {
      if (result.success && result.data?.session) {
        updateActiveSession(result.data.session);
        queryClient.invalidateQueries({ queryKey: ['focus', 'active'] });
      }
    },
  });

  const completeSessionMutation = useMutation({
    mutationFn: (sessionId: number) => focusService.completeSession(sessionId, true),
    onSuccess: (result, sessionId) => {
      removeActiveSession(sessionId);
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['user', 'stats'] });
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      if (result.data?.xp_earned) {
        pushXPToast({ type: 'player', amount: result.data.xp_earned, currentXp: user?.xp ?? 0, xpForNext: user?.xp_for_next_level ?? 100, level: user?.level ?? 1 });
      }
      // Show card earned modal if card was generated
      if (result.data?.card_earned) {
        setEarnedCard({
          ...result.data.card_earned,
          quick_completion: result.data.quick_completion,
          quick_completion_message: result.data.quick_completion_message,
        } as EarnedCard);
        setShowCardModal(true);
      }
      // Level-up rewards
      if (result.data?.level_up) {
        setLevelUpData({
          newLevel: result.data.new_level || 0,
          rewards: result.data.level_rewards || [],
          genreUnlockAvailable: result.data.genre_unlock_available || null,
        });
        if (!result.data?.card_earned) setShowLevelUpModal(true);
      }
      // Streak milestone
      if (result.data?.streak_milestone) {
        setStreakMilestoneData(result.data.streak_milestone);
        setShowStreakMilestoneModal(true);
      }
      // Companion XP toast
      if (result.data?.companion_xp) {
        const cxp = result.data.companion_xp;
        pushXPToast({ type: 'companion', amount: cxp.xp_earned, cardEmoji: cxp.card_emoji ?? undefined, cardName: cxp.card_name ?? undefined, levelUp: cxp.level_up, cardLevel: cxp.new_level ?? undefined, cardXp: cxp.card_xp ?? 0, cardXpForNext: cxp.xp_to_next ?? 100 });
      }
      hapticFeedback('success');
    },
  });

  const cancelSessionMutation = useMutation({
    mutationFn: (sessionId: number) => focusService.cancelSession(sessionId),
    onSuccess: (result, sessionId) => {
      removeActiveSession(sessionId);
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['focus'] });
      hapticFeedback('light');
    },
  });

  const completeTaskMutation = useMutation({
    mutationFn: (taskId: number) => tasksService.updateTask(taskId, { status: 'completed' }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['user', 'stats'] });
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      if (result.data?.xp_earned) {
        pushXPToast({ type: 'player', amount: result.data.xp_earned, currentXp: user?.xp ?? 0, xpForNext: user?.xp_for_next_level ?? 100, level: user?.level ?? 1 });
      }
      // Show card earned modal if card was generated
      if (result.data?.card_earned) {
        setEarnedCard({
          ...result.data.card_earned,
          quick_completion: result.data.quick_completion,
          quick_completion_message: result.data.quick_completion_message,
        } as EarnedCard);
        setShowCardModal(true);
      }
      // Level-up rewards
      if (result.data?.level_up) {
        setLevelUpData({
          newLevel: result.data.new_level || 0,
          rewards: result.data.level_rewards || [],
          genreUnlockAvailable: result.data.genre_unlock_available || null,
        });
        if (!result.data?.card_earned) setShowLevelUpModal(true);
      }
      // Streak milestone
      if (result.data?.streak_milestone) {
        setStreakMilestoneData(result.data.streak_milestone);
        setShowStreakMilestoneModal(true);
      }
      // Companion XP toast
      if (result.data?.companion_xp) {
        const cxp = result.data.companion_xp;
        pushXPToast({ type: 'companion', amount: cxp.xp_earned, cardEmoji: cxp.card_emoji ?? undefined, cardName: cxp.card_name ?? undefined, levelUp: cxp.level_up, cardLevel: cxp.new_level ?? undefined, cardXp: cxp.card_xp ?? 0, cardXpForNext: cxp.xp_to_next ?? 100 });
      }
      hapticFeedback('success');
    },
  });

  const restoreTaskMutation = useMutation({
    mutationFn: (taskId: number) => tasksService.updateTask(taskId, { status: 'pending' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      hapticFeedback('success');
    },
  });

  // Helper to get session for a task
  const getSessionForTask = (taskId: number) => {
    return activeSessions.find(s => s.task_id === taskId);
  };

  const handleCreateTask = (title: string, description: string, dueDate: string | null, scheduledAt?: string, autoDecompose?: boolean, subtasks?: string[]) => {
    createMutation.mutate({ title, description, due_date: dueDate || selectedDateStr, scheduled_at: scheduledAt, autoDecompose, subtasks });
  };

  const handleQuickTaskCreate = () => {
    const title = quickTaskTitle.trim();
    if (!title) return;
    setQuickTaskPending(title);
    setQuickTaskTitle('');
    createMutation.mutate(
      { title, description: '', due_date: selectedDateStr },
      { onSettled: () => setQuickTaskPending(null) }
    );
  };

  // Toggle compact mode
  const toggleCompactMode = useCallback(() => {
    setIsCompactMode(prev => {
      const newValue = !prev;
      localStorage.setItem('taskListCompact', String(newValue));
      return newValue;
    });
    hapticFeedback('light');
  }, []);

  // Toggle collapsed group
  const toggleGroup = useCallback((priority: string) => {
    setCollapsedGroups(prev => ({
      ...prev,
      [priority]: !prev[priority],
    }));
    hapticFeedback('light');
  }, []);

  // Check for postponed tasks notification
  const { data: postponeData } = useQuery({
    queryKey: ['tasks', 'postpone-status'],
    queryFn: () => tasksService.getPostponeStatus(),
    enabled: !!user,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  const handleMoodSubmit = async (mood: MoodLevel, energy: EnergyLevel, note?: string) => {
    setMoodLoading(true);
    try {
      const result = await moodService.createMoodCheck({ mood, energy, note });
      if (result.success && result.data) {
        setLatestMood(result.data.mood_check);
        setShowMoodModal(false);
        hapticFeedback('success');
        if (result.data.xp_earned) {
          pushXPToast({ type: 'player', amount: result.data.xp_earned, currentXp: user?.xp ?? 0, xpForNext: user?.xp_for_next_level ?? 100, level: user?.level ?? 1 });
        }
      }
    } catch (error) {
      console.error('Failed to log mood:', error);
    } finally {
      setMoodLoading(false);
    }
  };

  // Query shared tasks
  const { data: sharedWithMeData } = useQuery({
    queryKey: ['tasks', 'shared'],
    queryFn: () => tasksService.getSharedWithMe(),
    enabled: !!user,
    staleTime: 30 * 1000,
  });
  const sharedTasks = sharedWithMeData?.data?.shared_tasks || [];

  // Query pending shared task rewards (cards earned from shared tasks)
  const { data: sharedRewardsData } = useQuery({
    queryKey: ['tasks', 'shared-rewards'],
    queryFn: () => tasksService.getSharedTaskRewards(),
    enabled: !!user,
    staleTime: 30 * 1000,
  });
  const sharedRewards = sharedRewardsData?.data?.rewards || [];
  const [showSharedRewardModal, setShowSharedRewardModal] = useState(false);

  // Show shared reward modal when rewards are available and no other modal is showing
  useEffect(() => {
    if (sharedRewards.length > 0 && !showCardModal && !showLevelUpModal && !showStreakMilestoneModal && modalPhase === 'done') {
      setShowSharedRewardModal(true);
    }
  }, [sharedRewards.length, showCardModal, showLevelUpModal, showStreakMilestoneModal, modalPhase]);

  const acceptSharedMutation = useMutation({
    mutationFn: (sharedId: number) => tasksService.acceptSharedTask(sharedId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks', 'shared'] });
      hapticFeedback('success');
    },
  });

  const declineSharedMutation = useMutation({
    mutationFn: (sharedId: number) => tasksService.declineSharedTask(sharedId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks', 'shared'] });
      hapticFeedback('light');
    },
  });

  const allTasks = tasksData?.data?.tasks || [];
  const postponeStatus = postponeData?.data;
  const showPostponeNotification = postponeStatus?.has_postponed && !postponeNotificationDismissed;

  // Filter tasks by search query (must be before early returns)
  const filteredTasks = useMemo(() => {
    if (!searchQuery.trim()) return allTasks;
    const query = searchQuery.toLowerCase();
    return allTasks.filter(task => task.title.toLowerCase().includes(query));
  }, [allTasks, searchQuery]);

  // Group tasks by priority (must be before early returns)
  const groupedTasks = useMemo(() => {
    const groups: Record<'high' | 'medium' | 'low', typeof allTasks> = {
      high: [],
      medium: [],
      low: [],
    };
    for (const task of filteredTasks) {
      const priority = (task.priority || 'medium') as 'high' | 'medium' | 'low';
      groups[priority].push(task);
    }
    return groups;
  }, [filteredTasks]);

  const priorityConfig = {
    high: { label: t('highPriority'), color: 'text-red-400', bg: 'bg-red-500/20', border: 'border-red-500/30' },
    medium: { label: t('mediumPriority'), color: 'text-yellow-400', bg: 'bg-yellow-500/20', border: 'border-yellow-500/30' },
    low: { label: t('lowPriority'), color: 'text-green-400', bg: 'bg-green-500/20', border: 'border-green-500/30' },
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (authError && !user) {
    return (
      <div className="flex flex-col items-center justify-center h-screen p-6 text-center">
        <div className="w-32 h-32 mb-6 relative">
          <div className="absolute inset-0 rounded-full bg-gradient-to-br from-orange-500/20 to-red-500/20 blur-2xl animate-pulse" />
          <div className="relative w-full h-full flex items-center justify-center">
            <span className="text-7xl">🔧</span>
          </div>
        </div>
        <h1 className="text-2xl font-bold text-white mb-3">
          {t('maintenanceTitle')}
        </h1>
        <p className="text-gray-400 mb-2 max-w-xs leading-relaxed">
          {t('maintenanceDesc')}
        </p>
        <p className="text-gray-500 text-sm mb-8 max-w-xs">
          {t('maintenanceHint')}
        </p>
        <Button
          variant="gradient"
          size="lg"
          className="w-full max-w-xs"
          onClick={() => window.location.reload()}
        >
          {t('tryAgain')}
        </Button>
      </div>
    );
  }

  if (!user) {
    // Mobile app handles its own auth - just show loading
    if (isMobileApp()) {
      return (
        <div className="flex items-center justify-center h-screen">
          <div className="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full" />
        </div>
      );
    }

    // Show full landing page with login/register for non-Telegram browser users
    if (!isTelegramEnvironment) {
      return <LandingPage />;
    }

    // In Telegram but not authenticated - show simple message
    return (
      <div className="flex flex-col items-center justify-center h-screen p-6 text-center">
        <div className="w-48 h-48 mb-8 relative animate-float">
          <div className="absolute inset-0 rounded-full bg-gradient-to-br from-purple-500/30 to-blue-500/30 blur-2xl" />
          <div className="absolute inset-4 rounded-full bg-gradient-to-br from-purple-600 to-blue-600 animate-pulse-glow" />
        </div>
        <h1 className="text-2xl font-bold text-white mb-3">
          MoodSprint
        </h1>
        <p className="text-gray-400 mb-8 max-w-xs">
          {t('personalAssistantDesc')}
        </p>
        <Button variant="gradient" size="lg" className="w-full max-w-xs">
          <Sparkles className="w-5 h-5" />
          {t('openInTelegram')}
        </Button>
        <p className="text-xs text-gray-500 mt-4">
          {t('telegramOnlyHint')}
        </p>
      </div>
    );
  }

  // Get greeting based on time
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return t('goodMorning');
    if (hour < 17) return t('goodAfternoon');
    return t('goodEvening');
  };

  return (
    <SpotlightOnboarding steps={ONBOARDING_STEPS} storageKey="home">
    <div className="relative">
      {/* Scroll overlay with blur */}
      <ScrollBackdrop />
    <div className="p-4 space-y-6">
      {/* Daily Bonus Modal — only enabled when modal phase reaches it */}
      <DailyBonus
        enabled={modalPhase === 'dailyBonus'}
        onDone={() => setModalPhase('mood')}
      />

      {/* Postponed Tasks Notification */}
      {showPostponeNotification && postponeStatus && (
        <div className="bg-amber-500/20 border border-amber-500/30 rounded-xl p-3 flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-amber-500/30 flex items-center justify-center flex-shrink-0">
            <ArrowUp className="w-4 h-4 text-amber-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-amber-200">{postponeStatus.message}</p>
            {postponeStatus.priority_changes && postponeStatus.priority_changes.length > 0 && (
              <div className="mt-1 text-xs text-amber-400/80">
                {t('priorityRaised')}: {postponeStatus.priority_changes.map(c => c.task_title).join(', ')}
              </div>
            )}
          </div>
          <button
            onClick={() => setPostponeNotificationDismissed(true)}
            className="p-1 text-amber-400 hover:text-amber-300 transition-colors flex-shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Active Event Banner */}
      <EventBanner />

      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white truncate mr-3">
          {getGreeting()}, {user.first_name || t('friend')}
        </h1>
        <div className="flex items-center gap-2 flex-shrink-0">
          {user.streak_days > 0 && <StreakIndicator days={user.streak_days} />}
          <button
            onClick={() => setShowMoodModal(true)}
            className="w-10 h-10 rounded-full bg-dark-700 border border-gray-700 flex items-center justify-center hover:bg-dark-600 transition-colors"
            data-onboarding="mood-check"
          >
            {latestMood ? (
              <span className="text-lg">
                {MOOD_EMOJIS[latestMood.mood as keyof typeof MOOD_EMOJIS]}
              </span>
            ) : (
              <Smile className="w-5 h-5 text-gray-400" />
            )}
          </button>
        </div>
      </div>

      {/* Week Calendar */}
      <WeekCalendar
        selectedDate={selectedDate}
        onDateSelect={setSelectedDate}
        language={language}
        taskCounts={taskCounts}
      />

      {/* Quick Task Input */}
      <div className="space-y-2">
        <div className="flex gap-2">
          <input
            type="text"
            value={quickTaskTitle}
            onChange={(e) => setQuickTaskTitle(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleQuickTaskCreate(); }}
            placeholder={t('quickTaskPlaceholder')}
            disabled={!!quickTaskPending}
            className="flex-1 px-4 py-2.5 bg-gray-800/50 border border-gray-700 rounded-xl text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50"
          />
          <button
            onClick={handleQuickTaskCreate}
            disabled={!quickTaskTitle.trim() || !!quickTaskPending}
            className="w-10 h-10 rounded-xl bg-primary-500 hover:bg-primary-600 disabled:opacity-40 disabled:hover:bg-primary-500 flex items-center justify-center transition-colors flex-shrink-0"
          >
            {quickTaskPending ? (
              <Loader2 className="w-5 h-5 text-white animate-spin" />
            ) : (
              <ArrowUp className="w-5 h-5 text-white" />
            )}
          </button>
        </div>
        {quickTaskPending && (
          <div className="flex items-center gap-2 px-3 py-2 bg-primary-500/10 border border-primary-500/20 rounded-xl animate-pulse">
            <Loader2 className="w-3.5 h-3.5 text-primary-400 animate-spin" />
            <span className="text-xs text-primary-300">{t('addingTask')}: {quickTaskPending}</span>
          </div>
        )}
      </div>

      {/* Shared with me */}
      {sharedTasks.length > 0 && (
        <div className="space-y-2">
          <h2 className="font-semibold text-white text-sm flex items-center gap-2">
            <Share2 className="w-4 h-4 text-primary-400" />
            {t('sharedWithMe')}
          </h2>
          {sharedTasks.map((shared) => (
            <button
              key={shared.id}
              onClick={() => setPreviewSharedTask(shared)}
              className="w-full text-left bg-dark-700/50 rounded-xl p-3 border border-primary-500/20 hover:bg-dark-700/80 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-primary-500/20 flex items-center justify-center flex-shrink-0">
                  <Share2 className="w-4 h-4 text-primary-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-medium text-white truncate">
                    {shared.task?.title || `Task #${shared.task_id}`}
                  </h3>
                  <p className="text-xs text-gray-500">
                    {t('sharedByName').replace('{name}', shared.owner_name || '?')}
                  </p>
                </div>
                {shared.status === 'pending' && (
                  <span className="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 text-xs flex-shrink-0">{t('statusPending')}</span>
                )}
                {shared.status === 'accepted' && (
                  <span className="px-2 py-0.5 rounded-full bg-primary-500/20 text-primary-400 text-xs flex-shrink-0">{t('statusInProgress')}</span>
                )}
                {shared.status === 'completed' && (
                  <span className="px-2 py-0.5 rounded-full bg-green-500/20 text-green-400 text-xs flex-shrink-0">{t('done')}</span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Tasks Section */}
      <div className="space-y-3 min-h-[180px]">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-white capitalize">{formatDateDisplay(selectedDate, language, t)}</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={toggleCompactMode}
              className="p-2 rounded-lg bg-gray-700/50 hover:bg-gray-600/50 transition-colors"
              title={isCompactMode ? t('normalView') : t('compactView')}
            >
              {isCompactMode ? <LayoutGrid className="w-4 h-4 text-gray-400" /> : <List className="w-4 h-4 text-gray-400" />}
            </button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setShowCreateModal(true)}
              data-onboarding="create-task"
            >
              <Plus className="w-4 h-4 mr-1" />
              {t('add')}
            </Button>
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('searchTasks')}
            className="w-full pl-10 pr-4 py-2 bg-gray-800/50 border border-gray-700 rounded-xl text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 hover:bg-gray-600 rounded"
            >
              <X className="w-4 h-4 text-gray-400" />
            </button>
          )}
        </div>

        {/* Status Filters */}
        <div className="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4 scrollbar-hide md:overflow-x-visible md:flex-wrap">
          {([
            { value: 'pending' as const, labelKey: 'statusPending' as const },
            { value: 'in_progress' as const, labelKey: 'statusInProgress' as const },
            { value: 'completed' as const, labelKey: 'statusCompleted' as const },
            { value: 'all' as const, labelKey: 'all' as const },
            { value: 'archived' as const, labelKey: 'archived' as const },
          ]).map((filter) => {
            const count = filter.value !== 'all' && filter.value !== 'archived'
              ? statusCounts[filter.value as keyof typeof statusCounts]
              : 0;
            const showBadge = filter.value !== 'all' && filter.value !== 'archived' && count > 0;

            return (
              <button
                key={filter.value}
                onClick={() => setFilterStatus(filter.value)}
                className={`relative px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                  filterStatus === filter.value
                    ? 'bg-primary-500 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                {t(filter.labelKey)}
                {showBadge && (
                  <span className={`ml-1.5 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-bold ${
                    filterStatus === filter.value
                      ? 'bg-white/20 text-white'
                      : 'bg-primary-500/80 text-white'
                  }`}>
                    {count > 99 ? '99+' : count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {tasksLoading && !tasksData ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Card key={i} variant="glass" className="h-14 animate-pulse" />
            ))}
          </div>
        ) : filteredTasks.length > 0 ? (
          <div className="space-y-3">
            {(['high', 'medium', 'low'] as const).map((priority) => {
              const tasks = groupedTasks[priority];
              if (tasks.length === 0) return null;
              const config = priorityConfig[priority];
              const isCollapsed = collapsedGroups[priority];

              return (
                <div key={priority} className={`rounded-xl border ${config.border} overflow-hidden`}>
                  {/* Group Header */}
                  <button
                    onClick={() => toggleGroup(priority)}
                    className={`w-full flex items-center justify-between px-3 py-2 ${config.bg} hover:opacity-90 transition-opacity`}
                  >
                    <div className="flex items-center gap-2">
                      {isCollapsed ? (
                        <ChevronRight className={`w-4 h-4 ${config.color}`} />
                      ) : (
                        <ChevronDown className={`w-4 h-4 ${config.color}`} />
                      )}
                      <span className={`text-sm font-medium ${config.color}`}>{config.label}</span>
                    </div>
                    <span className="text-xs text-gray-400">{tasks.length} {t('tasksCount')}</span>
                  </button>

                  {/* Group Content */}
                  {!isCollapsed && (
                    <div className={`${isCompactMode ? 'divide-y divide-gray-800' : 'p-2 space-y-2'}`}>
                      {tasks.map((task) => {
                        const session = getSessionForTask(task.id);

                        if (isCompactMode) {
                          // Ultra compact row
                          return (
                            <div
                              key={task.id}
                              onClick={() => { markTaskSeen(task.id); router.push(`/tasks/${task.id}`); }}
                              className={`flex items-center gap-2 px-3 py-2 hover:bg-gray-800/50 cursor-pointer ${task.status === 'completed' ? 'opacity-50' : ''}`}
                            >
                              <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                                task.status === 'completed' ? 'bg-green-500' : 'bg-purple-500'
                              }`} />
                              <span className={`text-sm flex-1 min-w-0 truncate ${task.status === 'completed' ? 'text-gray-500 line-through' : 'text-white'}`}>
                                {task.title}
                              </span>
                              {newTaskIds.has(task.id) && (
                                <span className="px-1.5 py-0.5 bg-primary-500/30 text-primary-400 text-[10px] font-bold rounded-full flex-shrink-0">
                                  NEW
                                </span>
                              )}
                              {task.status !== 'completed' && task.status !== 'archived' && !session && (() => {
                                const dl = getDeadlineInfo(task.due_date, t);
                                return dl ? (
                                  <span className={`flex items-center gap-0.5 px-1 py-0.5 rounded-full text-[10px] font-medium flex-shrink-0 ${dl.bg} ${dl.color}`}>
                                    <Flame className="w-2.5 h-2.5" />
                                    {dl.label}
                                  </span>
                                ) : null;
                              })()}
                              {(task.shared_with_count ?? 0) > 0 && (
                                <span className="flex items-center gap-0.5 px-1 py-0.5 rounded-full text-[10px] font-medium flex-shrink-0 bg-primary-500/20 text-primary-400">
                                  <Users className="w-2.5 h-2.5" />
                                  {task.shared_with_count}
                                </span>
                              )}
                              {task.status !== 'completed' && session && (
                                <MiniTimer
                                  session={session}
                                  onPause={() => pauseSessionMutation.mutate(session.id)}
                                  onResume={() => resumeSessionMutation.mutate(session.id)}
                                  onComplete={() => completeSessionMutation.mutate(session.id)}
                                  onStop={() => cancelSessionMutation.mutate(session.id)}
                                />
                              )}
                              {task.status === 'archived' && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    restoreTaskMutation.mutate(task.id);
                                  }}
                                  className="p-1 rounded bg-orange-500/20 hover:bg-orange-500/30 flex-shrink-0"
                                >
                                  <RotateCcw className="w-3 h-3 text-orange-400" />
                                </button>
                              )}
                              {task.status !== 'completed' && task.status !== 'archived' && !session && (
                                <div className="flex items-center gap-1">
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      markTaskSeen(task.id);
                                      completeTaskMutation.mutate(task.id);
                                    }}
                                    className="p-1 rounded bg-green-500/20 hover:bg-green-500/30 flex-shrink-0"
                                  >
                                    <CheckCircle2 className="w-3 h-3 text-green-400" />
                                  </button>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      markTaskSeen(task.id);
                                      startFocusMutation.mutate(task.id);
                                    }}
                                    className="p-1 rounded bg-primary-500/20 hover:bg-primary-500/30 flex-shrink-0"
                                  >
                                    <Play className="w-3 h-3 text-primary-400" fill="currentColor" />
                                  </button>
                                </div>
                              )}
                            </div>
                          );
                        }

                        // Normal card
                        const isArchived = task.status === 'archived';
                        return (
                          <TaskCardCompact
                            key={task.id}
                            task={task}
                            isNew={newTaskIds.has(task.id)}
                            onClick={() => { markTaskSeen(task.id); router.push(`/tasks/${task.id}`); }}
                            onStart={!isArchived && task.status !== 'completed' && !session ? () => { markTaskSeen(task.id); startFocusMutation.mutate(task.id); } : undefined}
                            onCompleteTask={!isArchived && task.status !== 'completed' && !session ? () => { markTaskSeen(task.id); completeTaskMutation.mutate(task.id); } : undefined}
                            onRestore={isArchived ? () => restoreTaskMutation.mutate(task.id) : undefined}
                            activeSession={session}
                            onPause={session ? () => pauseSessionMutation.mutate(session.id) : undefined}
                            onResume={session ? () => resumeSessionMutation.mutate(session.id) : undefined}
                            onComplete={session ? () => completeSessionMutation.mutate(session.id) : undefined}
                            onStop={session ? () => cancelSessionMutation.mutate(session.id) : undefined}
                          />
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <Card variant="glass" className="text-center py-8">
            {filterStatus === 'archived' ? (
              <>
                <Archive className="w-12 h-12 text-orange-400 mx-auto mb-3" />
                <p className="text-gray-400 mb-1">{t('noArchivedTasks')}</p>
                <p className="text-gray-500 text-sm">{t('archivedTasksDesc')}</p>
              </>
            ) : (
              <>
                <Sparkles className="w-12 h-12 text-purple-400 mx-auto mb-3" />
                <p className="text-gray-400 mb-4">
                  {searchQuery
                    ? t('noTasksInCategory')
                    : filterStatus === 'all'
                    ? `${t('noTasksForDate')} ${formatDateDisplay(selectedDate, language, t).toLowerCase()}`
                    : t('noTasksInCategory')}
                </p>
                <Button variant="gradient" onClick={() => setShowCreateModal(true)}>
                  <Plus className="w-4 h-4" />
                  {t('createTask')}
                </Button>
              </>
            )}
          </Card>
        )}
      </div>

      {/* Mood Modal */}
      <Modal
        isOpen={showMoodModal}
        onClose={() => setShowMoodModal(false)}
        title={t('howAreYouFeeling')}
      >
        <MoodSelector onSubmit={handleMoodSubmit} isLoading={moodLoading} />
      </Modal>

      {/* Create Task Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title={t('createTask')}
      >
        <TaskForm
          onSubmit={handleCreateTask}
          isLoading={createMutation.isPending}
          initialDueDate={selectedDateStr}
        />
      </Modal>

      {/* Card Earned Modal */}
      <CardEarnedModal
        isOpen={showCardModal}
        card={earnedCard}
        onClose={() => {
          setShowCardModal(false);
          setEarnedCard(null);
          // Show level-up modal after card modal if there was a level up
          if (levelUpData) {
            setShowLevelUpModal(true);
          } else if (shouldShowCardTutorial()) {
            setShowCardTutorial(true);
          }
        }}
        t={t}
      />

      {/* Shared Task Rewards Modal (combined) */}
      <SharedRewardsModal
        isOpen={showSharedRewardModal}
        rewards={sharedRewards}
        onClose={() => {
          setShowSharedRewardModal(false);
          // Mark all as shown
          sharedRewards.forEach(r => tasksService.markSharedRewardShown(r.shared_id));
          queryClient.invalidateQueries({ queryKey: ['tasks', 'shared-rewards'] });
        }}
        t={t}
      />

      {/* Level Up Modal */}
      {levelUpData && (
        <LevelUpModal
          isOpen={showLevelUpModal}
          onClose={() => {
            setShowLevelUpModal(false);
            setLevelUpData(null);
            queryClient.invalidateQueries({ queryKey: ['cards'] });
            // Show energy limit modal if pending
            if (energyLimitData) {
              setShowEnergyLimitModal(true);
              return;
            }
            // Advance modal queue to next phase
            if (modalPhase === 'catchup') {
              setModalPhase('dailyBonus');
            }
            if (shouldShowCardTutorial()) {
              setShowCardTutorial(true);
            }
          }}
          newLevel={levelUpData.newLevel}
          rewards={levelUpData.rewards}
          genreUnlockAvailable={levelUpData.genreUnlockAvailable}
          onGenreSelect={() => {
            queryClient.invalidateQueries({ queryKey: ['cards'] });
          }}
        />
      )}

      {/* Energy Limit Modal */}
      {energyLimitData && (
        <EnergyLimitModal
          isOpen={showEnergyLimitModal}
          onClose={() => {
            setShowEnergyLimitModal(false);
            setEnergyLimitData(null);
            queryClient.invalidateQueries({ queryKey: ['campaign'] });
            // Advance modal queue to next phase
            if (modalPhase === 'catchup') {
              setModalPhase('dailyBonus');
            }
            if (shouldShowCardTutorial()) {
              setShowCardTutorial(true);
            }
          }}
          oldMax={energyLimitData.old_max}
          newMax={energyLimitData.new_max}
        />
      )}

      {/* Streak Milestone Modal */}
      <StreakMilestoneModal
        isOpen={showStreakMilestoneModal}
        onClose={() => {
          setShowStreakMilestoneModal(false);
          setStreakMilestoneData(null);
        }}
        milestone={streakMilestoneData}
      />

      {/* Card Tutorial (first-time onboarding) */}
      <CardTutorial
        isOpen={showCardTutorial}
        onClose={() => setShowCardTutorial(false)}
      />

      {/* Shared Task Preview Modal */}
      <Modal
        isOpen={!!previewSharedTask}
        onClose={() => setPreviewSharedTask(null)}
        title={previewSharedTask?.task?.title || `Task #${previewSharedTask?.task_id}`}
      >
        {previewSharedTask && (() => {
          const task = previewSharedTask.task;
          const priorityColors: Record<string, string> = {
            high: 'bg-red-500/20 text-red-400',
            medium: 'bg-amber-500/20 text-amber-400',
            low: 'bg-green-500/20 text-green-400',
          };
          return (
            <div className="space-y-4">
              {/* From user */}
              <p className="text-sm text-gray-400">
                {t('fromUser').replace('{name}', previewSharedTask.owner_name || '?')}
              </p>

              {/* Message */}
              {previewSharedTask.message && (
                <div className="bg-dark-700/50 rounded-xl p-3 border border-gray-700/50">
                  <p className="text-xs text-gray-500 mb-1">{t('taskMessage')}</p>
                  <p className="text-sm text-gray-300">{previewSharedTask.message}</p>
                </div>
              )}

              {/* Priority + Type badges */}
              {task && (
                <div className="flex items-center gap-2 flex-wrap">
                  {task.priority && (
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${priorityColors[task.priority] || 'bg-gray-700 text-gray-300'}`}>
                      {t(task.priority === 'high' ? 'priorityHigh' : task.priority === 'medium' ? 'priorityMedium' : 'priorityLow')}
                    </span>
                  )}
                  {task.task_type && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-primary-500/20 text-primary-400">
                      {task.task_type}
                    </span>
                  )}
                </div>
              )}

              {/* Description */}
              {task?.description && (
                <p className="text-sm text-gray-300">{task.description}</p>
              )}

              {/* Subtasks */}
              {task?.subtasks && task.subtasks.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 mb-2">
                    {t('subtasksCount')} ({task.subtasks_completed}/{task.subtasks.length})
                  </p>
                  <div className="space-y-1.5">
                    {task.subtasks.map((sub) => (
                      <div key={sub.id} className="flex items-center gap-2 text-sm">
                        <CheckCircle2
                          className={`w-4 h-4 flex-shrink-0 ${sub.status === 'completed' ? 'text-green-400' : 'text-gray-600'}`}
                        />
                        <span className={sub.status === 'completed' ? 'text-gray-500 line-through' : 'text-gray-300'}>
                          {sub.title}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-2">
                {previewSharedTask.status === 'pending' && (
                  <>
                    <button
                      onClick={() => {
                        acceptSharedMutation.mutate(previewSharedTask.id);
                        setPreviewSharedTask(null);
                      }}
                      className="flex-1 py-3 rounded-xl bg-primary-500 text-white font-medium text-sm"
                    >
                      {t('acceptTask')}
                    </button>
                    <button
                      onClick={() => {
                        declineSharedMutation.mutate(previewSharedTask.id);
                        setPreviewSharedTask(null);
                      }}
                      className="flex-1 py-3 rounded-xl bg-gray-700 text-gray-300 font-medium text-sm"
                    >
                      {t('declineTask')}
                    </button>
                  </>
                )}
                {previewSharedTask.status === 'accepted' && (
                  <button
                    onClick={() => {
                      router.push(`/tasks/${previewSharedTask.task_id}`);
                      setPreviewSharedTask(null);
                    }}
                    className="flex-1 py-3 rounded-xl bg-primary-500 text-white font-medium text-sm"
                  >
                    {t('openTask')}
                  </button>
                )}
              </div>
            </div>
          );
        })()}
      </Modal>
    </div>
    </div>
    </SpotlightOnboarding>
  );
}
