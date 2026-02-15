'use client';

import { Flame } from 'lucide-react';
import { Card } from '@/components/ui';
import { useTranslation } from '@/lib/i18n';

interface StreakBadgeProps {
  days: number;
  longestStreak: number;
}

export function StreakBadge({ days, longestStreak }: StreakBadgeProps) {
  const { t } = useTranslation();

  return (
    <Card variant="glass" className="flex items-center gap-3">
      <div className="w-12 h-12 rounded-full bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center animate-pulse-glow">
        <Flame className="w-6 h-6 text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-white">{days}</p>
        <p className="text-xs text-orange-400">{t('streakDaysInRow').replace('{count}', String(days))}</p>
      </div>
      {longestStreak > days && (
        <div className="ml-auto text-right">
          <p className="text-sm font-medium text-gray-400">{t('record')}</p>
          <p className="text-sm text-purple-300">{t('daysShort').replace('{count}', String(longestStreak))}</p>
        </div>
      )}
    </Card>
  );
}
