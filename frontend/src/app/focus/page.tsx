'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Play, Clock, Target } from 'lucide-react';
import { Button, Card, Modal } from '@/components/ui';
import { FocusTimer } from '@/components/focus';
import { useAppStore } from '@/lib/store';
import { focusService, tasksService } from '@/services';
import { hapticFeedback } from '@/lib/telegram';
import { DEFAULT_FOCUS_DURATION } from '@/domain/constants';
import type { Subtask } from '@/domain/types';

export default function FocusPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { activeSession, setActiveSession, showXPAnimation } = useAppStore();
  const [showSelectSubtask, setShowSelectSubtask] = useState(false);
  const [duration, setDuration] = useState(DEFAULT_FOCUS_DURATION);

  const { data: tasksData } = useQuery({
    queryKey: ['tasks', 'in_progress'],
    queryFn: () => tasksService.getTasks({ status: 'in_progress' }),
  });

  const { data: historyData } = useQuery({
    queryKey: ['focus', 'history'],
    queryFn: () => focusService.getHistory({ limit: 5 }),
  });

  const startMutation = useMutation({
    mutationFn: (subtaskId?: number) =>
      focusService.startSession({
        subtask_id: subtaskId,
        planned_duration_minutes: duration,
      }),
    onSuccess: (result) => {
      if (result.success && result.data) {
        setActiveSession(result.data.session);
        setShowSelectSubtask(false);
        hapticFeedback('success');
      }
    },
  });

  const completeMutation = useMutation({
    mutationFn: (completeSubtask: boolean) =>
      focusService.completeSession(activeSession?.id, completeSubtask),
    onSuccess: (result) => {
      setActiveSession(null);
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
      queryClient.invalidateQueries({ queryKey: ['focus'] });
      hapticFeedback('light');
    },
  });

  const pauseMutation = useMutation({
    mutationFn: () => focusService.pauseSession(),
    onSuccess: (result) => {
      if (result.success && result.data?.session) {
        setActiveSession(result.data.session);
      }
    },
  });

  const resumeMutation = useMutation({
    mutationFn: () => focusService.resumeSession(),
    onSuccess: (result) => {
      if (result.success && result.data?.session) {
        setActiveSession(result.data.session);
      }
    },
  });

  // Get all pending subtasks from active tasks
  const availableSubtasks: (Subtask & { taskTitle: string })[] = [];
  tasksData?.data?.tasks?.forEach((task) => {
    task.subtasks?.forEach((subtask) => {
      if (subtask.status !== 'completed') {
        availableSubtasks.push({ ...subtask, taskTitle: task.title });
      }
    });
  });

  const durations = [15, 25, 45, 60];
  const history = historyData?.data?.sessions || [];

  // Active session view
  if (activeSession) {
    return (
      <FocusTimer
        session={activeSession}
        onComplete={(completeSubtask) => completeMutation.mutate(completeSubtask)}
        onCancel={() => cancelMutation.mutate()}
        onPause={() => pauseMutation.mutate()}
        onResume={() => resumeMutation.mutate()}
      />
    );
  }

  return (
    <div className="p-4 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-gray-900">Focus Session</h1>
        <p className="text-sm text-gray-500">Concentrate on one task at a time</p>
      </div>

      {/* Duration Selector */}
      <Card>
        <h3 className="font-medium text-gray-900 mb-3">Session Duration</h3>
        <div className="flex gap-2">
          {durations.map((d) => (
            <button
              key={d}
              onClick={() => setDuration(d)}
              className={`flex-1 py-3 rounded-xl text-sm font-medium transition-all ${
                duration === d
                  ? 'bg-primary-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {d} min
            </button>
          ))}
        </div>
      </Card>

      {/* Start Buttons */}
      <div className="space-y-3">
        {availableSubtasks.length > 0 ? (
          <Button
            onClick={() => setShowSelectSubtask(true)}
            className="w-full h-14"
            size="lg"
          >
            <Target className="w-5 h-5 mr-2" />
            Start with a task
          </Button>
        ) : (
          <Button
            onClick={() => startMutation.mutate(undefined)}
            isLoading={startMutation.isPending}
            className="w-full h-14"
            size="lg"
          >
            <Play className="w-5 h-5 mr-2" />
            Start Free Focus
          </Button>
        )}

        {availableSubtasks.length > 0 && (
          <Button
            variant="secondary"
            onClick={() => startMutation.mutate(undefined)}
            isLoading={startMutation.isPending}
            className="w-full"
          >
            Start without task
          </Button>
        )}
      </div>

      {/* Recent Sessions */}
      {history.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-medium text-gray-900">Recent Sessions</h3>
          <div className="space-y-2">
            {history.map((session) => (
              <Card key={session.id} padding="sm" className="flex items-center gap-3">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    session.status === 'completed'
                      ? 'bg-green-100 text-green-600'
                      : 'bg-gray-100 text-gray-400'
                  }`}
                >
                  <Clock className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">
                    {session.subtask_title || 'Free focus'}
                  </p>
                  <p className="text-xs text-gray-500">
                    {session.actual_duration_minutes} min
                  </p>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Select Subtask Modal */}
      <Modal
        isOpen={showSelectSubtask}
        onClose={() => setShowSelectSubtask(false)}
        title="Choose a step"
      >
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {availableSubtasks.map((subtask) => (
            <button
              key={subtask.id}
              onClick={() => startMutation.mutate(subtask.id)}
              className="w-full p-3 text-left rounded-xl bg-gray-50 hover:bg-gray-100 transition-colors"
            >
              <p className="font-medium text-gray-900">{subtask.title}</p>
              <p className="text-xs text-gray-500 mt-0.5">{subtask.taskTitle}</p>
            </button>
          ))}
        </div>
      </Modal>
    </div>
  );
}
