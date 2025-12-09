'use client';

import { Card, Progress } from '@/components/ui';
import { ACHIEVEMENT_ICONS } from '@/domain/constants';
import type { UserAchievement } from '@/domain/types';

interface AchievementCardProps {
  achievement: UserAchievement;
}

export function AchievementCard({ achievement }: AchievementCardProps) {
  const icon = ACHIEVEMENT_ICONS[achievement.icon] || '🏆';
  const isUnlocked = achievement.is_unlocked;

  return (
    <Card
      className={`${
        isUnlocked
          ? 'bg-gradient-to-br from-yellow-500/20 to-orange-500/20 border border-yellow-500/30'
          : 'opacity-50'
      }`}
    >
      <div className="flex items-center gap-3">
        <div
          className={`text-2xl flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-lg ${
            isUnlocked ? 'bg-yellow-500/20' : 'bg-gray-700 grayscale opacity-50'
          }`}
        >
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <h4 className={`font-semibold ${isUnlocked ? 'text-white' : 'text-gray-400'}`}>
            {achievement.title}
          </h4>
          <p className="text-sm text-gray-400 mt-0.5 line-clamp-1">{achievement.description}</p>

          {!isUnlocked && achievement.progress_max && (
            <div className="mt-2">
              <Progress
                value={achievement.progress}
                max={achievement.progress_max}
                size="sm"
              />
              <p className="text-xs text-gray-500 mt-1">
                {achievement.progress}/{achievement.progress_max}
              </p>
            </div>
          )}

          {isUnlocked && (
            <p className="text-xs text-yellow-400 mt-1 font-medium">
              +{achievement.xp_reward} XP
            </p>
          )}
        </div>
      </div>
    </Card>
  );
}
