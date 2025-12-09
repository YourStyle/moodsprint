'use client';

import { useState, useEffect, useCallback } from 'react';
import { Pause, Play, X, Check } from 'lucide-react';
import { Button, Card } from '@/components/ui';
import type { FocusSession } from '@/domain/types';

interface FocusTimerProps {
  session: FocusSession;
  onComplete: (completeSubtask: boolean) => void;
  onCancel: () => void;
  onPause: () => void;
  onResume: () => void;
}

export function FocusTimer({
  session,
  onComplete,
  onCancel,
  onPause,
  onResume,
}: FocusTimerProps) {
  const [elapsed, setElapsed] = useState(session.elapsed_minutes * 60);
  const isPaused = session.status === 'paused';
  const planned = session.planned_duration_minutes * 60;

  useEffect(() => {
    if (isPaused) return;

    const interval = setInterval(() => {
      setElapsed((e) => e + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [isPaused]);

  const formatTime = useCallback((seconds: number) => {
    const mins = Math.floor(Math.abs(seconds) / 60);
    const secs = Math.abs(seconds) % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }, []);

  const remaining = planned - elapsed;
  const isOvertime = remaining < 0;
  const progress = Math.min(100, (elapsed / planned) * 100);

  // Circle progress
  const radius = 120;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
      {session.subtask_title && (
        <Card className="mb-6 w-full max-w-sm text-center">
          <p className="text-sm text-gray-400">Работаю над</p>
          <p className="font-semibold text-white mt-1">{session.subtask_title}</p>
          {session.task_title && (
            <p className="text-xs text-gray-400 mt-1">{session.task_title}</p>
          )}
        </Card>
      )}

      <div className="relative w-72 h-72">
        <svg className="w-full h-full transform -rotate-90">
          <circle
            cx="144"
            cy="144"
            r={radius}
            stroke="currentColor"
            strokeWidth="8"
            fill="none"
            className="text-gray-700"
          />
          <circle
            cx="144"
            cy="144"
            r={radius}
            stroke="currentColor"
            strokeWidth="8"
            fill="none"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className={`transition-all duration-1000 ${
              isOvertime ? 'text-red-500' : 'text-primary-500'
            }`}
          />
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-5xl font-bold tabular-nums ${
            isOvertime ? 'text-red-500' : 'text-white'
          }`}>
            {isOvertime && '+'}
            {formatTime(isOvertime ? -remaining : remaining)}
          </span>
          <span className="text-sm text-gray-500 mt-2">
            {isOvertime ? 'сверхурочно' : 'осталось'}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4 mt-8">
        <Button
          variant="ghost"
          iconOnly
          onClick={onCancel}
          className="w-14 h-14 rounded-full"
        >
          <X className="w-6 h-6" />
        </Button>

        <Button
          variant={isPaused ? 'primary' : 'secondary'}
          iconOnly
          onClick={isPaused ? onResume : onPause}
          className="w-16 h-16 rounded-full"
        >
          {isPaused ? (
            <Play className="w-7 h-7" />
          ) : (
            <Pause className="w-7 h-7" />
          )}
        </Button>

        <Button
          variant="primary"
          iconOnly
          onClick={() => onComplete(true)}
          className="w-14 h-14 rounded-full bg-green-500 hover:bg-green-600"
        >
          <Check className="w-6 h-6" />
        </Button>
      </div>

      <p className="text-sm text-gray-500 mt-4">
        {isPaused ? 'Пауза' : 'Фокус...'}
      </p>
    </div>
  );
}
