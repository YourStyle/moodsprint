'use client';

import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { Timer, Play, Pause, CheckCircle2, Square } from 'lucide-react';
import { calculateElapsedSeconds } from '@/lib/dateUtils';
import type { FocusSession } from '@/domain/types';

export interface MiniTimerProps {
  session: FocusSession;
  onPause: () => void;
  onResume: () => void;
  onComplete: () => void;
  onStop: () => void;
}

/**
 * Compact inline timer shown inside task card rows during an active focus session.
 * Displays remaining time (or elapsed time in no-timer mode) with pause/resume/complete/stop controls.
 *
 * Usage:
 *   <MiniTimer
 *     session={activeSession}
 *     onPause={() => pauseSession(session.id)}
 *     onResume={() => resumeSession(session.id)}
 *     onComplete={() => completeTask(task.id)}
 *     onStop={() => cancelSession(session.id)}
 *   />
 */
export function MiniTimer({ session, onPause, onResume, onComplete, onStop }: MiniTimerProps) {
  const initialElapsed = useMemo(() => {
    if (session.status === 'paused') {
      return session.elapsed_minutes * 60;
    }
    return calculateElapsedSeconds(session.started_at);
  }, [session.started_at, session.status, session.elapsed_minutes]);

  const [elapsed, setElapsed] = useState(initialElapsed);
  const isPaused = session.status === 'paused';
  const planned = session.planned_duration_minutes * 60;

  useEffect(() => {
    setElapsed(initialElapsed);
  }, [initialElapsed]);

  useEffect(() => {
    if (isPaused) return;
    const interval = setInterval(() => {
      setElapsed(calculateElapsedSeconds(session.started_at));
    }, 1000);
    return () => clearInterval(interval);
  }, [isPaused, session.started_at]);

  const formatTime = useCallback((seconds: number) => {
    const mins = Math.floor(Math.abs(seconds) / 60);
    const secs = Math.abs(seconds) % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }, []);

  const isNoTimerMode = session.planned_duration_minutes >= 480;
  const remaining = planned - elapsed;
  const isOvertime = !isNoTimerMode && remaining < 0;

  // Auto-complete when timer expires
  const autoCompletedRef = useRef(false);
  useEffect(() => {
    if (isNoTimerMode || isPaused) return;
    if (remaining <= 0 && !autoCompletedRef.current) {
      autoCompletedRef.current = true;
      onComplete();
    }
  }, [remaining, isNoTimerMode, isPaused, onComplete]);

  return (
    <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
      <div
        className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-mono ${
          isOvertime
            ? 'bg-red-500/20 text-red-400'
            : isPaused
            ? 'bg-yellow-500/20 text-yellow-400'
            : 'bg-primary-500/20 text-primary-400'
        }`}
      >
        <Timer className="w-3 h-3" />
        <span className="tabular-nums">
          {isOvertime && '+'}
          {isNoTimerMode
            ? formatTime(elapsed)
            : formatTime(isOvertime ? -remaining : remaining)}
        </span>
      </div>

      <button
        onClick={(e) => {
          e.stopPropagation();
          isPaused ? onResume() : onPause();
        }}
        className={`w-6 h-6 rounded flex items-center justify-center ${
          isPaused ? 'bg-primary-500/20 text-primary-400' : 'bg-yellow-500/20 text-yellow-400'
        }`}
      >
        {isPaused ? <Play className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
      </button>

      <button
        onClick={(e) => {
          e.stopPropagation();
          onComplete();
        }}
        className="w-6 h-6 rounded bg-green-500/20 text-green-400 flex items-center justify-center"
      >
        <CheckCircle2 className="w-3 h-3" />
      </button>

      <button
        onClick={(e) => {
          e.stopPropagation();
          onStop();
        }}
        className="w-6 h-6 rounded bg-gray-500/20 text-gray-400 flex items-center justify-center"
      >
        <Square className="w-3 h-3" />
      </button>
    </div>
  );
}
