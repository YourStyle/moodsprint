'use client';

import { useState } from 'react';
import { Plus, Sparkles, Menu, HelpCircle, Clock } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { Button, Card, Modal } from '@/components/ui';
import { MoodSelector } from '@/components/mood';
import { AIBlob } from '@/components/AIBlob';
import { TaskCard } from '@/components/tasks';
import { XPBar, StreakBadge, DailyGoals, DailyBonus } from '@/components/gamification';
import { useAppStore } from '@/lib/store';
import { tasksService, moodService, gamificationService } from '@/services';
import { hapticFeedback } from '@/lib/telegram';
import type { MoodLevel, EnergyLevel } from '@/domain/types';

function WeekCalendar() {
  const days = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];
  const today = new Date();
  const currentDay = today.getDay();

  return (
    <div className="flex justify-between gap-1">
      {days.map((day, index) => {
        const isToday = index === currentDay;
        const date = new Date(today);
        date.setDate(today.getDate() - currentDay + index);

        return (
          <div
            key={day}
            className={`flex flex-col items-center py-2 px-3 rounded-xl transition-all ${
              isToday
                ? 'bg-dark-600 border border-purple-500/30'
                : 'opacity-60'
            }`}
          >
            <span className="text-xs text-gray-400 mb-1">{day}</span>
            <span className={`text-lg font-semibold ${isToday ? 'text-white' : 'text-gray-400'}`}>
              {date.getDate()}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function TaskCardNew({
  task,
  onClick,
}: {
  task: { id: number; title: string; progress_percent: number; estimated_minutes?: number; ai_suggestion?: string };
  onClick: () => void;
}) {
  return (
    <Card
      variant="gradient"
      padding="md"
      hover
      onClick={onClick}
      className="relative overflow-hidden"
    >
      {/* Time indicator */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h3 className="font-semibold text-white">{task.title}</h3>
            {task.estimated_minutes && (
              <div className="flex items-center gap-1 text-xs text-gray-400">
                <Clock className="w-3 h-3" />
                <span>{task.estimated_minutes} мин</span>
              </div>
            )}
          </div>
        </div>
        <span className="text-purple-300 font-medium">{task.progress_percent}%</span>
      </div>

      {/* Progress bar */}
      <div className="progress-bar h-1.5 mb-3">
        <div
          className="progress-bar-fill h-full"
          style={{ width: `${task.progress_percent}%` }}
        />
      </div>

      {/* AI suggestion */}
      {task.ai_suggestion && (
        <div className="flex items-start gap-2 text-sm">
          <span className="text-purple-400">✨</span>
          <p className="text-gray-400">{task.ai_suggestion}</p>
        </div>
      )}
    </Card>
  );
}

export default function HomePage() {
  const router = useRouter();
  const { user, isLoading, latestMood, setLatestMood, showMoodModal, setShowMoodModal, showXPAnimation } = useAppStore();
  const [moodLoading, setMoodLoading] = useState(false);

  const { data: tasksData, isLoading: tasksLoading } = useQuery({
    queryKey: ['tasks', 'active'],
    queryFn: () => tasksService.getTasks({ status: 'in_progress', limit: 3 }),
    enabled: !!user,
  });

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
  const activeTasks = tasksData?.data?.tasks || [];

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
          <p className="text-gray-400">{user.first_name || 'there'}</p>
        </div>
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white font-bold">
          {(user.first_name?.[0] || 'U').toUpperCase()}
        </div>
      </div>

      {/* Week Calendar */}
      <WeekCalendar />

      {/* AI Assistant Blob */}
      <div className="relative">
        <Card variant="glass" padding="lg" className="overflow-visible">
          <div className="flex items-center gap-4">
            <AIBlob size={100} className="flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <h2 className="text-lg font-semibold text-white mb-1">
                Твой AI-помощник
              </h2>
              <p className="text-sm text-gray-400">
                {latestMood
                  ? 'Готов помочь с задачами на основе твоего настроения'
                  : 'Отметь настроение, чтобы я мог подстроиться под тебя'}
              </p>
              {!latestMood && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="mt-2 text-purple-400"
                  onClick={() => setShowMoodModal(true)}
                >
                  <Sparkles className="w-4 h-4 mr-1" />
                  Отметить настроение
                </Button>
              )}
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

      {/* Tasks Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-white">Твои задачи</h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push('/tasks')}
          >
            Все
          </Button>
        </div>

        {tasksLoading ? (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <Card key={i} variant="glass" className="h-28 animate-pulse" />
            ))}
          </div>
        ) : activeTasks.length > 0 ? (
          <div className="space-y-3">
            {activeTasks.map((task, index) => (
              <div
                key={task.id}
                className="animate-slide-up"
                style={{ animationDelay: `${index * 100}ms` }}
              >
                <TaskCardNew
                  task={{
                    ...task,
                    ai_suggestion: index === 0 ? 'ИИ приоритизировал эту задачу — начни с неё прямо сейчас.' : undefined,
                    estimated_minutes: task.subtasks?.reduce((acc, s) => acc + (s.estimated_minutes || 0), 0) || 30,
                  }}
                  onClick={() => router.push(`/tasks/${task.id}`)}
                />
              </div>
            ))}
          </div>
        ) : (
          <Card variant="glass" className="text-center py-8">
            <Sparkles className="w-12 h-12 text-purple-400 mx-auto mb-3" />
            <p className="text-gray-400 mb-4">Нет активных задач</p>
            <Button variant="gradient" onClick={() => router.push('/tasks')}>
              <Plus className="w-4 h-4" />
              Создать задачу
            </Button>
          </Card>
        )}
      </div>

      {/* Mood Modal */}
      <Modal
        isOpen={showMoodModal}
        onClose={() => setShowMoodModal(false)}
        title="Как ты себя чувствуешь?"
      >
        <MoodSelector onSubmit={handleMoodSubmit} isLoading={moodLoading} />
      </Modal>
    </div>
  );
}
