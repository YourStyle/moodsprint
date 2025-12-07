'use client';

import { useQuery } from '@tanstack/react-query';
import { Trophy, Target, Clock, CheckSquare, TrendingUp, LogOut } from 'lucide-react';
import { Card, Progress } from '@/components/ui';
import { XPBar, StreakBadge, AchievementCard } from '@/components/gamification';
import { useAppStore } from '@/lib/store';
import { gamificationService } from '@/services';
import { authService } from '@/services';

export default function ProfilePage() {
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

  const handleLogout = () => {
    authService.logout();
    setUser(null);
    window.location.reload();
  };

  if (!user) {
    return (
      <div className="p-4 text-center">
        <p className="text-gray-500">Please login to view your profile</p>
      </div>
    );
  }

  const stats = statsData?.data;
  const achievements = achievementsData?.data;

  return (
    <div className="p-4 space-y-4">
      {/* User Info */}
      <Card className="text-center">
        <div className="w-20 h-20 mx-auto bg-gradient-to-br from-primary-400 to-accent-400 rounded-full flex items-center justify-center text-white text-3xl font-bold mb-3">
          {user.first_name?.[0] || user.username?.[0] || '?'}
        </div>
        <h1 className="text-xl font-bold text-gray-900">
          {user.first_name || user.username}
        </h1>
        {user.username && user.first_name && (
          <p className="text-sm text-gray-500">@{user.username}</p>
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
            <p className="text-2xl font-bold text-gray-900">{stats.total_tasks_completed}</p>
            <p className="text-xs text-gray-500">Tasks Done</p>
          </Card>
          <Card className="text-center">
            <Target className="w-6 h-6 mx-auto text-blue-500 mb-2" />
            <p className="text-2xl font-bold text-gray-900">{stats.total_subtasks_completed}</p>
            <p className="text-xs text-gray-500">Steps Done</p>
          </Card>
          <Card className="text-center">
            <Clock className="w-6 h-6 mx-auto text-purple-500 mb-2" />
            <p className="text-2xl font-bold text-gray-900">{Math.round(stats.total_focus_minutes / 60)}h</p>
            <p className="text-xs text-gray-500">Focus Time</p>
          </Card>
          <Card className="text-center">
            <TrendingUp className="w-6 h-6 mx-auto text-orange-500 mb-2" />
            <p className="text-2xl font-bold text-gray-900">{stats.longest_streak}</p>
            <p className="text-xs text-gray-500">Best Streak</p>
          </Card>
        </div>
      )}

      {/* Achievements */}
      {achievements && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Trophy className="w-5 h-5 text-yellow-500" />
            <h2 className="font-semibold text-gray-900">Achievements</h2>
            <span className="text-sm text-gray-500">
              {achievements.unlocked.length} unlocked
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
              <h3 className="text-sm font-medium text-gray-500 mt-4">In Progress</h3>
              <div className="space-y-2">
                {achievements.in_progress.slice(0, 5).map((ach) => (
                  <AchievementCard key={ach.id} achievement={ach} />
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* Logout */}
      <button
        onClick={handleLogout}
        className="w-full flex items-center justify-center gap-2 py-3 text-gray-500 hover:text-red-500 transition-colors"
      >
        <LogOut className="w-4 h-4" />
        <span>Sign out</span>
      </button>
    </div>
  );
}
