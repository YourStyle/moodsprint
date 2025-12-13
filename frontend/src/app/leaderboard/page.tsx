'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Trophy, Medal, Flame, Star, Crown, Skull } from 'lucide-react';
import { Card } from '@/components/ui';
import { gamificationService } from '@/services';
import { useAppStore } from '@/lib/store';
import { cn } from '@/lib/utils';

type LeaderboardType = 'weekly' | 'all_time';

export default function LeaderboardPage() {
  const { user } = useAppStore();
  const [type, setType] = useState<LeaderboardType>('weekly');

  const { data: leaderboardData, isLoading } = useQuery({
    queryKey: ['leaderboard', type],
    queryFn: () => gamificationService.getLeaderboard(type, 20),
    enabled: !!user,
  });

  const leaderboard = leaderboardData?.data?.leaderboard || [];

  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1:
        return <Crown className="w-5 h-5 text-yellow-400" />;
      case 2:
        return <Medal className="w-5 h-5 text-gray-300" />;
      case 3:
        return <Medal className="w-5 h-5 text-amber-600" />;
      default:
        return <span className="w-5 h-5 flex items-center justify-center text-sm text-gray-400">{rank}</span>;
    }
  };

  const getRankBg = (rank: number) => {
    switch (rank) {
      case 1:
        return 'bg-gradient-to-r from-yellow-500/20 to-amber-500/20 border-yellow-500/30';
      case 2:
        return 'bg-gradient-to-r from-gray-400/20 to-gray-300/20 border-gray-400/30';
      case 3:
        return 'bg-gradient-to-r from-amber-600/20 to-orange-600/20 border-amber-600/30';
      default:
        return 'bg-gray-800/50 border-gray-700/50';
    }
  };

  if (!user) {
    return (
      <div className="p-4 text-center">
        <p className="text-gray-500">Войдите чтобы увидеть лидерборд</p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4 pt-safe">
      {/* Header */}
      <div className="text-center mb-6">
        <Trophy className="w-12 h-12 text-yellow-500 mx-auto mb-2" />
        <h1 className="text-2xl font-bold text-white">Лидерборд</h1>
        <p className="text-sm text-gray-400">Лучшие охотники на монстров</p>
      </div>

      {/* Type Toggle */}
      <div className="flex gap-2 p-1 bg-gray-800 rounded-xl">
        <button
          onClick={() => setType('weekly')}
          className={cn(
            'flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all',
            type === 'weekly'
              ? 'bg-purple-500 text-white'
              : 'text-gray-400 hover:text-white'
          )}
        >
          За неделю
        </button>
        <button
          onClick={() => setType('all_time')}
          className={cn(
            'flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all',
            type === 'all_time'
              ? 'bg-purple-500 text-white'
              : 'text-gray-400 hover:text-white'
          )}
        >
          Все время
        </button>
      </div>

      {/* Leaderboard */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <Card key={i} className="animate-pulse">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-gray-700 rounded-full" />
                <div className="flex-1">
                  <div className="h-4 bg-gray-700 rounded w-1/3 mb-2" />
                  <div className="h-3 bg-gray-700 rounded w-1/4" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : leaderboard.length === 0 ? (
        <Card className="text-center py-8">
          <Star className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400">Пока нет участников</p>
          <p className="text-sm text-gray-500 mt-1">
            Будь первым в рейтинге!
          </p>
        </Card>
      ) : (
        <div className="space-y-2">
          {leaderboard.map((entry) => {
            const isCurrentUser = entry.user_id === user.id;

            return (
              <div
                key={entry.user_id}
                className={cn(
                  'flex items-center gap-3 p-3 rounded-xl border transition-all',
                  getRankBg(entry.rank),
                  isCurrentUser && 'ring-2 ring-purple-500'
                )}
              >
                {/* Rank */}
                <div className="w-8 flex items-center justify-center">
                  {getRankIcon(entry.rank)}
                </div>

                {/* Avatar */}
                <div
                  className={cn(
                    'w-10 h-10 rounded-full flex items-center justify-center text-white font-bold',
                    entry.rank === 1
                      ? 'bg-gradient-to-br from-yellow-400 to-amber-500'
                      : entry.rank === 2
                      ? 'bg-gradient-to-br from-gray-300 to-gray-400'
                      : entry.rank === 3
                      ? 'bg-gradient-to-br from-amber-500 to-orange-600'
                      : 'bg-gradient-to-br from-purple-500 to-blue-500'
                  )}
                >
                  {entry.first_name?.[0] || entry.username?.[0] || '?'}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className={cn(
                    'font-medium truncate',
                    isCurrentUser ? 'text-purple-400' : 'text-white'
                  )}>
                    {entry.first_name || entry.username}
                    {isCurrentUser && ' (вы)'}
                  </p>
                  <div className="flex items-center gap-2 text-xs text-gray-400">
                    <span>Ур. {entry.level}</span>
                    {entry.streak_days > 0 && (
                      <span className="flex items-center gap-0.5">
                        <Flame className="w-3 h-3 text-orange-500" />
                        {entry.streak_days}
                      </span>
                    )}
                  </div>
                </div>

                {/* Monsters Killed */}
                <div className="text-right">
                  <div className="flex items-center gap-1 justify-end">
                    <Skull className="w-4 h-4 text-red-400" />
                    <p className="font-bold text-red-400">{entry.monsters_killed || 0}</p>
                  </div>
                  <p className="text-xs text-gray-500">монстров</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
