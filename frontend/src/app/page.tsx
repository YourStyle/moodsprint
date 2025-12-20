'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { Plus, Sparkles, Play, Pause, Square, ArrowUp, X, Smile, Timer, CheckCircle2, Filter } from 'lucide-react';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { Button, Card, Modal } from '@/components/ui';
import { MoodSelector } from '@/components/mood';
import { TaskForm } from '@/components/tasks';
import { DailyBonus } from '@/components/gamification';
import { CardEarnedModal, type EarnedCard } from '@/components/cards';
import { useAppStore } from '@/lib/store';
import { tasksService, moodService, focusService } from '@/services';
import { hapticFeedback } from '@/lib/telegram';
import { MOOD_EMOJIS } from '@/domain/constants';
import { useLanguage, TranslationKey } from '@/lib/i18n';
import type { MoodLevel, EnergyLevel, FocusSession, TaskStatus } from '@/domain/types';

type FilterStatus = TaskStatus | 'all';

const formatDateForAPI = (date: Date): string => {
  return date.toISOString().split('T')[0];
};

const formatDateDisplay = (date: Date, language: 'ru' | 'en', t: (key: TranslationKey) => string): string => {
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  if (formatDateForAPI(date) === formatDateForAPI(today)) return t('today');
  if (formatDateForAPI(date) === formatDateForAPI(tomorrow)) return t('tomorrow');
  if (formatDateForAPI(date) === formatDateForAPI(yesterday)) return t('yesterday');

  const locale = language === 'ru' ? 'ru-RU' : 'en-US';
  return date.toLocaleDateString(locale, { weekday: 'long', day: 'numeric', month: 'long' });
};

interface WeekCalendarProps {
  selectedDate: Date;
  onDateSelect: (date: Date) => void;
  language: 'ru' | 'en';
  taskCounts?: Record<string, number>;
}

const WEEK_DAYS = {
  ru: ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'],
  en: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
};

function WeekCalendar({ selectedDate, onDateSelect, language, taskCounts = {} }: WeekCalendarProps) {
  const days = WEEK_DAYS[language];
  const today = new Date();
  const currentDay = today.getDay();
  const selectedDateStr = formatDateForAPI(selectedDate);

  return (
    <div className="flex justify-between gap-1">
      {days.map((day, index) => {
        const date = new Date(today);
        date.setDate(today.getDate() - currentDay + index);
        const dateStr = formatDateForAPI(date);
        const isSelected = dateStr === selectedDateStr;
        const isToday = dateStr === formatDateForAPI(today);
        const taskCount = taskCounts[dateStr] || 0;

        return (
          <button
            key={day}
            onClick={() => onDateSelect(date)}
            className={`relative flex flex-col items-center py-2 px-3 rounded-xl transition-all ${
              isSelected
                ? 'bg-primary-500/20 border border-primary-500/50'
                : isToday
                ? 'bg-dark-600 border border-gray-700'
                : 'opacity-60 hover:opacity-100'
            }`}
          >
            <span className="text-xs text-gray-400 mb-1">{day}</span>
            <span className={`text-lg font-semibold ${isSelected ? 'text-primary-400' : isToday ? 'text-white' : 'text-gray-400'}`}>
              {date.getDate()}
            </span>
            {taskCount > 0 && !isSelected && (
              <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 bg-purple-500 rounded-full text-[10px] font-bold text-white flex items-center justify-center">
                {taskCount > 9 ? '9+' : taskCount}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

// Helper to calculate elapsed seconds
function calculateElapsedSeconds(session: FocusSession): number {
  const startedAt = new Date(session.started_at).getTime();
  const now = Date.now();
  return Math.floor((now - startedAt) / 1000);
}

// Mini timer component for compact cards
function MiniTimer({ session, onPause, onResume, onComplete, onStop }: {
  session: FocusSession;
  onPause: () => void;
  onResume: () => void;
  onComplete: () => void;
  onStop: () => void;
}) {
  const initialElapsed = useMemo(() => {
    if (session.status === 'paused') {
      return session.elapsed_minutes * 60;
    }
    return calculateElapsedSeconds(session);
  }, [session.started_at, session.status, session.elapsed_minutes]);

  const [elapsed, setElapsed] = useState(initialElapsed);
  const isPaused = session.status === 'paused';
  const planned = session.planned_duration_minutes * 60;

  useEffect(() => {
    setElapsed(initialElapsed);
  }, [initialElapsed]);

  useEffect(() => {
    if (isPaused) return;
    const interval = setInterval(() => {
      setElapsed(calculateElapsedSeconds(session));
    }, 1000);
    return () => clearInterval(interval);
  }, [isPaused, session.started_at]);

  const formatTime = useCallback((seconds: number) => {
    const mins = Math.floor(Math.abs(seconds) / 60);
    const secs = Math.abs(seconds) % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }, []);

  const isNoTimerMode = session.planned_duration_minutes >= 480;
  const remaining = planned - elapsed;
  const isOvertime = !isNoTimerMode && remaining < 0;

  return (
    <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
      <div className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-mono ${
        isOvertime ? 'bg-red-500/20 text-red-400' : isPaused ? 'bg-yellow-500/20 text-yellow-400' : 'bg-primary-500/20 text-primary-400'
      }`}>
        <Timer className="w-3 h-3" />
        <span className="tabular-nums">
          {isOvertime && '+'}
          {isNoTimerMode ? formatTime(elapsed) : formatTime(isOvertime ? -remaining : remaining)}
        </span>
      </div>
      <button
        onClick={isPaused ? onResume : onPause}
        className={`w-6 h-6 rounded flex items-center justify-center ${
          isPaused ? 'bg-primary-500/20 text-primary-400' : 'bg-yellow-500/20 text-yellow-400'
        }`}
      >
        {isPaused ? <Play className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
      </button>
      <button
        onClick={onComplete}
        className="w-6 h-6 rounded bg-green-500/20 text-green-400 flex items-center justify-center"
      >
        <CheckCircle2 className="w-3 h-3" />
      </button>
      <button
        onClick={onStop}
        className="w-6 h-6 rounded bg-gray-500/20 text-gray-400 flex items-center justify-center"
      >
        <Square className="w-3 h-3" />
      </button>
    </div>
  );
}

function TaskCardCompact({
  task,
  onClick,
  onStart,
  activeSession,
  onPause,
  onResume,
  onComplete,
  onStop,
}: {
  task: { id: number; title: string; progress_percent: number; estimated_minutes?: number; status: string; subtasks_count: number };
  onClick: () => void;
  onStart?: () => void;
  activeSession?: FocusSession;
  onPause?: () => void;
  onResume?: () => void;
  onComplete?: () => void;
  onStop?: () => void;
}) {
  const isCompleted = task.status === 'completed';
  const hasSubtasks = task.subtasks_count > 0;
  const hasActiveSession = !!activeSession;

  return (
    <div
      className={`bg-dark-700/50 rounded-xl p-3 border ${hasActiveSession ? 'border-primary-500/50' : 'border-gray-800'} ${isCompleted ? 'opacity-50' : ''}`}
    >
      <div className="flex items-center gap-3" onClick={onClick}>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
          isCompleted ? 'bg-green-500/20' : hasActiveSession ? 'bg-primary-500/30' : 'bg-purple-500/20'
        }`}>
          {isCompleted ? (
            <span className="text-sm text-green-400">✓</span>
          ) : hasActiveSession ? (
            <div className="w-3 h-3 rounded-full bg-primary-500 animate-pulse" />
          ) : (
            <Sparkles className="w-4 h-4 text-purple-400" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className={`text-sm font-medium ${isCompleted ? 'text-gray-500 line-through' : 'text-white'}`}>
            {task.title}
          </h3>
          {!isCompleted && hasSubtasks && !hasActiveSession && (
            <div className="mt-1 h-1 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-500 rounded-full transition-all"
                style={{ width: `${task.progress_percent}%` }}
              />
            </div>
          )}
        </div>
        {hasActiveSession && activeSession && onPause && onResume && onComplete && onStop ? (
          <MiniTimer
            session={activeSession}
            onPause={onPause}
            onResume={onResume}
            onComplete={onComplete}
            onStop={onStop}
          />
        ) : !isCompleted && onStart && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onStart();
            }}
            className="w-8 h-8 rounded-lg bg-primary-500 hover:bg-primary-600 flex items-center justify-center transition-colors flex-shrink-0"
          >
            <Play className="w-4 h-4 text-white" fill="white" />
          </button>
        )}
      </div>
    </div>
  );
}

export default function HomePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { t, language, setLanguage } = useLanguage();
  const { user, isLoading, latestMood, setLatestMood, showMoodModal, setShowMoodModal, showXPAnimation, setActiveSession, activeSessions, removeActiveSession, updateActiveSession } = useAppStore();
  const [moodLoading, setMoodLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [postponeNotificationDismissed, setPostponeNotificationDismissed] = useState(false);
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('pending');
  const [earnedCard, setEarnedCard] = useState<EarnedCard | null>(null);
  const [showCardModal, setShowCardModal] = useState(false);

  const selectedDateStr = formatDateForAPI(selectedDate);

  // Calculate week date range for task counts
  const weekDates = useMemo(() => {
    const today = new Date();
    const currentDay = today.getDay();
    const dates: string[] = [];
    for (let i = 0; i < 7; i++) {
      const date = new Date(today);
      date.setDate(today.getDate() - currentDay + i);
      dates.push(formatDateForAPI(date));
    }
    return dates;
  }, []);

  // Check if we should show mood modal on first entry
  useEffect(() => {
    if (user && !latestMood) {
      // Check if mood was checked today
      moodService.getLatestMood().then((result) => {
        if (result.success && result.data?.mood_check) {
          setLatestMood(result.data.mood_check);
        } else {
          // No mood today, show modal
          setShowMoodModal(true);
        }
      });
    }
  }, [user, latestMood, setLatestMood, setShowMoodModal]);

  // Query tasks for selected date with status filter
  const { data: tasksData, isLoading: tasksLoading, isFetching } = useQuery({
    queryKey: ['tasks', 'by_date', selectedDateStr, filterStatus],
    queryFn: () => tasksService.getTasks({
      due_date: selectedDateStr,
      ...(filterStatus !== 'all' && { status: filterStatus }),
      limit: 100,
    }),
    enabled: !!user,
    placeholderData: keepPreviousData,
  });

  // Query all tasks for week to show counts on calendar
  const { data: weekTasksData } = useQuery({
    queryKey: ['tasks', 'week', weekDates[0], weekDates[6]],
    queryFn: () => tasksService.getTasks({ limit: 200 }),
    enabled: !!user,
    staleTime: 1000 * 60 * 2, // 2 minutes
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
    mutationFn: (input: { title: string; description: string; due_date: string; scheduled_at?: string }) =>
      tasksService.createTask(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setShowCreateModal(false);
      hapticFeedback('success');
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
        hapticFeedback('success');
      }
    },
  });

  const pauseSessionMutation = useMutation({
    mutationFn: (sessionId: number) => focusService.pauseSession(),
    onSuccess: (result) => {
      if (result.success && result.data?.session) {
        updateActiveSession(result.data.session);
      }
    },
  });

  const resumeSessionMutation = useMutation({
    mutationFn: (sessionId: number) => focusService.resumeSession(),
    onSuccess: (result) => {
      if (result.success && result.data?.session) {
        updateActiveSession(result.data.session);
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
      if (result.data?.xp_earned) showXPAnimation(result.data.xp_earned);
      // Show card earned modal if card was generated
      if (result.data?.card_earned) {
        setEarnedCard(result.data.card_earned as EarnedCard);
        setShowCardModal(true);
      }
      hapticFeedback('success');
    },
  });

  const cancelSessionMutation = useMutation({
    mutationFn: (sessionId: number) => focusService.cancelSession(sessionId),
    onSuccess: (result, sessionId) => {
      removeActiveSession(sessionId);
      queryClient.invalidateQueries({ queryKey: ['focus'] });
      hapticFeedback('light');
    },
  });

  // Helper to get session for a task
  const getSessionForTask = (taskId: number) => {
    return activeSessions.find(s => s.task_id === taskId);
  };

  const handleCreateTask = (title: string, description: string, dueDate: string, scheduledAt?: string) => {
    createMutation.mutate({ title, description, due_date: dueDate, scheduled_at: scheduledAt });
  };

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
          showXPAnimation(result.data.xp_earned);
        }
      }
    } catch (error) {
      console.error('Failed to log mood:', error);
    } finally {
      setMoodLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!user) {
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
          Это твой личный помощник, который знает, как распределить дела для максимальной эффективности.
        </p>
        <Button variant="gradient" size="lg" className="w-full max-w-xs">
          <Sparkles className="w-5 h-5" />
          Открыть в Telegram
        </Button>
        <p className="text-xs text-gray-500 mt-4">
          Пожалуйста, откройте приложение через Telegram для продолжения.
        </p>
      </div>
    );
  }

  const tasks = tasksData?.data?.tasks || [];
  const postponeStatus = postponeData?.data;
  const showPostponeNotification = postponeStatus?.has_postponed && !postponeNotificationDismissed;

  // Get greeting based on time
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return t('goodMorning');
    if (hour < 17) return t('goodAfternoon');
    return t('goodEvening');
  };

  // Toggle language
  const toggleLanguage = () => {
    const newLang = language === 'ru' ? 'en' : 'ru';
    setLanguage(newLang);
    hapticFeedback('light');
  };

  return (
    <div className="min-h-screen p-4 space-y-6 safe-area-top safe-area-bottom">
      {/* Daily Bonus Modal */}
      <DailyBonus />

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
                Приоритет повышен: {postponeStatus.priority_changes.map(c => c.task_title).join(', ')}
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

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            {getGreeting()},
          </h1>
          <p className="text-gray-400">{user.first_name || t('friend')}</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Language Toggle */}
          <button
            onClick={toggleLanguage}
            className="w-10 h-10 rounded-full bg-dark-700 border border-gray-700 flex items-center justify-center hover:bg-dark-600 transition-colors text-sm font-medium"
          >
            {language === 'ru' ? '🇷🇺' : '🇬🇧'}
          </button>
          {/* Mood Button */}
          <button
            onClick={() => setShowMoodModal(true)}
            className="w-10 h-10 rounded-full bg-dark-700 border border-gray-700 flex items-center justify-center hover:bg-dark-600 transition-colors"
          >
            {latestMood ? (
              <span className="text-lg">
                {MOOD_EMOJIS[latestMood.mood as keyof typeof MOOD_EMOJIS]}
              </span>
            ) : (
              <Smile className="w-5 h-5 text-gray-400" />
            )}
          </button>
          {/* Avatar */}
          {user.photo_url ? (
            <img
              src={user.photo_url}
              alt={user.first_name || 'User'}
              className="w-12 h-12 rounded-full object-cover border-2 border-purple-500/50"
            />
          ) : (
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white font-bold">
              {(user.first_name?.[0] || '?').toUpperCase()}
            </div>
          )}
        </div>
      </div>

      {/* Week Calendar */}
      <WeekCalendar
        selectedDate={selectedDate}
        onDateSelect={setSelectedDate}
        language={language}
        taskCounts={taskCounts}
      />

      {/* Tasks Section */}
      <div className="space-y-3 min-h-[180px]">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-white capitalize">{formatDateDisplay(selectedDate, language, t)}</h2>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowCreateModal(true)}
          >
            <Plus className="w-4 h-4 mr-1" />
            {t('add')}
          </Button>
        </div>

        {/* Status Filters */}
        <div className="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4">
          {([
            { value: 'pending' as const, labelKey: 'statusPending' as const },
            { value: 'in_progress' as const, labelKey: 'statusInProgress' as const },
            { value: 'completed' as const, labelKey: 'statusCompleted' as const },
            { value: 'all' as const, labelKey: 'all' as const },
          ]).map((filter) => (
            <button
              key={filter.value}
              onClick={() => setFilterStatus(filter.value)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                filterStatus === filter.value
                  ? 'bg-primary-500 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {t(filter.labelKey)}
            </button>
          ))}
        </div>

        {tasksLoading && !tasksData ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Card key={i} variant="glass" className="h-14 animate-pulse" />
            ))}
          </div>
        ) : tasks.length > 0 ? (
          <div className="space-y-2">
            {tasks.map((task) => {
              const session = getSessionForTask(task.id);
              return (
                <TaskCardCompact
                  key={task.id}
                  task={task}
                  onClick={() => router.push(`/tasks/${task.id}`)}
                  onStart={task.status !== 'completed' && !session ? () => startFocusMutation.mutate(task.id) : undefined}
                  activeSession={session}
                  onPause={session ? () => pauseSessionMutation.mutate(session.id) : undefined}
                  onResume={session ? () => resumeSessionMutation.mutate(session.id) : undefined}
                  onComplete={session ? () => completeSessionMutation.mutate(session.id) : undefined}
                  onStop={session ? () => cancelSessionMutation.mutate(session.id) : undefined}
                />
              );
            })}
          </div>
        ) : (
          <Card variant="glass" className="text-center py-8">
            <Sparkles className="w-12 h-12 text-purple-400 mx-auto mb-3" />
            <p className="text-gray-400 mb-4">
              {filterStatus === 'all'
                ? `${t('noTasksForDate')} ${formatDateDisplay(selectedDate, language, t).toLowerCase()}`
                : t('noTasksInCategory')}
            </p>
            <Button variant="gradient" onClick={() => setShowCreateModal(true)}>
              <Plus className="w-4 h-4" />
              {t('createTask')}
            </Button>
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
        }}
        t={t}
      />
    </div>
  );
}
