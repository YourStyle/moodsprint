'use client';

import { useState, useEffect } from 'react';
import { Plus, Sparkles, Menu, HelpCircle, Clock, Play, ChevronLeft, ChevronRight } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { Button, Card, Modal } from '@/components/ui';
import { MoodSelector } from '@/components/mood';
import { TaskForm } from '@/components/tasks';
import { AIBlob } from '@/components/AIBlob';
import { TaskCard } from '@/components/tasks';
import { XPBar, StreakBadge, DailyGoals, DailyBonus } from '@/components/gamification';
import { useAppStore } from '@/lib/store';
import { tasksService, moodService, gamificationService, focusService } from '@/services';
import { hapticFeedback } from '@/lib/telegram';
import type { MoodLevel, EnergyLevel, TaskPriority } from '@/domain/types';

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

export default function HomePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, isLoading, latestMood, setLatestMood, showMoodModal, setShowMoodModal, showXPAnimation, setActiveSession } = useAppStore();
  const [moodLoading, setMoodLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [showCreateModal, setShowCreateModal] = useState(false);

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

  const { data: tasksData, isLoading: tasksLoading } = useQuery({
    queryKey: ['tasks', 'by_date', selectedDateStr],
    queryFn: () => tasksService.getTasks({ due_date: selectedDateStr, limit: 50 }),
    enabled: !!user,
  });

  const createMutation = useMutation({
    mutationFn: (input: { title: string; description: string; priority: TaskPriority; due_date: string }) =>
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

  const handleCreateTask = (title: string, description: string, priority: TaskPriority, dueDate: string) => {
    createMutation.mutate({ title, description, priority, due_date: dueDate });
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
  const incompleteTasks = tasks.filter(t => t.status !== 'completed');
  const completedTasks = tasks.filter(t => t.status === 'completed');

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

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            {getGreeting()},
          </h1>
          <p className="text-gray-400">{user.first_name || 'друг'}</p>
        </div>
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white font-bold">
          {(user.first_name?.[0] || '?').toUpperCase()}
        </div>
      </div>

      {/* Week Calendar */}
      <WeekCalendar selectedDate={selectedDate} onDateSelect={setSelectedDate} />

      {/* Tasks Section - Moved to top */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-white capitalize">{formatDateDisplay(selectedDate)}</h2>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowCreateModal(true)}
          >
            <Plus className="w-4 h-4 mr-1" />
            Добавить
          </Button>
        </div>

        {tasksLoading ? (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <Card key={i} variant="glass" className="h-20 animate-pulse" />
            ))}
          </div>
        ) : tasks.length > 0 ? (
          <div className="space-y-2">
            {/* Incomplete tasks first */}
            {incompleteTasks.map((task) => (
              <TaskCardCompact
                key={task.id}
                task={task}
                onClick={() => router.push(`/tasks/${task.id}`)}
                onStart={() => startFocusMutation.mutate(task.id)}
              />
            ))}
            {/* Completed tasks */}
            {completedTasks.map((task) => (
              <TaskCardCompact
                key={task.id}
                task={task}
                onClick={() => router.push(`/tasks/${task.id}`)}
              />
            ))}
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

      {/* AI Assistant Blob */}
      <div className="relative">
        <Card variant="glass" padding="lg" className="overflow-visible">
          <div className="flex items-center gap-4">
            <AIBlob size={80} className="flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <h2 className="text-lg font-semibold text-white mb-1">
                Твой AI-помощник
              </h2>
              <p className="text-sm text-gray-400">
                {latestMood
                  ? 'Готов помочь с задачами на основе твоего настроения'
                  : 'Отметь настроение, чтобы я мог подстроиться под тебя'}
              </p>
              <Button
                variant="ghost"
                size="sm"
                className="mt-2 text-purple-400"
                onClick={() => setShowMoodModal(true)}
              >
                <Sparkles className="w-4 h-4 mr-1" />
                {latestMood ? 'Обновить настроение' : 'Отметить настроение'}
              </Button>
            </div>
          </div>
        </Card>
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
    </div>
  );
}
