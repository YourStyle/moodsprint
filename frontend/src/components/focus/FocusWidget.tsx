'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Play, Pause, X, Check, Plus, Timer } from 'lucide-react';
import { Modal, Button } from '@/components/ui';
import { useAppStore } from '@/lib/store';
import { focusService } from '@/services';
import { hapticFeedback } from '@/lib/telegram';
import type { FocusSession } from '@/domain/types';

function calculateElapsedSeconds(session: FocusSession): number {
  const startedAt = new Date(session.started_at).getTime();
  const now = Date.now();
  const elapsedMs = now - startedAt;
  return Math.floor(elapsedMs / 1000);
}

export function FocusWidget() {
  const queryClient = useQueryClient();
  const { activeSession, setActiveSession, showXPAnimation } = useAppStore();
  const [showModal, setShowModal] = useState(false);
  const [showAddTimeModal, setShowAddTimeModal] = useState(false);

  const initialElapsed = useMemo(() => {
    if (!activeSession) return 0;
    if (activeSession.status === 'paused') {
      return activeSession.elapsed_minutes * 60;
    }
    return calculateElapsedSeconds(activeSession);
  }, [activeSession?.started_at, activeSession?.status, activeSession?.elapsed_minutes]);

  const [elapsed, setElapsed] = useState(initialElapsed);
  const isPaused = activeSession?.status === 'paused';
  const planned = (activeSession?.planned_duration_minutes || 25) * 60;

  useEffect(() => {
    setElapsed(initialElapsed);
  }, [initialElapsed]);

  useEffect(() => {
    if (!activeSession || isPaused) return;

    const interval = setInterval(() => {
      setElapsed(calculateElapsedSeconds(activeSession));
    }, 1000);

    return () => clearInterval(interval);
  }, [activeSession, isPaused]);

  const formatTime = useCallback((seconds: number) => {
    const mins = Math.floor(Math.abs(seconds) / 60);
    const secs = Math.abs(seconds) % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }, []);

  const completeMutation = useMutation({
    mutationFn: (completeSubtask: boolean) =>
      focusService.completeSession(activeSession?.id, completeSubtask),
    onSuccess: (result) => {
      setActiveSession(null);
      setShowModal(false);
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['focus'] });
      queryClient.invalidateQueries({ queryKey: ['user', 'stats'] });
      queryClient.invalidateQueries({ queryKey: ['daily', 'goals'] });
      if (result.data?.xp_earned) {
        showXPAnimation(result.data.xp_earned);
      }
      hapticFeedback('success');
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => focusService.cancelSession(activeSession?.id),
    onSuccess: () => {
      setActiveSession(null);
      setShowModal(false);
      queryClient.invalidateQueries({ queryKey: ['focus'] });
      hapticFeedback('light');
    },
  });

  const pauseMutation = useMutation({
    mutationFn: () => focusService.pauseSession(),
    onSuccess: (result) => {
      if (result.success && result.data?.session) {
        setActiveSession(result.data.session);
        queryClient.invalidateQueries({ queryKey: ['focus', 'active'] });
      }
    },
  });

  const resumeMutation = useMutation({
    mutationFn: () => focusService.resumeSession(),
    onSuccess: (result) => {
      if (result.success && result.data?.session) {
        setActiveSession(result.data.session);
        queryClient.invalidateQueries({ queryKey: ['focus', 'active'] });
      }
    },
  });

  const extendMutation = useMutation({
    mutationFn: (minutes: number) => focusService.extendSession(minutes),
    onSuccess: (result) => {
      if (result.success && result.data?.session) {
        setActiveSession(result.data.session);
        setShowAddTimeModal(false);
        queryClient.invalidateQueries({ queryKey: ['focus', 'active'] });
        hapticFeedback('success');
      }
    },
  });

  if (!activeSession) return null;

  const isNoTimerMode = activeSession.planned_duration_minutes >= 480;
  const remaining = planned - elapsed;
  const isOvertime = !isNoTimerMode && remaining < 0;
  const progress = isNoTimerMode ? 0 : Math.min(100, (elapsed / planned) * 100);

  return (
    <>
      {/* Floating Widget */}
      <button
        onClick={() => setShowModal(true)}
        className={`fixed bottom-24 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-2xl shadow-lg backdrop-blur-sm transition-all ${
          isOvertime
            ? 'bg-red-500/90 text-white animate-pulse'
            : isPaused
            ? 'bg-yellow-500/90 text-white'
            : 'bg-primary-500/90 text-white'
        }`}
      >
        <div className="relative w-10 h-10">
          <svg className="w-full h-full transform -rotate-90">
            <circle
              cx="20"
              cy="20"
              r="16"
              stroke="currentColor"
              strokeWidth="3"
              fill="none"
              className="opacity-30"
            />
            {!isNoTimerMode && (
              <circle
                cx="20"
                cy="20"
                r="16"
                stroke="currentColor"
                strokeWidth="3"
                fill="none"
                strokeLinecap="round"
                strokeDasharray={2 * Math.PI * 16}
                strokeDashoffset={2 * Math.PI * 16 * (1 - progress / 100)}
                className="transition-all duration-1000"
              />
            )}
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            {isPaused ? (
              <Pause className="w-4 h-4" />
            ) : (
              <Timer className="w-4 h-4" />
            )}
          </div>
        </div>
        <div className="text-left">
          <p className={`text-lg font-bold tabular-nums ${isOvertime ? 'text-white' : ''}`}>
            {isOvertime && '+'}
            {isNoTimerMode
              ? formatTime(elapsed)
              : formatTime(isOvertime ? -remaining : remaining)}
          </p>
          <p className="text-xs opacity-80 truncate max-w-[100px]">
            {activeSession.subtask_title || activeSession.task_title || 'Фокус'}
          </p>
        </div>
      </button>

      {/* Session Control Modal */}
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title="Фокус-сессия"
      >
        <div className="space-y-4">
          {/* Current task info */}
          <div className="text-center p-4 bg-gray-800 rounded-xl">
            <p className="text-3xl font-bold tabular-nums text-white mb-1">
              {isOvertime && '+'}
              {isNoTimerMode
                ? formatTime(elapsed)
                : formatTime(isOvertime ? -remaining : remaining)}
            </p>
            <p className="text-sm text-gray-400">
              {activeSession.subtask_title || activeSession.task_title || 'Свободный фокус'}
            </p>
          </div>

          {/* Pause/Resume button */}
          <Button
            variant="secondary"
            onClick={() => isPaused ? resumeMutation.mutate() : pauseMutation.mutate()}
            isLoading={pauseMutation.isPending || resumeMutation.isPending}
            className="w-full"
          >
            {isPaused ? (
              <>
                <Play className="w-4 h-4 mr-2" />
                Продолжить
              </>
            ) : (
              <>
                <Pause className="w-4 h-4 mr-2" />
                Пауза
              </>
            )}
          </Button>

          {/* Add time button */}
          {!isNoTimerMode && (
            <Button
              variant="secondary"
              onClick={() => setShowAddTimeModal(true)}
              className="w-full"
            >
              <Plus className="w-4 h-4 mr-2" />
              Добавить время
            </Button>
          )}

          {/* Complete task button */}
          <Button
            variant="primary"
            onClick={() => completeMutation.mutate(true)}
            isLoading={completeMutation.isPending}
            className="w-full bg-green-500 hover:bg-green-600"
          >
            <Check className="w-4 h-4 mr-2" />
            Завершить задачу
          </Button>

          {/* Cancel button */}
          <Button
            variant="ghost"
            onClick={() => cancelMutation.mutate()}
            isLoading={cancelMutation.isPending}
            className="w-full text-red-400 hover:text-red-300 hover:bg-red-500/10"
          >
            <X className="w-4 h-4 mr-2" />
            Отменить сессию
          </Button>
        </div>
      </Modal>

      {/* Add Time Modal */}
      <Modal
        isOpen={showAddTimeModal}
        onClose={() => setShowAddTimeModal(false)}
        title="Добавить время"
      >
        <div className="grid grid-cols-2 gap-3">
          {[5, 10, 15, 25].map((mins) => (
            <Button
              key={mins}
              variant="secondary"
              onClick={() => extendMutation.mutate(mins)}
              isLoading={extendMutation.isPending}
              className="py-4"
            >
              +{mins} мин
            </Button>
          ))}
        </div>
      </Modal>
    </>
  );
}
