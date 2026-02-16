'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ChevronRight, Clock, CheckCircle2, Pause, Play, Square, Timer } from 'lucide-react';
import { Card, Progress } from '@/components/ui';
import { useAppStore } from '@/lib/store';
import { focusService } from '@/services';
import { hapticFeedback } from '@/lib/telegram';
import { PRIORITY_COLORS, TASK_TYPE_EMOJIS, TASK_TYPE_COLORS } from '@/domain/constants';
import type { Task, FocusSession } from '@/domain/types';

interface TaskCardProps {
  task: Task;
  onClick: () => void;
}

function calculateElapsedSeconds(session: FocusSession): number {
  const startedAt = new Date(session.started_at).getTime();
  const now = Date.now();
  return Math.floor((now - startedAt) / 1000);
}

function FocusTimer({ session, onComplete, onPause, onResume, onStop }: {
  session: FocusSession;
  onComplete: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
}) {
  const initialElapsed = useMemo(() => {
    if (session.status === 'paused') {
      return session.elapsed_minutes * 60;
    }
    return calculateElapsedSeconds(session);
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
      setElapsed(calculateElapsedSeconds(session));
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

  return (
    <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
      <div className={`flex items-center gap-1.5 px-2 py-1 rounded-lg ${
        isOvertime ? 'bg-red-500/20 text-red-400' : isPaused ? 'bg-yellow-500/20 text-yellow-400' : 'bg-primary-500/20 text-primary-400'
      }`}>
        <Timer className="w-3.5 h-3.5" />
        <span className="text-sm font-mono font-medium tabular-nums">
          {isOvertime && '+'}
          {isNoTimerMode ? formatTime(elapsed) : formatTime(isOvertime ? -remaining : remaining)}
        </span>
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); (isPaused ? onResume : onPause)(); }}
        className={`p-1.5 rounded-lg transition-colors ${
          isPaused ? 'bg-primary-500/20 text-primary-400 hover:bg-primary-500/30' : 'bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30'
        }`}
      >
        {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
      </button>
      <button
        onClick={(e) => { e.stopPropagation(); onComplete(); }}
        className="p-1.5 rounded-lg bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-colors"
      >
        <CheckCircle2 className="w-4 h-4" />
      </button>
      <button
        onClick={(e) => { e.stopPropagation(); onStop(); }}
        className="p-1.5 rounded-lg bg-gray-500/20 text-gray-400 hover:bg-gray-500/30 transition-colors"
      >
        <Square className="w-4 h-4" />
      </button>
    </div>
  );
}

export function TaskCard({ task, onClick }: TaskCardProps) {
  const queryClient = useQueryClient();
  const { activeSessions, removeActiveSession, updateActiveSession, showXPAnimation } = useAppStore();
  const isCompleted = task.status === 'completed';

  // Find active session for this task
  const activeSession = activeSessions.find(s => s.task_id === task.id);
  const hasActiveSession = !!activeSession;

  const completeMutation = useMutation({
    mutationFn: () => focusService.completeSession(activeSession?.id, true),
    onSuccess: (result) => {
      if (activeSession) removeActiveSession(activeSession.id);
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['focus'] });
      queryClient.invalidateQueries({ queryKey: ['user', 'stats'] });
      if (result.data?.xp_earned) showXPAnimation(result.data.xp_earned);
      hapticFeedback('success');
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => focusService.cancelSession(activeSession?.id),
    onSuccess: () => {
      if (activeSession) removeActiveSession(activeSession.id);
      queryClient.invalidateQueries({ queryKey: ['focus'] });
      hapticFeedback('light');
    },
  });

  const pauseMutation = useMutation({
    mutationFn: () => focusService.pauseSession(),
    onSuccess: (result) => {
      if (result.success && result.data?.session) {
        updateActiveSession(result.data.session);
      }
    },
  });

  const resumeMutation = useMutation({
    mutationFn: () => focusService.resumeSession(),
    onSuccess: (result) => {
      if (result.success && result.data?.session) {
        updateActiveSession(result.data.session);
      }
    },
  });

  return (
    <Card
      className={`cursor-pointer hover:shadow-md transition-all ${
        isCompleted ? 'opacity-60' : ''
      } ${hasActiveSession ? 'ring-2 ring-primary-500/50' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-1">
          {isCompleted ? (
            <CheckCircle2 className="w-5 h-5 text-green-500" />
          ) : hasActiveSession ? (
            <div className="w-5 h-5 rounded-full bg-primary-500 animate-pulse" />
          ) : (
            <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h3
              className={`font-medium text-white ${
                isCompleted ? 'line-through text-gray-400' : ''
              }`}
            >
              {task.title}
            </h3>
            {!hasActiveSession && (
              <div className="flex items-center gap-1.5 flex-shrink-0">
                {task.postponed_count > 0 && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-yellow-500/20 text-yellow-400 font-medium">
                    {task.postponed_count}x
                  </span>
                )}
                {task.task_type && (
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${TASK_TYPE_COLORS[task.task_type]}`}
                  >
                    {TASK_TYPE_EMOJIS[task.task_type]}
                  </span>
                )}
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${PRIORITY_COLORS[task.priority]}`}
                >
                  {task.priority}
                </span>
              </div>
            )}
          </div>

          {/* Active Session Timer */}
          {hasActiveSession && activeSession && (
            <div className="mt-2">
              <FocusTimer
                session={activeSession}
                onComplete={() => completeMutation.mutate()}
                onPause={() => pauseMutation.mutate()}
                onResume={() => resumeMutation.mutate()}
                onStop={() => cancelMutation.mutate()}
              />
            </div>
          )}

          {!hasActiveSession && task.description && (
            <p className="text-sm text-gray-500 mt-1 line-clamp-2">
              {task.description}
            </p>
          )}

          {task.subtasks_count > 0 && (
            <div className="mt-3 space-y-2">
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  {task.subtasks_completed}/{task.subtasks_count} шагов
                </span>
                <span>{task.progress_percent}%</span>
              </div>
              <Progress
                value={task.progress_percent}
                size="sm"
                color={isCompleted ? 'success' : hasActiveSession ? 'primary' : 'primary'}
              />
            </div>
          )}
        </div>

        {!hasActiveSession && (
          <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
        )}
      </div>
    </Card>
  );
}
