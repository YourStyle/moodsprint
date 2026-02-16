'use client';

import { Flame } from 'lucide-react';

interface StreakIndicatorProps {
  days: number;
}

export function StreakIndicator({ days }: StreakIndicatorProps) {
  if (days <= 0) return null;

  const isHot = days > 7;
  const isOnFire = days > 14;

  return (
    <div className="relative w-10 h-10 rounded-full bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center shadow-lg shadow-orange-500/30">
      <Flame
        className={`w-5 h-5 text-white ${isOnFire ? 'animate-flicker' : isHot ? 'animate-pulse' : ''}`}
      />
      <span className="absolute -bottom-1 -right-1 min-w-[18px] h-[18px] rounded-full bg-dark-800 border border-orange-500 text-[10px] font-bold text-orange-400 flex items-center justify-center px-0.5">
        {days}
      </span>
    </div>
  );
}
