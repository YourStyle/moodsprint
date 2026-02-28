'use client';

import { useState, useEffect, useMemo, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Wand2, Trash2, Plus, Play, Check, Timer, Infinity, Pencil, Sparkles, ChevronUp, ChevronDown, Pause, Square, Bell, RotateCcw, Share2, SearchX, CalendarDays } from 'lucide-react';
import { Button, Card, Modal, Progress, ScrollBackdrop, TimePicker, roundToFiveMinutes, DatePicker } from '@/components/ui';
import { SubtaskItem } from '@/components/tasks';
import { MoodSelector } from '@/components/mood';
import { CardEarnedModal, CardTutorial, shouldShowCardTutorial, type EarnedCard } from '@/components/cards';
import { LevelUpModal, StreakMilestoneModal, type LevelRewardItem } from '@/components/gamification';
import { tasksService, focusService, moodService } from '@/services';
import { cardsService } from '@/services/cards';
import { useAppStore } from '@/lib/store';
import { hapticFeedback, showBackButton, hideBackButton } from '@/lib/telegram';
import { useLanguage, type TranslationKey } from '@/lib/i18n';
import { PRIORITY_COLORS, TASK_TYPE_EMOJIS, TASK_TYPE_LABELS, TASK_TYPE_COLORS, DEFAULT_FOCUS_DURATION } from '@/domain/constants';
import { playFocusCompleteSound } from '@/lib/sounds';
import type { MoodLevel, EnergyLevel, TaskType, UpdateTaskInput } from '@/domain/types';

const TASK_TYPES: TaskType[] = [
  'creative', 'analytical', 'communication', 'physical',
  'learning', 'planning', 'coding', 'writing'
];

// Helper to calculate elapsed seconds
function calculateElapsedSeconds(session: { started_at: string }): number {
  const startedAt = new Date(session.started_at).getTime();
  const now = Date.now();
  return Math.floor((now - startedAt) / 1000);
}

// Timer component for active focus session
function FocusTimer({
  session,
  onPause,
  onResume,
  onCancel,
  isPauseLoading,
  isResumeLoading,
  t,
}: {
  session: {
    id: number;
    status: string;
    started_at: string;
    planned_duration_minutes: number;
    elapsed_minutes?: number;
  };
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
  isPauseLoading?: boolean;
  isResumeLoading?: boolean;
  t: (key: TranslationKey) => string;
}) {
  const isPaused = session.status === 'paused';
  const isNoTimerMode = session.planned_duration_minutes >= 480;

  const initialElapsed = useMemo(() => {
    if (isPaused) {
      return (session.elapsed_minutes || 0) * 60;
    }
    return calculateElapsedSeconds(session);
  }, [session.started_at, session.status, session.elapsed_minutes, isPaused]);

  const [elapsed, setElapsed] = useState(initialElapsed);
  const soundPlayedRef = useRef(false);

  useEffect(() => {
    setElapsed(initialElapsed);
  }, [initialElapsed]);

  useEffect(() => {
    if (isPaused) return;
    const interval = setInterval(() => {
      setElapsed(calculateElapsedSeconds(session));
    }, 1000);
    return () => clearInterval(interval);
  }, [isPaused, session.started_at, session]);

  // Reset sound flag when session changes
  useEffect(() => {
    soundPlayedRef.current = false;
  }, [session.started_at]);

  const planned = session.planned_duration_minutes * 60;
  const remaining = planned - elapsed;
  const isOvertime = !isNoTimerMode && remaining < 0;

  // Auto-complete and play sound when timer reaches zero
  useEffect(() => {
    if (isNoTimerMode || isPaused) return;
    if (remaining <= 0 && !soundPlayedRef.current) {
      soundPlayedRef.current = true;
      playFocusCompleteSound();
      onCancel(); // Auto-complete the session
    }
  }, [remaining, isNoTimerMode, isPaused, onCancel]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(Math.abs(seconds) / 60);
    const secs = Math.abs(seconds) % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="bg-gradient-to-br from-primary-500/20 to-primary-600/20 rounded-xl p-4 border border-primary-500/30">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Timer className="w-5 h-5 text-primary-400" />
          <span className="text-sm font-medium text-primary-300">
            {isPaused ? t('pause') : t('focus')}
          </span>
        </div>
        <div className={`text-2xl font-bold tabular-nums ${isOvertime ? 'text-orange-400' : 'text-white'}`}>
          {isOvertime && '+'}
          {isNoTimerMode ? formatTime(elapsed) : formatTime(isOvertime ? -remaining : remaining)}
        </div>
      </div>

      <div className="flex gap-2">
        <Button
          variant={isPaused ? 'primary' : 'secondary'}
          onClick={isPaused ? onResume : onPause}
          isLoading={isPaused ? isResumeLoading : isPauseLoading}
          className="flex-1"
        >
          {isPaused ? (
            <><Play className="w-4 h-4 mr-1" />{t('resume')}</>
          ) : (
            <><Pause className="w-4 h-4 mr-1" />{t('pause')}</>
          )}
        </Button>
        <Button
          variant="secondary"
          onClick={onCancel}
          className="px-3 bg-green-500/20 hover:bg-green-500/30 border-green-500/50 text-green-400"
          title={t('complete')}
        >
          <Square className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}

export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const taskId = Number(params.id);
  const { t, language } = useLanguage();

  const {
    user,
    latestMood,
    setLatestMood,
    setActiveSession,
    showXPAnimation,
    pushXPToast,
    activeSessions,
    setActiveSessions,
    updateActiveSession,
    removeActiveSession,
    getSessionForTask,
  } = useAppStore();
  const [showMoodModal, setShowMoodModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showAddSubtask, setShowAddSubtask] = useState(false);
  const [showTypeModal, setShowTypeModal] = useState(false);
  const [showDurationModal, setShowDurationModal] = useState(false);
  const [pendingFocusSubtaskId, setPendingFocusSubtaskId] = useState<number | null>(null);
  const [selectedDuration, setSelectedDuration] = useState<number | null>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('moodsprint_focus_duration');
      if (saved) {
        const num = parseInt(saved);
        if (num >= 5 && num <= 120) return num;
      }
    }
    return DEFAULT_FOCUS_DURATION;
  });
  const [customDurationInput, setCustomDurationInput] = useState('');
  const [newSubtaskTitle, setNewSubtaskTitle] = useState('');
  const [moodLoading, setMoodLoading] = useState(false);
  const [showEditTask, setShowEditTask] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editPriority, setEditPriority] = useState<'low' | 'medium' | 'high'>('medium');
  const [editTaskType, setEditTaskType] = useState<TaskType | null>(null);
  const [editDueDate, setEditDueDate] = useState('');
  const [editReminderEnabled, setEditReminderEnabled] = useState(false);
  const [editReminderDate, setEditReminderDate] = useState('');
  const [editReminderTime, setEditReminderTime] = useState('');
  const [showEditSubtask, setShowEditSubtask] = useState(false);
  const [editingSubtask, setEditingSubtask] = useState<{ id: number; title: string; estimated_minutes: number } | null>(null);
  const [earnedCard, setEarnedCard] = useState<EarnedCard | null>(null);
  const [showCardModal, setShowCardModal] = useState(false);
  const [showCardTutorial, setShowCardTutorial] = useState(false);
  const [showLevelUpModal, setShowLevelUpModal] = useState(false);
  const [levelUpData, setLevelUpData] = useState<{
    newLevel: number;
    rewards: LevelRewardItem[];
    genreUnlockAvailable?: { can_unlock: boolean; available_genres: string[]; suggested_genres?: string[] } | null;
  } | null>(null);
  const [showPriorityModal, setShowPriorityModal] = useState(false);
  const [showActionModal, setShowActionModal] = useState(false);
  const [showCompanionPicker, setShowCompanionPicker] = useState(false);
  const [showStreakMilestoneModal, setShowStreakMilestoneModal] = useState(false);
  const [streakMilestoneData, setStreakMilestoneData] = useState<{ milestone_days: number; xp_bonus: number; card_earned?: { id: number; name: string; emoji: string; rarity: string } } | null>(null);
  const [showShareModal, setShowShareModal] = useState(false);
  const [shareMessage, setShareMessage] = useState('');
  const [selectedFriendId, setSelectedFriendId] = useState<number | null>(null);

  // Show Telegram back button
  useEffect(() => {
    const handleBack = () => {
      router.push('/');
    };
    showBackButton(handleBack);
    return () => {
      hideBackButton();
    };
  }, [router]);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => tasksService.getTask(taskId),
    enabled: !!taskId,
  });

  // Fetch active focus sessions
  const { data: activeSessionsData } = useQuery({
    queryKey: ['focus', 'active'],
    queryFn: () => focusService.getActiveSession(),
  });

  // Sync active sessions to store
  useEffect(() => {
    if (activeSessionsData?.data?.sessions) {
      setActiveSessions(activeSessionsData.data.sessions);
    }
  }, [activeSessionsData, setActiveSessions]);

  // Get active session for this task
  const activeSession = useMemo(() => {
    return getSessionForTask(taskId);
  }, [getSessionForTask, taskId, activeSessions]);

  // Fetch companion card for hint
  const { data: companionData } = useQuery({
    queryKey: ['companion'],
    queryFn: () => cardsService.getCompanion(),
    staleTime: 5 * 60 * 1000,
  });
  const companion = companionData?.data?.companion;

  // Fetch cards for companion picker
  const { data: cardsForPicker } = useQuery({
    queryKey: ['cards'],
    queryFn: () => cardsService.getCards(),
    enabled: showCompanionPicker,
    staleTime: 5 * 60 * 1000,
  });
  const ownedCards = cardsForPicker?.data?.cards || [];

  const setCompanionMutation = useMutation({
    mutationFn: (cardId: number) => cardsService.setCompanion(cardId),
    onSuccess: () => {
      hapticFeedback('success');
      queryClient.invalidateQueries({ queryKey: ['companion'] });
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      setShowCompanionPicker(false);
    },
  });

  const removeCompanionMutation = useMutation({
    mutationFn: () => cardsService.removeCompanion(),
    onSuccess: () => {
      hapticFeedback('light');
      queryClient.invalidateQueries({ queryKey: ['companion'] });
      queryClient.invalidateQueries({ queryKey: ['cards'] });
    },
  });

  // Fetch friends for share modal
  const { data: friendsData } = useQuery({
    queryKey: ['friends'],
    queryFn: () => cardsService.getFriends(),
    enabled: showShareModal,
    staleTime: 5 * 60 * 1000,
  });
  const friendsList = friendsData?.data?.friends || [];

  // Fetch shares for this task (owner only)
  const { data: sharesData, refetch: refetchShares } = useQuery({
    queryKey: ['task', taskId, 'shares'],
    queryFn: () => tasksService.getTaskShares(taskId),
    enabled: !!taskId,
    staleTime: 30 * 1000,
  });
  const taskShares = sharesData?.data?.shares || [];

  // Find if current user is a shared assignee
  const sharedRecord = useMemo(() => {
    // This will be populated from task data's is_shared_assignee flag
    return null;
  }, []);

  const shareTaskMutation = useMutation({
    mutationFn: ({ friendId, message }: { friendId: number; message?: string }) =>
      tasksService.shareTask(taskId, friendId, message),
    onSuccess: () => {
      setShowShareModal(false);
      setShareMessage('');
      setSelectedFriendId(null);
      refetchShares();
      hapticFeedback('success');
    },
  });

  const pingSharedTaskMutation = useMutation({
    mutationFn: (sharedId: number) => tasksService.pingSharedTask(sharedId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      hapticFeedback('success');
      router.push('/');
    },
  });

  const declineSharedTaskMutation = useMutation({
    mutationFn: (sharedId: number) => tasksService.declineSharedTask(sharedId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      router.push('/');
      hapticFeedback('light');
    },
  });

  const [showNoNewStepsMessage, setShowNoNewStepsMessage] = useState(false);
  const [noNewStepsReason, setNoNewStepsReason] = useState('');

  const decomposeMutation = useMutation({
    mutationFn: (moodId?: number) => tasksService.decomposeTask(taskId, moodId),
    onSuccess: (result) => {
      refetch();
      if (result.data?.no_new_steps) {
        // Task is already well-decomposed
        setNoNewStepsReason(result.data.message || t('taskAlreadyDecomposed'));
        setShowNoNewStepsMessage(true);
        hapticFeedback('warning');
        // Auto-hide after 3 seconds
        setTimeout(() => setShowNoNewStepsMessage(false), 3000);
      } else {
        hapticFeedback('success');
      }
    },
  });

  const toggleSubtaskMutation = useMutation({
    mutationFn: ({ subtaskId, completed }: { subtaskId: number; completed: boolean }) =>
      tasksService.updateSubtask(subtaskId, {
        status: completed ? 'completed' : 'pending',
      }),
    onSuccess: (result) => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['user', 'stats'] });
      queryClient.invalidateQueries({ queryKey: ['daily', 'goals'] });
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
        });
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

  const deleteMutation = useMutation({
    mutationFn: () => tasksService.deleteTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      router.push('/');
      hapticFeedback('success');
    },
  });

  const createSubtaskMutation = useMutation({
    mutationFn: (title: string) => tasksService.createSubtask(taskId, { title }),
    onSuccess: () => {
      refetch();
      setShowAddSubtask(false);
      setNewSubtaskTitle('');
      hapticFeedback('success');
    },
  });

  const startFocusMutation = useMutation({
    mutationFn: ({ subtaskId, duration }: { subtaskId: number; duration: number | null }) =>
      focusService.startSession({
        subtask_id: subtaskId,
        // null duration means "work without timer" - use very long duration
        planned_duration_minutes: duration ?? 480,
      }),
    onSuccess: (result) => {
      if (result.success && result.data) {
        setActiveSession(result.data.session);
        setShowDurationModal(false);
        setShowActionModal(false);
        setPendingFocusSubtaskId(null);
        hapticFeedback('success');
      }
    },
  });

  const startTaskFocusMutation = useMutation({
    mutationFn: (duration: number | null) =>
      focusService.startSession({
        task_id: taskId,
        // null duration means "work without timer" - use very long duration
        planned_duration_minutes: duration ?? 480,
      }),
    onSuccess: (result) => {
      if (result.success && result.data) {
        setActiveSession(result.data.session);
        setShowDurationModal(false);
        setShowActionModal(false);
        hapticFeedback('success');
      }
    },
  });

  // Focus session control mutations
  const pauseSessionMutation = useMutation({
    mutationFn: (sessionId: number) => focusService.pauseSession(sessionId),
    onSuccess: (result) => {
      if (result.success && result.data?.session) {
        updateActiveSession(result.data.session);
        queryClient.invalidateQueries({ queryKey: ['focus', 'active'] });
        hapticFeedback('light');
      }
    },
    onError: (error) => {
      console.error('Pause failed:', error);
      queryClient.invalidateQueries({ queryKey: ['focus', 'active'] });
    },
  });

  const resumeSessionMutation = useMutation({
    mutationFn: (sessionId: number) => focusService.resumeSession(sessionId),
    onSuccess: (result) => {
      if (result.success && result.data?.session) {
        updateActiveSession(result.data.session);
        queryClient.invalidateQueries({ queryKey: ['focus', 'active'] });
        hapticFeedback('light');
      }
    },
    onError: (error) => {
      console.error('Resume failed:', error);
      queryClient.invalidateQueries({ queryKey: ['focus', 'active'] });
    },
  });

  const completeSessionMutation = useMutation({
    mutationFn: (sessionId: number) => focusService.completeSession(sessionId),
    onSuccess: (result) => {
      if (result.success && result.data?.session) {
        removeActiveSession(result.data.session.id);
        refetch();
        queryClient.invalidateQueries({ queryKey: ['tasks'] });
        queryClient.invalidateQueries({ queryKey: ['focus', 'active'] });
        if (result.data.xp_earned) {
          pushXPToast({ type: 'player', amount: result.data.xp_earned, currentXp: user?.xp ?? 0, xpForNext: user?.xp_for_next_level ?? 100, level: user?.level ?? 1 });
        }
        hapticFeedback('success');
      }
    },
  });

  const cancelSessionMutation = useMutation({
    mutationFn: (sessionId: number) => focusService.cancelSession(sessionId),
    onSuccess: (result) => {
      if (result.success && result.data?.session) {
        removeActiveSession(result.data.session.id);
        queryClient.invalidateQueries({ queryKey: ['focus', 'active'] });
        hapticFeedback('light');
      }
    },
  });

  // Open duration modal before starting focus
  const handleStartFocus = (subtaskId?: number) => {
    setPendingFocusSubtaskId(subtaskId ?? null);
    const saved = localStorage.getItem('moodsprint_focus_duration');
    const defaultDur = saved ? parseInt(saved) : DEFAULT_FOCUS_DURATION;
    setSelectedDuration(defaultDur >= 5 && defaultDur <= 120 ? defaultDur : DEFAULT_FOCUS_DURATION);
    setCustomDurationInput('');
    setShowDurationModal(true);
  };

  // Confirm duration and start focus
  const confirmStartFocus = () => {
    if (pendingFocusSubtaskId !== null) {
      startFocusMutation.mutate({ subtaskId: pendingFocusSubtaskId, duration: selectedDuration });
    } else {
      startTaskFocusMutation.mutate(selectedDuration);
    }
  };

  const completeTaskMutation = useMutation({
    mutationFn: async () => {
      // Cancel any active session for this task first
      const activeSession = getSessionForTask(taskId);
      if (activeSession) {
        await focusService.cancelSession(activeSession.id);
        removeActiveSession(activeSession.id);
      }
      return tasksService.updateTask(taskId, { status: 'completed' });
    },
    onSuccess: (result) => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['user', 'stats'] });
      queryClient.invalidateQueries({ queryKey: ['daily', 'goals'] });
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      queryClient.invalidateQueries({ queryKey: ['focus', 'active'] });
      if (result.data?.xp_earned) {
        pushXPToast({ type: 'player', amount: result.data.xp_earned, currentXp: user?.xp ?? 0, xpForNext: user?.xp_for_next_level ?? 100, level: user?.level ?? 1 });
      }
      // Show card earned modal if card was generated
      if (result.data?.card_earned) {
        setEarnedCard({
          ...result.data.card_earned,
          quick_completion: result.data.quick_completion,
          quick_completion_message: result.data.quick_completion_message,
        });
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
    mutationFn: () => tasksService.updateTask(taskId, { status: 'pending' }),
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      hapticFeedback('success');
    },
  });

  const updateTypeMutation = useMutation({
    mutationFn: (taskType: TaskType) =>
      tasksService.updateTask(taskId, { task_type: taskType }),
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setShowTypeModal(false);
      hapticFeedback('success');
    },
  });

  const updatePriorityMutation = useMutation({
    mutationFn: (priority: 'low' | 'medium' | 'high') =>
      tasksService.updateTask(taskId, { priority }),
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setShowPriorityModal(false);
      hapticFeedback('success');
    },
  });

  const updateTaskMutation = useMutation({
    mutationFn: (data: UpdateTaskInput) =>
      tasksService.updateTask(taskId, data),
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setShowEditTask(false);
      hapticFeedback('success');
    },
  });

  const updateSubtaskMutation = useMutation({
    mutationFn: ({ subtaskId, data }: { subtaskId: number; data: { title?: string; estimated_minutes?: number } }) =>
      tasksService.updateSubtask(subtaskId, data),
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setShowEditSubtask(false);
      setEditingSubtask(null);
      hapticFeedback('success');
    },
  });

  const handleDecompose = () => {
    if (!latestMood) {
      setShowMoodModal(true);
    } else {
      decomposeMutation.mutate(latestMood.id);
    }
  };

  const handleMoodSubmit = async (mood: MoodLevel, energy: EnergyLevel, note?: string) => {
    setMoodLoading(true);
    try {
      const result = await moodService.createMoodCheck({ mood, energy, note });
      if (result.success && result.data) {
        setLatestMood(result.data.mood_check);
        setShowMoodModal(false);
        // Now decompose with the new mood
        decomposeMutation.mutate(result.data.mood_check.id);
        if (result.data.xp_earned) {
          pushXPToast({ type: 'player', amount: result.data.xp_earned, currentXp: user?.xp ?? 0, xpForNext: user?.xp_for_next_level ?? 100, level: user?.level ?? 1 });
        }
      }
    } finally {
      setMoodLoading(false);
    }
  };

  const task = data?.data?.task;
  const isSharedAssignee = task && user && task.user_id !== user.id;

  // Find shared record for assignee mode (to get shared_id for ping/decline)
  const { data: sharedWithMeData } = useQuery({
    queryKey: ['tasks', 'shared'],
    queryFn: () => tasksService.getSharedWithMe(),
    enabled: !!isSharedAssignee,
    staleTime: 30 * 1000,
  });
  const mySharedRecord = useMemo(() => {
    if (!isSharedAssignee || !sharedWithMeData?.data?.shared_tasks) return null;
    return sharedWithMeData.data.shared_tasks.find(
      (s) => s.task_id === taskId && s.status === 'accepted'
    ) || null;
  }, [isSharedAssignee, sharedWithMeData, taskId]);

  if (isLoading) {
    return (
      <div className="p-4">
        <Card className="h-32 animate-pulse" />
      </div>
    );
  }

  if (!task) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
        <div className="w-16 h-16 rounded-2xl bg-gray-800 border border-gray-700 flex items-center justify-center mb-4">
          <SearchX className="w-8 h-8 text-gray-500" />
        </div>
        <h2 className="text-lg font-semibold text-white mb-1">{t('taskNotFound')}</h2>
        <p className="text-sm text-gray-500 mb-6 max-w-[260px]">
          {t('taskNotFoundDesc')}
        </p>
        <Button onClick={() => router.push('/')} variant="primary" className="px-8">
          {t('goToMain')}
        </Button>
      </div>
    );
  }

  const subtasks = task.subtasks || [];

  return (
    <div className="relative">
      <ScrollBackdrop />
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <h1 className="text-lg font-bold text-white break-words">{task.title}</h1>
          {isSharedAssignee && (
            <p className="text-xs text-gray-500 mt-0.5">
              {t('sharedByName').replace('{name}', taskShares.length > 0 ? (taskShares[0]?.owner_name || '') : '')}
            </p>
          )}
        </div>
        {!isSharedAssignee && task.status !== 'completed' && task.status !== 'archived' && (
          <button
            onClick={() => setShowShareModal(true)}
            className="p-2 bg-primary-500/20 hover:bg-primary-500/30 rounded-full text-primary-400 hover:text-primary-300 flex-shrink-0 transition-colors"
          >
            <Share2 className="w-5 h-5" />
          </button>
        )}
        {!isSharedAssignee && task.status !== 'completed' && (
          <button
            onClick={() => {
              setEditTitle(task.title);
              setEditDescription(task.description || '');
              setEditPriority(task.priority as 'low' | 'medium' | 'high');
              setEditTaskType(task.task_type as TaskType | null);
              setEditDueDate(task.due_date || '');
              // Initialize reminder state
              if (task.scheduled_at) {
                const scheduledDate = new Date(task.scheduled_at);
                setEditReminderEnabled(true);
                // Use local date components (not UTC) so timezone doesn't shift values
                const y = scheduledDate.getFullYear();
                const m = String(scheduledDate.getMonth() + 1).padStart(2, '0');
                const d = String(scheduledDate.getDate()).padStart(2, '0');
                setEditReminderDate(`${y}-${m}-${d}`);
                setEditReminderTime(scheduledDate.toTimeString().slice(0, 5));
              } else {
                setEditReminderEnabled(false);
                // Default reminder date to task due date if it's in the future
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                const taskDue = task.due_date ? new Date(task.due_date + 'T00:00:00') : null;
                const useTaskDate = taskDue && taskDue >= today;
                const defaultDate = useTaskDate ? taskDue : new Date();
                if (!useTaskDate) defaultDate.setHours(defaultDate.getHours() + 1);
                const y = defaultDate.getFullYear();
                const m = String(defaultDate.getMonth() + 1).padStart(2, '0');
                const d = String(defaultDate.getDate()).padStart(2, '0');
                setEditReminderDate(`${y}-${m}-${d}`);
                const timeDate = useTaskDate ? new Date(Date.now() + 3600000) : defaultDate;
                setEditReminderTime(timeDate.toTimeString().slice(0, 5));
              }
              setShowEditTask(true);
            }}
            className="p-2 hover:bg-gray-700 rounded-full text-gray-400 hover:text-white flex-shrink-0"
          >
            <Pencil className="w-5 h-5" />
          </button>
        )}
        {!isSharedAssignee && (
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="p-2 hover:bg-red-500/20 rounded-full text-gray-400 hover:text-red-500 flex-shrink-0"
          >
            <Trash2 className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Task Info */}
      <Card>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            {task.task_type && (
              task.status !== 'completed' ? (
                <button
                  onClick={() => setShowTypeModal(true)}
                  className={`text-xs px-2 py-0.5 rounded-full transition-opacity hover:opacity-80 ${TASK_TYPE_COLORS[task.task_type]}`}
                >
                  {TASK_TYPE_EMOJIS[task.task_type]} {TASK_TYPE_LABELS[task.task_type]}
                </button>
              ) : (
                <span className={`text-xs px-2 py-0.5 rounded-full ${TASK_TYPE_COLORS[task.task_type]}`}>
                  {TASK_TYPE_EMOJIS[task.task_type]} {TASK_TYPE_LABELS[task.task_type]}
                </span>
              )
            )}
            {!task.task_type && task.status !== 'completed' && (
              <button
                onClick={() => setShowTypeModal(true)}
                className="text-xs px-2 py-0.5 rounded-full bg-gray-600/50 text-gray-400 border border-dashed border-gray-500 hover:bg-gray-600"
              >
                {t('addType')}
              </button>
            )}
            {task.status !== 'completed' ? (
              <button
                onClick={() => setShowPriorityModal(true)}
                className={`text-xs px-2 py-0.5 rounded-full transition-opacity hover:opacity-80 ${PRIORITY_COLORS[task.priority]}`}
              >
                {task.priority === 'low' ? t('priorityLow') : task.priority === 'medium' ? t('priorityMedium') : t('priorityHigh')}
              </button>
            ) : (
              <span className={`text-xs px-2 py-0.5 rounded-full ${PRIORITY_COLORS[task.priority]}`}>
                {task.priority === 'low' ? t('priorityLow') : task.priority === 'medium' ? t('priorityMedium') : t('priorityHigh')}
              </span>
            )}
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              task.status === 'completed'
                ? 'bg-green-500/20 text-green-400'
                : task.status === 'archived'
                ? 'bg-orange-500/20 text-orange-400'
                : task.status === 'in_progress'
                ? 'bg-blue-500/20 text-blue-400'
                : 'bg-gray-500/20 text-gray-400'
            }`}>
              {task.status === 'completed' ? t('statusCompleted') : task.status === 'archived' ? t('archived') : task.status === 'in_progress' ? t('statusInProgress') : t('statusPending')}
            </span>
          </div>
          <span className="text-sm text-gray-500">
            {task.status === 'completed' ? 100 : task.progress_percent}{t('percentComplete')}
          </span>
        </div>
        <Progress value={task.status === 'completed' ? 100 : task.progress_percent} color={task.status === 'completed' ? 'success' : 'primary'} />

        {/* Deadline & Reminder */}
        {(task.due_date || task.scheduled_at) && (
          <div className="flex flex-col gap-2 mt-3 pt-3 border-t border-gray-700/50 text-sm">
            {task.due_date && (
              <div className="flex items-center gap-1.5 text-gray-300">
                <CalendarDays className="w-4 h-4 text-primary-400" />
                <span>{t('deadline')}:</span>
                <span className={`font-medium ${
                  new Date(task.due_date) < new Date() && task.status !== 'completed'
                    ? 'text-red-400'
                    : 'text-white'
                }`}>
                  {new Date(task.due_date).toLocaleDateString(
                    language === 'ru' ? 'ru-RU' : 'en-US',
                    { day: 'numeric', month: 'short', year: 'numeric' }
                  )}
                </span>
              </div>
            )}
            {task.scheduled_at && (
              <div className="flex items-center gap-1.5 text-gray-300">
                <Bell className="w-4 h-4 text-yellow-400" />
                <span>{t('reminderTime')}:</span>
                <span className="font-medium text-white">
                  {new Date(task.scheduled_at).toLocaleString(
                    language === 'ru' ? 'ru-RU' : 'en-US',
                    { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }
                  )}
                </span>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Rarity Odds Bar */}
      {task.status !== 'completed' && task.rarity_odds && (
        <div className="flex items-center gap-1.5 px-1">
          <span className="text-[10px] text-gray-500 mr-1">{t('cardOdds')}:</span>
          {Object.entries(task.rarity_odds).map(([rarity, pct]) => {
            const colors: Record<string, string> = {
              common: 'bg-gray-500',
              uncommon: 'bg-green-500',
              rare: 'bg-blue-500',
              epic: 'bg-purple-500',
              legendary: 'bg-yellow-500',
            };
            return (
              <div key={rarity} className="flex items-center gap-0.5">
                <div className={`w-1.5 h-1.5 rounded-full ${colors[rarity] || 'bg-gray-500'}`} />
                <span className="text-[10px] text-gray-500">{pct}%</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Restore button for archived tasks */}
      {task.status === 'archived' && (
        <Button
          variant="secondary"
          onClick={() => restoreTaskMutation.mutate()}
          isLoading={restoreTaskMutation.isPending}
          className="w-full h-14 bg-orange-500/20 hover:bg-orange-500/30 border-orange-500/50 text-orange-400"
        >
          <RotateCcw className="w-5 h-5 mr-2" />
          {t('restore')}
        </Button>
      )}

      {/* Shared assignee actions */}
      {isSharedAssignee && mySharedRecord && (
        <div className="flex gap-2">
          <Button
            variant="primary"
            onClick={() => pingSharedTaskMutation.mutate(mySharedRecord.id)}
            isLoading={pingSharedTaskMutation.isPending}
            className="flex-1 h-14"
          >
            <Check className="w-5 h-5 mr-2" />
            {t('notifyOwner')}
          </Button>
          <Button
            variant="secondary"
            onClick={() => declineSharedTaskMutation.mutate(mySharedRecord.id)}
            isLoading={declineSharedTaskMutation.isPending}
            className="flex-shrink-0 h-14 px-4"
          >
            {t('declineTask')}
          </Button>
        </div>
      )}

      {/* Shared with indicator (for owner) */}
      {!isSharedAssignee && taskShares.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-gray-500 px-1">{t('sharedWith')}</p>
          {taskShares
            .filter((s) => s.status !== 'declined')
            .map((s) => {
              const statusConfig = {
                completed: { label: t('done'), color: 'bg-green-500/20 text-green-400 border-green-500/30', icon: '✓' },
                accepted: { label: t('statusInProgress'), color: 'bg-blue-500/20 text-blue-400 border-blue-500/30', icon: '→' },
                pending: { label: t('statusPending'), color: 'bg-amber-500/20 text-amber-400 border-amber-500/30', icon: '⏳' },
              };
              const cfg = statusConfig[s.status as keyof typeof statusConfig] || statusConfig.pending;
              return (
                <div
                  key={s.id}
                  className={`flex items-center justify-between rounded-xl p-3 border ${cfg.color}`}
                >
                  <div className="flex items-center gap-2">
                    <Share2 className="w-4 h-4" />
                    <span className="text-sm font-medium">{s.assignee_name || '?'}</span>
                  </div>
                  <span className="text-xs font-medium">{cfg.icon} {cfg.label}</span>
                </div>
              );
            })}
        </div>
      )}

      {/* Action Buttons or Active Session Timer */}
      {!isSharedAssignee && task.status !== 'completed' && task.status !== 'archived' && (
        activeSession ? (
          <FocusTimer
            session={activeSession}
            onPause={() => pauseSessionMutation.mutate(activeSession.id)}
            onResume={() => resumeSessionMutation.mutate(activeSession.id)}
            onCancel={() => completeSessionMutation.mutate(activeSession.id)}
            isPauseLoading={pauseSessionMutation.isPending}
            isResumeLoading={resumeSessionMutation.isPending}
            t={t}
          />
        ) : (
          <div className="flex gap-2">
            <Button
              variant="primary"
              onClick={() => handleStartFocus()}
              className="flex-1 h-14"
            >
              <Timer className="w-5 h-5 mr-2" />
              {t('startFocusButton')}
            </Button>
            <Button
              variant="secondary"
              onClick={() => completeTaskMutation.mutate()}
              isLoading={completeTaskMutation.isPending}
              className="flex-1 h-14 bg-green-500/20 hover:bg-green-500/30 border-green-500/50 text-green-400"
            >
              <Check className="w-5 h-5 mr-2" />
              {t('completeTask')}
            </Button>
          </div>
        )
      )}

      {/* Companion indicator */}
      {task.status !== 'completed' && (
        companion ? (
          <button
            onClick={() => setShowCompanionPicker(true)}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl bg-pink-500/10 border border-pink-500/20 text-left -mt-1"
          >
            {companion.image_url ? (
              <img src={companion.image_url} alt="" className="w-8 h-8 rounded-lg object-cover" />
            ) : (
              <span className="text-lg">{companion.emoji || '🐾'}</span>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-pink-400 truncate">{companion.name}</p>
              <p className="text-[10px] text-gray-500">{t('companionHint')}</p>
            </div>
            {activeSession && (
              <span className="text-[10px] text-pink-400 animate-pulse">{t('companionGainingXp')}</span>
            )}
          </button>
        ) : (
          <button
            onClick={() => setShowCompanionPicker(true)}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-xl bg-gray-800/50 border border-dashed border-gray-600 text-left -mt-1"
          >
            <span className="text-sm">🐾</span>
            <span className="text-xs text-gray-500">{t('setCompanion')}</span>
          </button>
        )
      )}

      {/* Decompose Button */}
      {subtasks.length === 0 && task.status !== 'completed' && (
        <Button
          onClick={handleDecompose}
          isLoading={decomposeMutation.isPending}
          className="w-full"
        >
          <Wand2 className="w-4 h-4 mr-2" />
          {t('decomposeWithAI')}
        </Button>
      )}

      {/* Description */}
      {task.description && (
        <div className="bg-gray-800/50 rounded-xl p-3">
          <p className="text-sm text-gray-300 whitespace-pre-wrap">{task.description}</p>
        </div>
      )}

      {/* No new steps notification */}
      {showNoNewStepsMessage && (
        <div className="fixed top-16 left-4 right-4 z-50 animate-in slide-in-from-top-2">
          <div className="bg-amber-500/20 border border-amber-500/50 text-amber-300 rounded-xl p-3 text-sm text-center backdrop-blur-sm">
            {noNewStepsReason}
          </div>
        </div>
      )}

      {/* Subtasks */}
      {(subtasks.length > 0 || decomposeMutation.isPending) && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-white">{t('steps')}</h2>
            {task.status !== 'completed' && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowAddSubtask(true)}
                  className="text-sm text-primary-500 hover:text-primary-600 flex items-center gap-1"
                >
                  <Plus className="w-4 h-4" />
                  {t('add')}
                </button>
                <button
                  onClick={handleDecompose}
                  disabled={decomposeMutation.isPending}
                  className="text-sm text-gray-400 hover:text-gray-300 flex items-center gap-1 disabled:opacity-50"
                >
                  {decomposeMutation.isPending ? (
                    <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Wand2 className="w-4 h-4" />
                  )}
                </button>
              </div>
            )}
          </div>

          <div className="space-y-2">
            {/* Skeleton loaders while decomposing */}
            {decomposeMutation.isPending && (
              <>
                {[1, 2, 3].map((i) => (
                  <div
                    key={`skeleton-${i}`}
                    className="bg-gray-800/50 rounded-xl p-3 animate-pulse"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-5 h-5 rounded-full bg-gray-700" />
                      <div className="flex-1">
                        <div className="h-4 bg-gray-700 rounded w-3/4 mb-1" />
                        <div className="h-3 bg-gray-700/50 rounded w-1/4" />
                      </div>
                    </div>
                  </div>
                ))}
              </>
            )}

            {/* Actual subtasks */}
            {!decomposeMutation.isPending && subtasks.map((subtask) => (
              <SubtaskItem
                key={subtask.id}
                subtask={subtask}
                onToggle={() =>
                  toggleSubtaskMutation.mutate({
                    subtaskId: subtask.id,
                    completed: subtask.status !== 'completed',
                  })
                }
                onFocus={() => handleStartFocus(subtask.id)}
                onEdit={() => {
                  setEditingSubtask({
                    id: subtask.id,
                    title: subtask.title,
                    estimated_minutes: subtask.estimated_minutes,
                  });
                  setShowEditSubtask(true);
                }}
                disabled={toggleSubtaskMutation.isPending}
              />
            ))}
          </div>
        </div>
      )}

      {/* Add Subtask when no subtasks exist */}
      {subtasks.length === 0 && task.status !== 'completed' && (
        <Button
          variant="secondary"
          onClick={() => setShowAddSubtask(true)}
          className="w-full mt-2"
        >
          <Plus className="w-4 h-4 mr-2" />
          {t('addStepManually')}
        </Button>
      )}

      {/* Mood Modal */}
      <Modal
        isOpen={showMoodModal}
        onClose={() => setShowMoodModal(false)}
        title={t('firstCheckMood')}
      >
        <p className="text-sm text-gray-500 mb-4">
          {t('moodDecomposeHint')}
        </p>
        <MoodSelector onSubmit={handleMoodSubmit} isLoading={moodLoading} />
      </Modal>

      {/* Delete Confirmation */}
      <Modal
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        title={t('deleteTask')}
      >
        <p className="text-gray-600 mb-4">
          {t('deleteTaskConfirm').replace('{title}', task.title)}
        </p>
        <div className="flex gap-3">
          <Button
            variant="secondary"
            onClick={() => setShowDeleteConfirm(false)}
            className="flex-1"
          >
            {t('cancel')}
          </Button>
          <Button
            variant="danger"
            onClick={() => deleteMutation.mutate()}
            isLoading={deleteMutation.isPending}
            className="flex-1"
          >
            {t('delete')}
          </Button>
        </div>
      </Modal>

      {/* Edit Task Modal */}
      <Modal
        isOpen={showEditTask}
        onClose={() => setShowEditTask(false)}
        title={t('editTask')}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              {t('title')}
            </label>
            <input
              type="text"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              placeholder={t('taskTitlePlaceholder')}
              className="w-full p-3 bg-gray-800 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              {t('description')}
            </label>
            <textarea
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              placeholder={t('taskDescriptionPlaceholder')}
              rows={3}
              className="w-full p-3 bg-gray-800 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
            />
          </div>
          {/* Priority */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              {t('taskPriority')}
            </label>
            <div className="flex gap-2">
              {(['low', 'medium', 'high'] as const).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setEditPriority(p)}
                  className={`flex-1 py-2 px-3 text-sm font-medium rounded-xl transition-all ${
                    editPriority === p
                      ? `${PRIORITY_COLORS[p]} ring-2 ring-offset-2 ring-offset-gray-900`
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  {p === 'low' ? t('priorityLow') : p === 'medium' ? t('priorityMedium') : t('priorityHigh')}
                </button>
              ))}
            </div>
          </div>
          {/* Task Type */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              {t('taskType')}
            </label>
            <div className="grid grid-cols-4 gap-2">
              {TASK_TYPES.map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setEditTaskType(type)}
                  className={`p-2 rounded-xl text-center transition-all ${
                    editTaskType === type
                      ? `${TASK_TYPE_COLORS[type]} ring-2 ring-offset-2 ring-offset-gray-900`
                      : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                  }`}
                >
                  <span className="text-lg">{TASK_TYPE_EMOJIS[type]}</span>
                </button>
              ))}
            </div>
          </div>
          {/* Deadline */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              <span className="flex items-center gap-2">
                <CalendarDays className="w-4 h-4 text-primary-400" />
                {t('deadline')}
              </span>
            </label>
            <div className="flex gap-2">
              <DatePicker
                value={editDueDate || new Date().toISOString().split('T')[0]}
                onChange={setEditDueDate}
                className="flex-1"
              />
              {editDueDate && (
                <button
                  type="button"
                  onClick={() => setEditDueDate('')}
                  className="px-3 py-2 rounded-xl bg-gray-700 text-gray-400 hover:text-red-400 hover:bg-gray-600 transition-colors text-sm"
                >
                  ✕
                </button>
              )}
            </div>
          </div>
          {/* Reminder */}
          <div>
            <label className="flex items-center justify-between cursor-pointer p-3 rounded-xl bg-gray-800/50 border border-gray-700">
              <span className="flex items-center gap-2 text-sm font-medium text-gray-300">
                <Bell className="w-4 h-4 text-primary-400" />
                {t('setReminder')}
              </span>
              <div className="relative">
                <input
                  type="checkbox"
                  checked={editReminderEnabled}
                  onChange={(e) => setEditReminderEnabled(e.target.checked)}
                  className="sr-only"
                />
                <div className={`w-10 h-5 rounded-full transition-colors ${editReminderEnabled ? 'bg-primary-500' : 'bg-gray-600'}`}>
                  <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${editReminderEnabled ? 'translate-x-5' : 'translate-x-0.5'}`} />
                </div>
              </div>
            </label>
            {editReminderEnabled && (
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">{t('date')}</label>
                  <DatePicker
                    value={editReminderDate || new Date().toISOString().split('T')[0]}
                    onChange={setEditReminderDate}
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">{t('time')}</label>
                  <TimePicker
                    value={roundToFiveMinutes(editReminderTime)}
                    onChange={setEditReminderTime}
                  />
                </div>
              </div>
            )}
          </div>
          <div className="flex gap-3">
            <Button
              variant="secondary"
              onClick={() => setShowEditTask(false)}
              className="flex-1"
            >
              {t('cancel')}
            </Button>
            <Button
              onClick={() => {
                let scheduledAt: string | null | undefined = undefined;
                if (editReminderEnabled && editReminderDate && editReminderTime) {
                  const localDate = new Date(`${editReminderDate}T${editReminderTime}:00`);
                  scheduledAt = localDate.toISOString();
                } else if (!editReminderEnabled) {
                  scheduledAt = null; // Clear reminder if disabled
                }
                updateTaskMutation.mutate({
                  title: editTitle.trim(),
                  description: editDescription.trim() || undefined,
                  priority: editPriority,
                  task_type: editTaskType || undefined,
                  due_date: editDueDate || null,
                  scheduled_at: scheduledAt,
                });
              }}
              isLoading={updateTaskMutation.isPending}
              disabled={!editTitle.trim()}
              className="flex-1"
            >
              {t('save')}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Add Subtask Modal */}
      <Modal
        isOpen={showAddSubtask}
        onClose={() => {
          setShowAddSubtask(false);
          setNewSubtaskTitle('');
        }}
        title={t('addStep')}
      >
        <div className="space-y-4">
          <input
            type="text"
            value={newSubtaskTitle}
            onChange={(e) => setNewSubtaskTitle(e.target.value)}
            placeholder={t('stepTitlePlaceholder')}
            className="w-full p-3 bg-gray-800 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
            autoFocus
          />
          <div className="flex gap-3">
            <Button
              variant="secondary"
              onClick={() => {
                setShowAddSubtask(false);
                setNewSubtaskTitle('');
              }}
              className="flex-1"
            >
              {t('cancel')}
            </Button>
            <Button
              onClick={() => createSubtaskMutation.mutate(newSubtaskTitle)}
              isLoading={createSubtaskMutation.isPending}
              disabled={!newSubtaskTitle.trim()}
              className="flex-1"
            >
              {t('add')}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Edit Subtask Modal */}
      <Modal
        isOpen={showEditSubtask}
        onClose={() => {
          setShowEditSubtask(false);
          setEditingSubtask(null);
        }}
        title={t('editStep')}
      >
        {editingSubtask && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                {t('title')}
              </label>
              <input
                type="text"
                value={editingSubtask.title}
                onChange={(e) => setEditingSubtask({ ...editingSubtask, title: e.target.value })}
                placeholder={t('stepTitlePlaceholder')}
                className="w-full p-3 bg-gray-800 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                autoFocus
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                {t('timeMinutes')}
              </label>
              <input
                type="number"
                min={1}
                max={480}
                value={editingSubtask.estimated_minutes}
                onChange={(e) => setEditingSubtask({ ...editingSubtask, estimated_minutes: Math.max(1, parseInt(e.target.value) || 1) })}
                className="w-full p-3 bg-gray-800 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div className="flex gap-3">
              <Button
                variant="secondary"
                onClick={() => {
                  setShowEditSubtask(false);
                  setEditingSubtask(null);
                }}
                className="flex-1"
              >
                {t('cancel')}
              </Button>
              <Button
                onClick={() => updateSubtaskMutation.mutate({
                  subtaskId: editingSubtask.id,
                  data: {
                    title: editingSubtask.title.trim(),
                    estimated_minutes: editingSubtask.estimated_minutes,
                  },
                })}
                isLoading={updateSubtaskMutation.isPending}
                disabled={!editingSubtask.title.trim()}
                className="flex-1"
              >
                {t('save')}
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Task Type Modal */}
      <Modal
        isOpen={showTypeModal}
        onClose={() => setShowTypeModal(false)}
        title={t('taskType')}
      >
        <p className="text-sm text-gray-500 mb-4">
          {t('taskTypeHint')}
        </p>
        <div className="grid grid-cols-2 gap-2">
          {TASK_TYPES.map((type) => (
            <button
              key={type}
              onClick={() => updateTypeMutation.mutate(type)}
              disabled={updateTypeMutation.isPending}
              className={`p-3 rounded-xl text-left transition-all ${
                task.task_type === type
                  ? `${TASK_TYPE_COLORS[type]} ring-2 ring-offset-2 ring-offset-gray-900`
                  : 'bg-gray-800 hover:bg-gray-700 text-gray-300'
              }`}
            >
              <span className="text-lg mr-2">{TASK_TYPE_EMOJIS[type]}</span>
              <span className="text-sm font-medium">{TASK_TYPE_LABELS[type]}</span>
            </button>
          ))}
        </div>
      </Modal>

      {/* Duration Selection Modal */}
      <Modal
        isOpen={showDurationModal}
        onClose={() => {
          setShowDurationModal(false);
          setPendingFocusSubtaskId(null);
        }}
        title={t('chooseDuration')}
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-2">
            {[15, 25, 45, 60].map((d) => (
              <button
                key={d}
                onClick={() => {
                  setSelectedDuration(d);
                  setCustomDurationInput('');
                }}
                className={`p-3 rounded-xl text-center transition-all ${
                  selectedDuration === d && !customDurationInput
                    ? 'bg-primary-500 text-white ring-2 ring-primary-500 ring-offset-2 ring-offset-gray-900'
                    : 'bg-gray-800 hover:bg-gray-700 text-gray-300'
                }`}
              >
                <Timer className="w-5 h-5 mx-auto mb-1" />
                <span className="text-sm font-medium">{d} {t('min')}</span>
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <input
              type="number"
              min={5}
              max={120}
              value={customDurationInput}
              onChange={(e) => {
                const val = e.target.value;
                setCustomDurationInput(val);
                const num = parseInt(val);
                if (num >= 5 && num <= 120) {
                  setSelectedDuration(num);
                }
              }}
              onFocus={() => {
                if (!customDurationInput && selectedDuration && selectedDuration !== null) {
                  setCustomDurationInput(String(selectedDuration));
                }
              }}
              placeholder={t('orCustom')}
              className="flex-1 px-3 py-2.5 bg-gray-800 rounded-xl text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <span className="text-sm text-gray-500 whitespace-nowrap">{t('customMinutes')}</span>
          </div>

          <button
            onClick={() => {
              setSelectedDuration(null);
              setCustomDurationInput('');
            }}
            className={`w-full p-3 rounded-xl text-center transition-all ${
              selectedDuration === null
                ? 'bg-primary-500 text-white ring-2 ring-primary-500 ring-offset-2 ring-offset-gray-900'
                : 'bg-gray-800 hover:bg-gray-700 text-gray-300'
            }`}
          >
            <Infinity className="w-5 h-5 mx-auto mb-1" />
            <span className="text-sm font-medium">{t('withoutTimer')}</span>
          </button>

          <Button
            onClick={confirmStartFocus}
            isLoading={startFocusMutation.isPending || startTaskFocusMutation.isPending}
            className="w-full"
          >
            <Play className="w-4 h-4 mr-2" />
            {t('start')}
          </Button>
        </div>
      </Modal>

      {/* Priority Modal */}
      <Modal
        isOpen={showPriorityModal}
        onClose={() => setShowPriorityModal(false)}
        title={t('taskPriority')}
      >
        <div className="space-y-2">
          {([
            { value: 'high' as const, labelKey: 'priorityHigh' as const, icon: <ChevronUp className="w-4 h-4" /> },
            { value: 'medium' as const, labelKey: 'priorityMedium' as const, icon: null },
            { value: 'low' as const, labelKey: 'priorityLow' as const, icon: <ChevronDown className="w-4 h-4" /> },
          ]).map((priority) => (
            <button
              key={priority.value}
              onClick={() => updatePriorityMutation.mutate(priority.value)}
              disabled={updatePriorityMutation.isPending}
              className={`w-full p-3 rounded-xl text-left flex items-center gap-3 transition-all ${
                task.priority === priority.value
                  ? `${PRIORITY_COLORS[priority.value]} ring-2 ring-offset-2 ring-offset-gray-900`
                  : 'bg-gray-800 hover:bg-gray-700 text-gray-300'
              }`}
            >
              <span className={`w-8 h-8 rounded-full flex items-center justify-center ${PRIORITY_COLORS[priority.value]}`}>
                {priority.icon || <span className="w-2 h-2 rounded-full bg-current" />}
              </span>
              <span className="font-medium">{t(priority.labelKey)}</span>
            </button>
          ))}
        </div>
      </Modal>

      {/* Action Selection Modal */}
      <Modal
        isOpen={showActionModal}
        onClose={() => setShowActionModal(false)}
        title={t('chooseAction')}
      >
        <div className="space-y-3">
          {/* Start Focus Option */}
          <button
            onClick={() => {
              setShowActionModal(false);
              handleStartFocus();
            }}
            className="w-full p-4 rounded-xl bg-primary-500/20 hover:bg-primary-500/30 border border-primary-500/50 transition-all text-left"
          >
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-primary-500/30 flex items-center justify-center">
                <Timer className="w-6 h-6 text-primary-400" />
              </div>
              <div>
                <p className="font-semibold text-white">{t('startFocusButton')}</p>
                <p className="text-sm text-gray-400">{t('startFocusHint')}</p>
              </div>
            </div>
          </button>

          {/* Complete Task Option */}
          <button
            onClick={() => {
              setShowActionModal(false);
              completeTaskMutation.mutate();
            }}
            disabled={completeTaskMutation.isPending}
            className="w-full p-4 rounded-xl bg-green-500/20 hover:bg-green-500/30 border border-green-500/50 transition-all text-left"
          >
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-green-500/30 flex items-center justify-center">
                <Check className="w-6 h-6 text-green-400" />
              </div>
              <div>
                <p className="font-semibold text-white">{t('completeTask')}</p>
                <p className="text-sm text-gray-400">{t('completeTaskHint')}</p>
              </div>
            </div>
          </button>
        </div>
      </Modal>

      {/* Companion Picker Modal */}
      <Modal
        isOpen={showCompanionPicker}
        onClose={() => setShowCompanionPicker(false)}
        title={t('selectCompanionCard')}
      >
        <div className="space-y-3">
          {companion && (
            <button
              onClick={() => { removeCompanionMutation.mutate(); setShowCompanionPicker(false); }}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-xl bg-gray-800/60 hover:bg-gray-700/60 text-gray-400 text-sm transition-colors"
            >
              <span>🐾</span>
              {t('removeCompanion')}
            </button>
          )}
          <div className="grid grid-cols-3 gap-2 max-h-[50vh] overflow-y-auto">
            {ownedCards.map((card) => (
              <button
                key={card.id}
                onClick={() => setCompanionMutation.mutate(card.id)}
                disabled={setCompanionMutation.isPending}
                className={`relative rounded-xl overflow-hidden transition-all ${
                  companion?.id === card.id
                    ? 'ring-2 ring-pink-500 opacity-60'
                    : 'hover:scale-105'
                }`}
              >
                <div className="aspect-square bg-gray-800">
                  {card.image_url ? (
                    <img src={card.image_url} alt={card.name} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <span className="text-2xl">{card.emoji || '🎴'}</span>
                    </div>
                  )}
                </div>
                <div className="px-1 py-1 bg-gray-900">
                  <p className="text-[10px] text-gray-300 truncate text-center">{card.name}</p>
                </div>
                {card.is_companion && (
                  <div className="absolute top-1 right-1 text-xs">🐾</div>
                )}
              </button>
            ))}
          </div>
        </div>
      </Modal>

      {/* Share Task Modal */}
      <Modal
        isOpen={showShareModal}
        onClose={() => {
          setShowShareModal(false);
          setShareMessage('');
          setSelectedFriendId(null);
        }}
        title={t('shareWithFriend')}
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-500">{t('selectFriend')}</p>
          <div className="max-h-[40vh] overflow-y-auto space-y-2">
            {friendsList.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">{t('noFriendsYet')}</p>
            ) : (
              friendsList.map((friend) => {
                const alreadyShared = taskShares.some(
                  (s) => s.assignee_id === friend.friend_id
                );
                return (
                  <button
                    key={friend.friendship_id}
                    disabled={alreadyShared}
                    onClick={() => setSelectedFriendId(friend.friend_id)}
                    className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all ${
                      alreadyShared
                        ? 'opacity-40 cursor-not-allowed bg-gray-800/30'
                        : selectedFriendId === friend.friend_id
                        ? 'bg-primary-500/20 border border-primary-500/50'
                        : 'bg-gray-800/50 hover:bg-gray-700/50'
                    }`}
                  >
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white text-sm font-bold">
                      {(friend.first_name?.[0] || '?').toUpperCase()}
                    </div>
                    <span className="text-sm text-white">{friend.first_name || friend.username || '?'}</span>
                    {alreadyShared && <span className="ml-auto text-xs text-gray-500">{t('done')}</span>}
                  </button>
                );
              })
            )}
          </div>
          <textarea
            value={shareMessage}
            onChange={(e) => setShareMessage(e.target.value)}
            placeholder={t('optionalMessage')}
            rows={2}
            className="w-full p-3 bg-gray-800 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none text-sm"
          />
          <Button
            onClick={() => {
              if (selectedFriendId) {
                shareTaskMutation.mutate({ friendId: selectedFriendId, message: shareMessage.trim() || undefined });
              }
            }}
            isLoading={shareTaskMutation.isPending}
            disabled={!selectedFriendId}
            className="w-full"
          >
            <Share2 className="w-4 h-4 mr-2" />
            {t('shareTask')}
          </Button>
        </div>
      </Modal>

      {/* Card Earned Modal */}
      <CardEarnedModal
        isOpen={showCardModal}
        card={earnedCard}
        onClose={() => {
          setShowCardModal(false);
          setEarnedCard(null);
          if (levelUpData) {
            setShowLevelUpModal(true);
          } else if (shouldShowCardTutorial()) {
            setShowCardTutorial(true);
          }
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

      {/* Streak Milestone Modal */}
      <StreakMilestoneModal
        isOpen={showStreakMilestoneModal}
        onClose={() => {
          setShowStreakMilestoneModal(false);
          setStreakMilestoneData(null);
        }}
        milestone={streakMilestoneData}
      />

      {/* Card Tutorial */}
      <CardTutorial
        isOpen={showCardTutorial}
        onClose={() => setShowCardTutorial(false)}
      />

    </div>
    </div>
  );
}
