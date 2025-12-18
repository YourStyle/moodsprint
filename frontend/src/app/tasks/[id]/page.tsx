'use client';

import { useState, useEffect, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Wand2, Trash2, Plus, Play, Check, Timer, Infinity, Pencil, Sparkles, Heart, Swords, ChevronUp, ChevronDown, Pause, Square } from 'lucide-react';
import { Button, Card, Modal, Progress } from '@/components/ui';
import { SubtaskItem } from '@/components/tasks';
import { MoodSelector } from '@/components/mood';
import { tasksService, focusService, moodService, cardsService } from '@/services';
import { useAppStore } from '@/lib/store';
import { hapticFeedback, showBackButton, hideBackButton } from '@/lib/telegram';
import { useLanguage, type TranslationKey } from '@/lib/i18n';
import { PRIORITY_COLORS, TASK_TYPE_EMOJIS, TASK_TYPE_LABELS, TASK_TYPE_COLORS, DEFAULT_FOCUS_DURATION } from '@/domain/constants';
import type { MoodLevel, EnergyLevel, TaskType } from '@/domain/types';

// Card type for earned card modal
interface EarnedCard {
  id: number;
  name: string;
  description: string;
  genre: string;
  rarity: string;
  hp: number;
  attack: number;
  emoji: string;
  image_url?: string | null;
}

// Rarity colors and labels
const RARITY_COLORS: Record<string, string> = {
  common: 'from-gray-500 to-gray-600',
  uncommon: 'from-green-500 to-green-600',
  rare: 'from-blue-500 to-blue-600',
  epic: 'from-purple-500 to-purple-600',
  legendary: 'from-yellow-500 to-orange-500',
};

const RARITY_TRANSLATION_KEYS: Record<string, string> = {
  common: 'rarityCommon',
  uncommon: 'rarityUncommon',
  rare: 'rarityRare',
  epic: 'rarityEpic',
  legendary: 'rarityLegendary',
};

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
  onComplete,
  onCancel,
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
  onComplete: () => void;
  onCancel: () => void;
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

  const planned = session.planned_duration_minutes * 60;
  const remaining = planned - elapsed;
  const isOvertime = !isNoTimerMode && remaining < 0;

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
        {isPaused ? (
          <Button
            variant="primary"
            onClick={onResume}
            className="flex-1"
          >
            <Play className="w-4 h-4 mr-1" />
            {t('resume')}
          </Button>
        ) : (
          <Button
            variant="secondary"
            onClick={onPause}
            className="flex-1"
          >
            <Pause className="w-4 h-4 mr-1" />
            {t('pause')}
          </Button>
        )}
        <Button
          variant="primary"
          onClick={onComplete}
          className="flex-1"
        >
          <Check className="w-4 h-4 mr-1" />
          {t('complete')}
        </Button>
        <Button
          variant="danger"
          onClick={onCancel}
          className="px-3"
        >
          <Square className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}

// CardEarnedModal component with async image generation
function CardEarnedModal({
  isOpen,
  card,
  onClose,
  t
}: {
  isOpen: boolean;
  card: EarnedCard | null;
  onClose: () => void;
  t: (key: TranslationKey) => string;
}) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  // Trigger async image generation when modal opens with a card
  useEffect(() => {
    if (isOpen && card && !card.image_url && !isGenerating) {
      setIsGenerating(true);
      setImageUrl(null);

      // Call the async image generation endpoint
      cardsService.generateCardImage(card.id)
        .then((result) => {
          if (result.success && result.data?.image_url) {
            setImageUrl(result.data.image_url);
          }
        })
        .catch((err) => {
          console.error('Failed to generate card image:', err);
        })
        .finally(() => {
          setIsGenerating(false);
        });
    } else if (card?.image_url) {
      setImageUrl(card.image_url);
    }
  }, [isOpen, card]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setImageUrl(null);
      setIsGenerating(false);
    }
  }, [isOpen]);

  if (!card) return null;

  const displayImageUrl = imageUrl || card.image_url;

  const rarityKey = (RARITY_TRANSLATION_KEYS[card.rarity] || 'rarityCommon') as TranslationKey;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={t('newCardTitle')}>
      <div className="flex flex-col items-center">
        {/* Card Preview */}
        <div className={`w-48 h-64 rounded-2xl bg-gradient-to-br ${RARITY_COLORS[card.rarity] || RARITY_COLORS.common} p-1 mb-4`}>
          <div className="w-full h-full bg-gray-900 rounded-xl flex flex-col overflow-hidden">
            {/* Card Image or Emoji */}
            <div className="flex-1 flex items-center justify-center bg-gray-800 relative">
              {displayImageUrl ? (
                <img
                  src={displayImageUrl}
                  alt={card.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <span className="text-5xl">{card.emoji}</span>
                  {isGenerating && (
                    <div className="absolute bottom-2 left-0 right-0 text-center">
                      <span className="text-xs text-gray-400 animate-pulse">
                        {t('cardImageGenerating')}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Card Info */}
            <div className="p-2 space-y-1">
              <p className="text-white font-bold text-sm truncate">{card.name}</p>
              <p className="text-gray-400 text-xs truncate">{card.description}</p>

              {/* Stats */}
              <div className="flex justify-between text-xs pt-1">
                <span className="text-red-400 flex items-center gap-1">
                  <Heart className="w-3 h-3" /> {card.hp}
                </span>
                <span className="text-orange-400 flex items-center gap-1">
                  <Swords className="w-3 h-3" /> {card.attack}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Rarity Badge */}
        <div className={`px-4 py-1 rounded-full bg-gradient-to-r ${RARITY_COLORS[card.rarity] || RARITY_COLORS.common} mb-4`}>
          <span className="text-white font-bold text-sm flex items-center gap-1">
            <Sparkles className="w-4 h-4" />
            {t(rarityKey)}
          </span>
        </div>

        <p className="text-gray-400 text-sm text-center mb-4">
          {t('cardAddedToCollection')}
        </p>

        <Button onClick={onClose} className="w-full">
          {t('great')}
        </Button>
      </div>
    </Modal>
  );
}

export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const taskId = Number(params.id);
  const { t } = useLanguage();

  const {
    latestMood,
    setLatestMood,
    setActiveSession,
    showXPAnimation,
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
  const [selectedDuration, setSelectedDuration] = useState<number | null>(DEFAULT_FOCUS_DURATION);
  const [newSubtaskTitle, setNewSubtaskTitle] = useState('');
  const [moodLoading, setMoodLoading] = useState(false);
  const [showEditTask, setShowEditTask] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [showEditSubtask, setShowEditSubtask] = useState(false);
  const [editingSubtask, setEditingSubtask] = useState<{ id: number; title: string; estimated_minutes: number } | null>(null);
  const [earnedCard, setEarnedCard] = useState<EarnedCard | null>(null);
  const [showCardModal, setShowCardModal] = useState(false);
  const [showPriorityModal, setShowPriorityModal] = useState(false);
  const [showActionModal, setShowActionModal] = useState(false);

  // Show Telegram back button
  useEffect(() => {
    const handleBack = () => {
      router.push('/tasks');
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

  const decomposeMutation = useMutation({
    mutationFn: (moodId?: number) => tasksService.decomposeTask(taskId, moodId),
    onSuccess: () => {
      refetch();
      hapticFeedback('success');
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
        showXPAnimation(result.data.xp_earned);
      }
      // Show card earned modal if card was generated
      if (result.data?.card_earned) {
        setEarnedCard(result.data.card_earned);
        setShowCardModal(true);
      }
      hapticFeedback('success');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => tasksService.deleteTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      router.push('/tasks');
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
    mutationFn: () => focusService.pauseSession(),
    onSuccess: (result) => {
      if (result.success && result.data?.session) {
        updateActiveSession(result.data.session);
        hapticFeedback('light');
      }
    },
  });

  const resumeSessionMutation = useMutation({
    mutationFn: () => focusService.resumeSession(),
    onSuccess: (result) => {
      if (result.success && result.data?.session) {
        updateActiveSession(result.data.session);
        hapticFeedback('light');
      }
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
          showXPAnimation(result.data.xp_earned);
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
    setSelectedDuration(DEFAULT_FOCUS_DURATION);
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
    mutationFn: () =>
      tasksService.updateTask(taskId, { status: 'completed' }),
    onSuccess: (result) => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['user', 'stats'] });
      queryClient.invalidateQueries({ queryKey: ['daily', 'goals'] });
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      if (result.data?.xp_earned) {
        showXPAnimation(result.data.xp_earned);
      }
      // Show card earned modal if card was generated
      if (result.data?.card_earned) {
        setEarnedCard(result.data.card_earned);
        setShowCardModal(true);
      }
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
    mutationFn: (data: { title?: string; description?: string }) =>
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
          showXPAnimation(result.data.xp_earned);
        }
      }
    } finally {
      setMoodLoading(false);
    }
  };

  const task = data?.data?.task;

  if (isLoading) {
    return (
      <div className="p-4">
        <Card className="h-32 animate-pulse" />
      </div>
    );
  }

  if (!task) {
    return (
      <div className="p-4 text-center">
        <p className="text-gray-500">{t('taskNotFound')}</p>
        <Button onClick={() => router.push('/tasks')} className="mt-4">
          {t('backToTasks')}
        </Button>
      </div>
    );
  }

  const subtasks = task.subtasks || [];

  return (
    <div className="p-4 space-y-4 pt-safe">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex-1 min-w-0">
          <h1 className="text-lg font-bold text-white truncate">{task.title}</h1>
        </div>
        <button
          onClick={() => {
            setEditTitle(task.title);
            setEditDescription(task.description || '');
            setShowEditTask(true);
          }}
          className="p-2 hover:bg-gray-700 rounded-full text-gray-400 hover:text-white"
        >
          <Pencil className="w-5 h-5" />
        </button>
        <button
          onClick={() => setShowDeleteConfirm(true)}
          className="p-2 hover:bg-red-500/20 rounded-full text-gray-400 hover:text-red-500"
        >
          <Trash2 className="w-5 h-5" />
        </button>
      </div>

      {/* Task Info */}
      <Card>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            {task.task_type && (
              <button
                onClick={() => setShowTypeModal(true)}
                className={`text-xs px-2 py-0.5 rounded-full transition-opacity hover:opacity-80 ${TASK_TYPE_COLORS[task.task_type]}`}
              >
                {TASK_TYPE_EMOJIS[task.task_type]} {TASK_TYPE_LABELS[task.task_type]}
              </button>
            )}
            {!task.task_type && (
              <button
                onClick={() => setShowTypeModal(true)}
                className="text-xs px-2 py-0.5 rounded-full bg-gray-600/50 text-gray-400 border border-dashed border-gray-500 hover:bg-gray-600"
              >
                {t('addType')}
              </button>
            )}
            <button
              onClick={() => setShowPriorityModal(true)}
              className={`text-xs px-2 py-0.5 rounded-full transition-opacity hover:opacity-80 ${PRIORITY_COLORS[task.priority]}`}
            >
              {task.priority === 'low' ? t('priorityLow') : task.priority === 'medium' ? t('priorityMedium') : t('priorityHigh')}
            </button>
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              task.status === 'completed'
                ? 'bg-green-500/20 text-green-400'
                : task.status === 'in_progress'
                ? 'bg-blue-500/20 text-blue-400'
                : 'bg-gray-500/20 text-gray-400'
            }`}>
              {task.status === 'completed' ? t('statusCompleted') : task.status === 'in_progress' ? t('statusInProgress') : t('statusPending')}
            </span>
          </div>
          <span className="text-sm text-gray-500">
            {task.progress_percent}{t('percentComplete')}
          </span>
        </div>
        <Progress value={task.progress_percent} color="primary" />
      </Card>

      {/* Action Button or Active Session Timer */}
      {task.status !== 'completed' && (
        activeSession ? (
          <FocusTimer
            session={activeSession}
            onPause={() => pauseSessionMutation.mutate()}
            onResume={() => resumeSessionMutation.mutate()}
            onComplete={() => completeSessionMutation.mutate(activeSession.id)}
            onCancel={() => cancelSessionMutation.mutate(activeSession.id)}
            t={t}
          />
        ) : (
          <Button
            variant="primary"
            onClick={() => setShowActionModal(true)}
            className="w-full h-14"
          >
            <Play className="w-5 h-5 mr-2" />
            {t('start')}
          </Button>
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

      {/* Subtasks */}
      {subtasks.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-white">{t('steps')}</h2>
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
                className="text-sm text-gray-400 hover:text-gray-300 flex items-center gap-1"
              >
                <Wand2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="space-y-2">
            {subtasks.map((subtask) => (
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
      {subtasks.length === 0 && (
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
              rows={4}
              className="w-full p-3 bg-gray-800 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
            />
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
              onClick={() => updateTaskMutation.mutate({
                title: editTitle.trim(),
                description: editDescription.trim() || undefined,
              })}
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
                onClick={() => setSelectedDuration(d)}
                className={`p-3 rounded-xl text-center transition-all ${
                  selectedDuration === d
                    ? 'bg-primary-500 text-white ring-2 ring-primary-500 ring-offset-2 ring-offset-gray-900'
                    : 'bg-gray-800 hover:bg-gray-700 text-gray-300'
                }`}
              >
                <Timer className="w-5 h-5 mx-auto mb-1" />
                <span className="text-sm font-medium">{d} {t('min')}</span>
              </button>
            ))}
          </div>

          <button
            onClick={() => setSelectedDuration(null)}
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

      {/* Card Earned Modal */}
      <CardEarnedModal
        isOpen={showCardModal}
        card={earnedCard}
        onClose={() => {
          setShowCardModal(false);
          setEarnedCard(null);
        }}
        t={t}
      />
    </div>
  );
}
