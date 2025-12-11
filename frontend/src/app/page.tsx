'use client';

import { useState, useEffect } from 'react';
import { Plus, Sparkles, Menu, HelpCircle, Clock, Play, ChevronLeft, ChevronRight, ArrowUp, X, Zap, Timer, Smile } from 'lucide-react';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { Button, Card, Modal } from '@/components/ui';
import { MoodSelector } from '@/components/mood';
import { TaskForm } from '@/components/tasks';
import { TaskCard } from '@/components/tasks';
import { XPBar, StreakBadge, DailyGoals, DailyBonus } from '@/components/gamification';
import { useAppStore } from '@/lib/store';
import { tasksService, moodService, gamificationService, focusService } from '@/services';
import { hapticFeedback } from '@/lib/telegram';
import { MOOD_EMOJIS } from '@/domain/constants';
import type { MoodLevel, EnergyLevel, TaskPriority, TaskSuggestion, PreferredTime } from '@/domain/types';

const formatDateForAPI = (date: Date): string => {
  return date.toISOString().split('T')[0];
};

const formatDateDisplay = (date: Date): string => {
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  if (formatDateForAPI(date) === formatDateForAPI(today)) return 'Сегодня';
  if (formatDateForAPI(date) === formatDateForAPI(tomorrow)) return 'Завтра';
  if (formatDateForAPI(date) === formatDateForAPI(yesterday)) return 'Вчера';

  return date.toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' });
};

interface WeekCalendarProps {
  selectedDate: Date;
  onDateSelect: (date: Date) => void;
}

function WeekCalendar({ selectedDate, onDateSelect }: WeekCalendarProps) {
  const days = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];
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

        return (
          <button
            key={day}
            onClick={() => onDateSelect(date)}
            className={`flex flex-col items-center py-2 px-3 rounded-xl transition-all ${
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
          </button>
        );
      })}
    </div>
  );
}

function TaskCardCompact({
  task,
  onClick,
  onStart,
}: {
  task: { id: number; title: string; progress_percent: number; estimated_minutes?: number; status: string; subtasks_count: number };
  onClick: () => void;
  onStart?: () => void;
}) {
  const isCompleted = task.status === 'completed';
  const hasSubtasks = task.subtasks_count > 0;

  return (
    <div
      className={`bg-dark-700/50 rounded-xl p-3 border border-gray-800 ${isCompleted ? 'opacity-50' : ''}`}
    >
      <div className="flex items-center gap-3" onClick={onClick}>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
          isCompleted ? 'bg-green-500/20' : 'bg-purple-500/20'
        }`}>
          {isCompleted ? (
            <span className="text-sm text-green-400">✓</span>
          ) : (
            <Sparkles className="w-4 h-4 text-purple-400" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className={`text-sm font-medium truncate ${isCompleted ? 'text-gray-500 line-through' : 'text-white'}`}>
            {task.title}
          </h3>
          {!isCompleted && hasSubtasks && (
            <div className="mt-1 h-1 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-500 rounded-full transition-all"
                style={{ width: `${task.progress_percent}%` }}
              />
            </div>
          )}
        </div>
        {!isCompleted && onStart && (
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

const TIME_OPTIONS = [15, 30, 45, 60, 90, 120];

function FreeTimeModal({
  isOpen,
  onClose,
  onSelectSuggestion,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSelectSuggestion: (suggestion: TaskSuggestion) => void;
}) {
  const [selectedTime, setSelectedTime] = useState<number | null>(null);
  const [suggestions, setSuggestions] = useState<TaskSuggestion[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchSuggestions = async (minutes: number) => {
    setLoading(true);
    setSelectedTime(minutes);
    try {
      const result = await tasksService.getSuggestions(minutes);
      if (result.success && result.data) {
        setSuggestions(result.data.suggestions);
      }
    } catch (error) {
      console.error('Failed to fetch suggestions:', error);
    } finally {
      setLoading(false);
    }
  };

  const getFitBadge = (quality: string) => {
    switch (quality) {
      case 'perfect':
        return <span className="text-xs px-2 py-0.5 bg-green-500/20 text-green-400 rounded-full">идеально</span>;
      case 'good':
        return <span className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded-full">хорошо</span>;
      case 'partial':
        return <span className="text-xs px-2 py-0.5 bg-yellow-500/20 text-yellow-400 rounded-full">частично</span>;
      default:
        return null;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'text-red-400';
      case 'medium': return 'text-yellow-400';
      default: return 'text-gray-400';
    }
  };

  if (!isOpen) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Есть свободное время?">
      <div className="space-y-4">
        {/* Time selection */}
        <div>
          <p className="text-sm text-gray-400 mb-3">Сколько у тебя есть времени?</p>
          <div className="grid grid-cols-3 gap-2">
            {TIME_OPTIONS.map((minutes) => (
              <button
                key={minutes}
                onClick={() => fetchSuggestions(minutes)}
                className={`py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                  selectedTime === minutes
                    ? 'bg-primary-500 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                {minutes < 60 ? `${minutes} мин` : `${minutes / 60} ч`}
              </button>
            ))}
          </div>
        </div>

        {/* Suggestions */}
        {selectedTime && (
          <div>
            <p className="text-sm text-gray-400 mb-3">
              {loading ? 'Подбираю задачи...' : suggestions.length > 0 ? 'Рекомендую:' : 'Нет подходящих задач'}
            </p>
            {loading ? (
              <div className="space-y-2">
                {[1, 2].map((i) => (
                  <div key={i} className="h-16 bg-gray-700 rounded-xl animate-pulse" />
                ))}
              </div>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {suggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSelectSuggestion(suggestion)}
                    className="w-full text-left p-3 bg-gray-700/50 hover:bg-gray-700 rounded-xl transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-xs ${getPriorityColor(suggestion.priority)}`}>●</span>
                          <span className="text-white font-medium truncate">{suggestion.task_title}</span>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-gray-400">
                          <Timer className="w-3 h-3" />
                          <span>{suggestion.estimated_minutes} мин</span>
                          {suggestion.type === 'task' && suggestion.subtasks_count ? (
                            <span>• {suggestion.subtasks_count} шагов</span>
                          ) : suggestion.type === 'subtasks' && suggestion.subtasks ? (
                            <span>• {suggestion.subtasks.length} шагов</span>
                          ) : null}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {getFitBadge(suggestion.fit_quality)}
                        <Play className="w-4 h-4 text-primary-400" />
                      </div>
                    </div>
                    {suggestion.type === 'subtasks' && suggestion.subtasks && (
                      <div className="mt-2 text-xs text-gray-500">
                        {suggestion.subtasks.slice(0, 3).map(s => s.title).join(' → ')}
                        {suggestion.subtasks.length > 3 && '...'}
                      </div>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}

export default function HomePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, isLoading, latestMood, setLatestMood, showMoodModal, setShowMoodModal, showXPAnimation, setActiveSession } = useAppStore();
  const [moodLoading, setMoodLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showFreeTimeModal, setShowFreeTimeModal] = useState(false);
  const [postponeNotificationDismissed, setPostponeNotificationDismissed] = useState(false);

  const selectedDateStr = formatDateForAPI(selectedDate);

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

  const { data: tasksData, isLoading: tasksLoading, isFetching } = useQuery({
    queryKey: ['tasks', 'by_date', selectedDateStr],
    queryFn: () => tasksService.getTasks({ due_date: selectedDateStr, limit: 50 }),
    enabled: !!user,
    placeholderData: keepPreviousData,
  });

  const createMutation = useMutation({
    mutationFn: (input: { title: string; description: string; priority: TaskPriority; due_date: string; preferred_time?: PreferredTime; scheduled_at?: string }) =>
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
        router.push('/focus');
        hapticFeedback('success');
      }
    },
  });

  const handleCreateTask = (title: string, description: string, priority: TaskPriority, dueDate: string, preferredTime?: PreferredTime, scheduledAt?: string) => {
    createMutation.mutate({ title, description, priority, due_date: dueDate, preferred_time: preferredTime, scheduled_at: scheduledAt });
  };

  const handleSelectSuggestion = (suggestion: TaskSuggestion) => {
    setShowFreeTimeModal(false);
    hapticFeedback('success');
    // Start focus session with the suggested duration
    focusService.startSession({
      task_id: suggestion.task_id,
      planned_duration_minutes: suggestion.estimated_minutes,
    }).then((result) => {
      if (result.success && result.data) {
        setActiveSession(result.data.session);
        router.push('/focus');
      }
    });
  };

  const { data: statsData } = useQuery({
    queryKey: ['user', 'stats'],
    queryFn: () => gamificationService.getUserStats(),
    enabled: !!user,
  });

  const { data: goalsData } = useQuery({
    queryKey: ['daily', 'goals'],
    queryFn: () => gamificationService.getDailyGoals(),
    enabled: !!user,
  });

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

  const stats = statsData?.data;
  const goals = goalsData?.data;
  const tasks = tasksData?.data?.tasks || [];
  const postponeStatus = postponeData?.data;
  const showPostponeNotification = postponeStatus?.has_postponed && !postponeNotificationDismissed;
  const incompleteTasks = tasks.filter(t => t.status !== 'completed');
  const completedTasks = tasks.filter(t => t.status === 'completed');

  // Limit displayed tasks to 10
  const MAX_DISPLAYED_TASKS = 10;
  const allTasksSorted = [...incompleteTasks, ...completedTasks];
  const displayedTasks = allTasksSorted.slice(0, MAX_DISPLAYED_TASKS);
  const hasMoreTasks = allTasksSorted.length > MAX_DISPLAYED_TASKS;

  // Get greeting based on time
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Доброе утро';
    if (hour < 17) return 'Добрый день';
    return 'Добрый вечер';
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
          <p className="text-gray-400">{user.first_name || 'друг'}</p>
        </div>
        <div className="flex items-center gap-3">
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
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white font-bold">
            {(user.first_name?.[0] || '?').toUpperCase()}
          </div>
        </div>
      </div>

      {/* Week Calendar */}
      <WeekCalendar selectedDate={selectedDate} onDateSelect={setSelectedDate} />

      {/* Tasks Section - Moved to top */}
      <div className="space-y-3 min-h-[180px]">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-white capitalize">{formatDateDisplay(selectedDate)}</h2>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowFreeTimeModal(true)}
              className="text-accent-400"
            >
              <Zap className="w-4 h-4 mr-1" />
              Есть время?
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setShowCreateModal(true)}
            >
              <Plus className="w-4 h-4 mr-1" />
              Добавить
            </Button>
          </div>
        </div>

        {tasksLoading && !tasksData ? (
          <div className="space-y-2">
            {[1, 2].map((i) => (
              <Card key={i} variant="glass" className="h-14 animate-pulse" />
            ))}
          </div>
        ) : tasks.length > 0 ? (
          <div className="space-y-2">
            {displayedTasks.map((task) => (
              <TaskCardCompact
                key={task.id}
                task={task}
                onClick={() => router.push(`/tasks/${task.id}`)}
                onStart={task.status !== 'completed' ? () => startFocusMutation.mutate(task.id) : undefined}
              />
            ))}
            {hasMoreTasks && (
              <button
                onClick={() => router.push('/tasks')}
                className="w-full py-2 text-sm text-purple-400 hover:text-purple-300 transition-colors"
              >
                Посмотреть все ({allTasksSorted.length})
              </button>
            )}
          </div>
        ) : (
          <Card variant="glass" className="text-center py-8">
            <Sparkles className="w-12 h-12 text-purple-400 mx-auto mb-3" />
            <p className="text-gray-400 mb-4">Нет задач на {formatDateDisplay(selectedDate).toLowerCase()}</p>
            <Button variant="gradient" onClick={() => setShowCreateModal(true)}>
              <Plus className="w-4 h-4" />
              Создать задачу
            </Button>
          </Card>
        )}
      </div>

      {/* XP Bar */}
      {stats && (
        <XPBar
          xp={stats.xp}
          level={stats.level}
          levelName={stats.level_name}
          xpForNextLevel={stats.xp_for_next_level}
          progressPercent={stats.xp_progress_percent}
        />
      )}

      {/* Streak Badge */}
      {stats && stats.streak_days > 0 && (
        <StreakBadge days={stats.streak_days} longestStreak={stats.longest_streak} />
      )}

      {/* Daily Goals */}
      {goals && <DailyGoals goals={goals.goals} allCompleted={goals.all_completed} />}

      {/* Mood Modal */}
      <Modal
        isOpen={showMoodModal}
        onClose={() => setShowMoodModal(false)}
        title="Как ты себя чувствуешь?"
      >
        <MoodSelector onSubmit={handleMoodSubmit} isLoading={moodLoading} />
      </Modal>

      {/* Create Task Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Создать задачу"
      >
        <TaskForm
          onSubmit={handleCreateTask}
          isLoading={createMutation.isPending}
          initialDueDate={selectedDateStr}
        />
      </Modal>

      {/* Free Time Modal */}
      <FreeTimeModal
        isOpen={showFreeTimeModal}
        onClose={() => setShowFreeTimeModal(false)}
        onSelectSuggestion={handleSelectSuggestion}
      />
    </div>
  );
}
