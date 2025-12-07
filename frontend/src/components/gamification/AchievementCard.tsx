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
          ? 'bg-gradient-to-br from-yellow-50 to-orange-50 border-yellow-200'
          : 'opacity-60'
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className={`text-3xl ${isUnlocked ? '' : 'grayscale opacity-50'}`}
        >
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-gray-900">{achievement.title}</h4>
          <p className="text-sm text-gray-500 mt-0.5">{achievement.description}</p>

          {!isUnlocked && achievement.progress_max && (
            <div className="mt-2">
              <Progress
                value={achievement.progress}
                max={achievement.progress_max}
                size="sm"
              />
              <p className="text-xs text-gray-400 mt-1">
                {achievement.progress}/{achievement.progress_max}
              </p>
            </div>
          )}

          {isUnlocked && (
            <p className="text-xs text-yellow-600 mt-2">
              +{achievement.xp_reward} XP
            </p>
          )}
        </div>
      </div>
    </Card>
  );
}
