'use client';

import { Card } from '@/components/ui';
import { MOOD_EMOJIS, ENERGY_EMOJIS } from '@/domain/constants';
import type { MoodCheck } from '@/domain/types';

interface MoodCardProps {
  mood: MoodCheck | null;
  onCheck: () => void;
}

export function MoodCard({ mood, onCheck }: MoodCardProps) {
  if (!mood) {
    return (
      <Card
        className="bg-gradient-to-br from-primary-50 to-accent-50 border-none cursor-pointer hover:shadow-md transition-shadow"
        onClick={onCheck}
      >
        <div className="text-center py-2">
          <div className="text-3xl mb-2">How are you feeling?</div>
          <p className="text-sm text-gray-600">Tap to log your mood</p>
        </div>
      </Card>
    );
  }

  const isOld = (() => {
    const checkTime = new Date(mood.created_at).getTime();
    const now = Date.now();
    const hoursSince = (now - checkTime) / (1000 * 60 * 60);
    return hoursSince > 4;
  })();

  return (
    <Card
      className={`cursor-pointer hover:shadow-md transition-shadow ${
        isOld ? 'bg-gray-50' : 'bg-gradient-to-br from-primary-50 to-accent-50'
      } border-none`}
      onClick={onCheck}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-500 mb-1">Current State</p>
          <div className="flex items-center gap-3">
            <span className="text-2xl">{MOOD_EMOJIS[mood.mood]}</span>
            <span className="text-2xl">{ENERGY_EMOJIS[mood.energy]}</span>
            <div className="text-sm">
              <p className="font-medium text-gray-900">{mood.mood_label}</p>
              <p className="text-gray-500">{mood.energy_label}</p>
            </div>
          </div>
        </div>
        {isOld && (
          <div className="text-right">
            <span className="text-xs text-gray-400">Tap to update</span>
          </div>
        )}
      </div>
    </Card>
  );
}
