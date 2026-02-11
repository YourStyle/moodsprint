'use client';

import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { LogOut, Settings, BarChart3, Sun, Moon, Sunrise, Sunset, Clock, Wallet } from 'lucide-react';
import { Card, ScrollBackdrop } from '@/components/ui';
import { TonConnectButton } from '@/components/ui/TonConnectButton';
import { XPBar, StreakBadge } from '@/components/gamification';
import { SparksBalance } from '@/components/sparks';
import { GenreSelector } from '@/components/GenreSelector';
import { ShowcaseSlots } from '@/components/cards/ShowcaseSlots';
import { useAppStore } from '@/lib/store';
import { gamificationService, onboardingService } from '@/services';
import { authService } from '@/services';
import { useLanguage } from '@/lib/i18n';

export default function ProfilePage() {
  const router = useRouter();
  const { user, setUser, isTelegramEnvironment } = useAppStore();
  const { t } = useLanguage();

  const { data: statsData } = useQuery({
    queryKey: ['user', 'stats'],
    queryFn: () => gamificationService.getUserStats(),
    enabled: !!user,
  });

  const { data: patternsData } = useQuery({
    queryKey: ['user', 'productivity-patterns'],
    queryFn: () => gamificationService.getProductivityPatterns(),
    enabled: !!user,
  });

  const { data: profileData } = useQuery({
    queryKey: ['onboarding', 'profile'],
    queryFn: () => onboardingService.getProfile(),
    enabled: !!user,
  });

  const handleLogout = () => {
    authService.logout();
    setUser(null);
    window.location.reload();
  };

  if (!user) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-4">
        <div className="p-6 bg-purple-500/20 rounded-full mb-6">
          <Settings className="w-12 h-12 text-purple-400" />
        </div>
        <h2 className="text-xl font-bold text-white mb-2">{t('loginToViewProfile')}</h2>
        <p className="text-gray-400 text-center mb-6 max-w-sm">
          Войдите в приложение, чтобы просмотреть свой профиль и статистику
        </p>
        <button
          onClick={() => router.push('/')}
          className="px-6 py-3 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700 transition-colors"
        >
          На главную
        </button>
      </div>
    );
  }

  const stats = statsData?.data;
  const patterns = patternsData?.data;
  const profile = profileData?.data?.profile;

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
      case 'morning': return t('morning');
      case 'afternoon': return t('afternoon');
      case 'evening': return t('evening');
      case 'night': return t('night');
      default: return t('variousTime');
    }
  };

  return (
    <div className="p-4 space-y-4">
      <ScrollBackdrop />
      {/* User Info */}
      <Card className="text-center relative z-10">
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

        {/* Genre selector and Settings under avatar */}
        <div className="flex items-center justify-center gap-3 mt-4 pt-4 border-t border-gray-700/50">
          <GenreSelector currentGenre={profile?.favorite_genre} />
          <button
            onClick={() => router.push('/settings')}
            className="p-2 rounded-xl bg-gray-800/80 border border-gray-700/50 text-gray-400 hover:text-white transition-colors"
            title={t('settings')}
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </Card>

      {/* Sparks Balance */}
      <SparksBalance />

      {/* Wallet - only show in Telegram environment */}
      {isTelegramEnvironment && (
        <Card>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Wallet className="w-5 h-5 text-cyan-500" />
              <span className="font-medium text-white">{t('tonWallet')}</span>
            </div>
            <TonConnectButton />
          </div>
        </Card>
      )}

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

      {/* Profile Showcase - 3 card slots */}
      <Card>
        <ShowcaseSlots />
      </Card>

      {/* Productivity Patterns */}
      {patterns && patterns.total_sessions > 0 && (
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-primary-500" />
            <h2 className="font-semibold text-white">{t('productivityAnalytics')}</h2>
          </div>

          {/* Best productivity time */}
          <div className="flex items-center gap-3 mb-4 p-3 bg-gray-700/50 rounded-xl">
            {getProductivityIcon(patterns.productivity_time)}
            <div>
              <p className="text-sm text-gray-400">{t('bestWorkTime')}</p>
              <p className="font-medium text-white">{getProductivityLabel(patterns.productivity_time)}</p>
            </div>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-3 gap-2 mb-4">
            <div className="text-center p-2 bg-gray-700/30 rounded-lg">
              <p className="text-lg font-bold text-white">{patterns.total_sessions}</p>
              <p className="text-xs text-gray-400">{t('sessions')}</p>
            </div>
            <div className="text-center p-2 bg-gray-700/30 rounded-lg">
              <p className="text-lg font-bold text-green-500">{patterns.overall_success_rate}%</p>
              <p className="text-xs text-gray-400">{t('completed')}</p>
            </div>
            <div className="text-center p-2 bg-gray-700/30 rounded-lg">
              <p className="text-lg font-bold text-white">{patterns.avg_session_duration}</p>
              <p className="text-xs text-gray-400">{t('minPerSession')}</p>
            </div>
          </div>

          {/* Best day */}
          {patterns.best_day && patterns.best_day.sessions > 0 && (
            <div className="text-sm text-gray-400">
              <span className="text-white font-medium">{patterns.best_day.day_name}</span>
              {' — '}{t('mostProductiveDay')} ({patterns.best_day.success_rate}% {t('successfulSessions')})
            </div>
          )}
        </Card>
      )}

      {/* Logout */}
      <button
        onClick={handleLogout}
        className="w-full flex items-center justify-center gap-2 py-3 text-gray-400 hover:text-red-400 transition-colors"
      >
        <LogOut className="w-4 h-4" />
        <span>{t('logout')}</span>
      </button>
    </div>
  );
}
