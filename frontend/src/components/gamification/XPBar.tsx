'use client';

import { CircularProgress } from '@/components/ui/Progress';

interface XPBarProps {
  xp: number;
  level: number;
  levelName?: string;
  xpForNextLevel: number;
  progressPercent: number;
}

export function XPBar({ xp, level, levelName, xpForNextLevel, progressPercent }: XPBarProps) {
  return (
    <div className="glass-card p-4">
      <div className="flex items-center gap-4">
        {/* Circular progress */}
        <CircularProgress value={progressPercent} size={64} strokeWidth={5}>
          <span className="text-lg font-bold text-white">{level}</span>
        </CircularProgress>

        {/* Level info */}
        <div className="flex-1">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-gray-400">Уровень {level}</span>
            <span className="text-sm text-purple-300">{xp} / {xpForNextLevel} XP</span>
          </div>
          {levelName && (
            <p className="text-lg font-semibold text-white">{levelName}</p>
          )}
          <div className="progress-bar h-1.5 mt-2">
            <div
              className="progress-bar-fill h-full"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
