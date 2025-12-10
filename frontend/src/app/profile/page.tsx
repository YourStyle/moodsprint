'use client';

import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { Trophy, Target, Clock, CheckSquare, TrendingUp, LogOut, Settings, BarChart3, Sun, Moon, Sunrise, Sunset, Swords, Scroll } from 'lucide-react';
import { Card, Progress, Button } from '@/components/ui';
import { XPBar, StreakBadge, AchievementCard, DailyQuests, CharacterStats } from '@/components/gamification';
import { useAppStore } from '@/lib/store';
import { gamificationService } from '@/services';
import { authService } from '@/services';

export default function ProfilePage() {
  const router = useRouter();
  const { user, setUser } = useAppStore();

  const { data: statsData } = useQuery({
    queryKey: ['user', 'stats'],
    queryFn: () => gamificationService.getUserStats(),
    enabled: !!user,
  });

  const { data: achievementsData } = useQuery({
    queryKey: ['user', 'achievements'],
    queryFn: () => gamificationService.getUserAchievements(),
    enabled: !!user,
  });

  const { data: patternsData } = useQuery({
    queryKey: ['user', 'productivity-patterns'],
    queryFn: () => gamificationService.getProductivityPatterns(),
    enabled: !!user,
  });

  const { data: questsData } = useQuery({
    queryKey: ['quests'],
    queryFn: () => gamificationService.getQuests(),
    enabled: !!user,
  });

  const { data: characterData } = useQuery({
    queryKey: ['character'],
    queryFn: () => gamificationService.getCharacter(),
    enabled: !!user,
  });

  const handleLogout = () => {
    authService.logout();
    setUser(null);
    window.location.reload();
  };

  if (!user) {
    return (
      <div className="p-4 text-center">
        <p className="text-gray-500">Войдите чтобы просмотреть профиль</p>
      </div>
    );
  }

  const stats = statsData?.data;
  const achievements = achievementsData?.data;
  const patterns = patternsData?.data;
  const quests = questsData?.data?.quests || [];
  const character = characterData?.data?.character;

  const getProductivityIcon = (time: string) => {
    switch (time) {
      case 'morning': return <Sunrise className="w-5 h-5 text-yellow-500" />;
      case 'afternoon': return <Sun className="w-5 h-5 text-orange-500" />;
      case 'evening': return <Sunset className="w-5 h-5 text-purple-500" />;
      case 'night': return <Moon className="w-5 h-5 text-blue-500" />;
      default: return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  const getProductivityLabel = (time: string) => {
    switch (time) {
      case 'morning': return 'Утро (5:00-12:00)';
      case 'afternoon': return 'День (12:00-17:00)';
      case 'evening': return 'Вечер (17:00-21:00)';
      case 'night': return 'Ночь (21:00-5:00)';
      default: return 'Разное время';
    }
  };

  return (
    <div className="p-4 space-y-4 pt-safe">
      {/* User Info */}
      <Card className="text-center">
        {user.photo_url ? (
          <img
            src={user.photo_url}
            alt={user.first_name || user.username || 'Профиль'}
            className="w-20 h-20 mx-auto rounded-full object-cover mb-3"
          />
        ) : (
          <div className="w-20 h-20 mx-auto bg-gradient-to-br from-primary-400 to-accent-400 rounded-full flex items-center justify-center text-white text-3xl font-bold mb-3">
            {user.first_name?.[0] || user.username?.[0] || '?'}
          </div>
        )}
        <h1 className="text-xl font-bold text-white">
          {user.first_name || user.username}
        </h1>
        {user.username && user.first_name && (
          <p className="text-sm text-gray-400">@{user.username}</p>
        )}
      </Card>

      {/* XP Bar */}
      {stats && (
        <XPBar
          xp={stats.xp}
          level={stats.level}
          xpForNextLevel={stats.xp_for_next_level}
          progressPercent={stats.xp_progress_percent}
        />
      )}

      {/* Streak */}
      {stats && (
        <StreakBadge days={stats.streak_days} longestStreak={stats.longest_streak} />
      )}

      {/* Stats Grid */}
      {stats && (
        <div className="grid grid-cols-2 gap-3">
          <Card className="text-center">
            <CheckSquare className="w-6 h-6 mx-auto text-green-500 mb-2" />
            <p className="text-2xl font-bold text-white">{stats.total_tasks_completed}</p>
            <p className="text-xs text-gray-400">Задач выполнено</p>
          </Card>
          <Card className="text-center">
            <Target className="w-6 h-6 mx-auto text-blue-500 mb-2" />
            <p className="text-2xl font-bold text-white">{stats.total_subtasks_completed}</p>
            <p className="text-xs text-gray-400">Шагов выполнено</p>
          </Card>
          <Card className="text-center">
            <Clock className="w-6 h-6 mx-auto text-purple-500 mb-2" />
            <p className="text-2xl font-bold text-white">{Math.round(stats.total_focus_minutes / 60)}ч</p>
            <p className="text-xs text-gray-400">Время фокуса</p>
          </Card>
          <Card className="text-center">
            <TrendingUp className="w-6 h-6 mx-auto text-orange-500 mb-2" />
            <p className="text-2xl font-bold text-white">{stats.longest_streak}</p>
            <p className="text-xs text-gray-400">Лучшая серия</p>
          </Card>
        </div>
      )}

      {/* Daily Quests */}
      {quests.length > 0 && <DailyQuests quests={quests} />}

      {/* Character Stats & Arena */}
      {character && (
        <>
          <CharacterStats character={character} />
          <Button
            variant="secondary"
            className="w-full"
            onClick={() => router.push('/arena')}
          >
            <Swords className="w-5 h-5 mr-2" />
            Перейти на арену
          </Button>
        </>
      )}

      {/* Productivity Patterns */}
      {patterns && patterns.total_sessions > 0 && (
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-primary-500" />
            <h2 className="font-semibold text-white">Аналитика продуктивности</h2>
          </div>

          {/* Best productivity time */}
          <div className="flex items-center gap-3 mb-4 p-3 bg-gray-700/50 rounded-xl">
            {getProductivityIcon(patterns.productivity_time)}
            <div>
              <p className="text-sm text-gray-400">Лучшее время для работы</p>
              <p className="font-medium text-white">{getProductivityLabel(patterns.productivity_time)}</p>
            </div>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-3 gap-2 mb-4">
            <div className="text-center p-2 bg-gray-700/30 rounded-lg">
              <p className="text-lg font-bold text-white">{patterns.total_sessions}</p>
              <p className="text-xs text-gray-400">Сессий</p>
            </div>
            <div className="text-center p-2 bg-gray-700/30 rounded-lg">
              <p className="text-lg font-bold text-green-500">{patterns.overall_success_rate}%</p>
              <p className="text-xs text-gray-400">Завершено</p>
            </div>
            <div className="text-center p-2 bg-gray-700/30 rounded-lg">
              <p className="text-lg font-bold text-white">{patterns.avg_session_duration}</p>
              <p className="text-xs text-gray-400">мин/сессия</p>
            </div>
          </div>

          {/* Best day */}
          {patterns.best_day && patterns.best_day.sessions > 0 && (
            <div className="text-sm text-gray-400">
              <span className="text-white font-medium">{patterns.best_day.day_name}</span>
              {' — '}ваш самый продуктивный день ({patterns.best_day.success_rate}% успешных сессий)
            </div>
          )}
        </Card>
      )}

      {/* Achievements */}
      {achievements && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Trophy className="w-5 h-5 text-yellow-500" />
            <h2 className="font-semibold text-white">Достижения</h2>
            <span className="text-sm text-gray-400">
              {achievements.unlocked.length} получено
            </span>
          </div>

          {achievements.unlocked.length > 0 && (
            <div className="space-y-2">
              {achievements.unlocked.map((ach) => (
                <AchievementCard key={ach.id} achievement={ach} />
              ))}
            </div>
          )}

          {achievements.in_progress.length > 0 && (
            <>
              <h3 className="text-sm font-medium text-gray-400 mt-4">В процессе</h3>
              <div className="space-y-2">
                {achievements.in_progress.slice(0, 5).map((ach) => (
                  <AchievementCard key={ach.id} achievement={ach} />
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* Settings & Logout */}
      <div className="space-y-2">
        <button
          onClick={() => router.push('/settings')}
          className="w-full flex items-center justify-center gap-2 py-3 text-gray-300 hover:text-white transition-colors bg-gray-800 rounded-xl"
        >
          <Settings className="w-4 h-4" />
          <span>Настройки</span>
        </button>
        <button
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-2 py-3 text-gray-400 hover:text-red-400 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span>Выйти</span>
        </button>
      </div>
    </div>
  );
}
