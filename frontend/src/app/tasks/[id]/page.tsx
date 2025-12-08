'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Wand2, Trash2, Plus } from 'lucide-react';
import { Button, Card, Modal, Progress } from '@/components/ui';
import { SubtaskItem } from '@/components/tasks';
import { MoodSelector } from '@/components/mood';
import { tasksService, focusService, moodService } from '@/services';
import { useAppStore } from '@/lib/store';
import { hapticFeedback } from '@/lib/telegram';
import { PRIORITY_COLORS } from '@/domain/constants';
import type { MoodLevel, EnergyLevel } from '@/domain/types';

export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const taskId = Number(params.id);

  const { latestMood, setLatestMood, setActiveSession, showXPAnimation } = useAppStore();
  const [showMoodModal, setShowMoodModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showAddSubtask, setShowAddSubtask] = useState(false);
  const [newSubtaskTitle, setNewSubtaskTitle] = useState('');
  const [moodLoading, setMoodLoading] = useState(false);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => tasksService.getTask(taskId),
    enabled: !!taskId,
  });

  const decomposeMutation = useMutation({
    mutationFn: (moodId?: number) => tasksService.decomposeTask(taskId, moodId),
    onSuccess: () => {
      refetch();
      hapticFeedback('success');
    },
  });

  const toggleSubtaskMutation = useMutation({
    mutationFn: ({ subtaskId, completed }: { subtaskId: number; completed: boolean }) =>
      tasksService.updateSubtask(subtaskId, {
        status: completed ? 'completed' : 'pending',
      }),
    onSuccess: (result) => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['user', 'stats'] });
      queryClient.invalidateQueries({ queryKey: ['daily', 'goals'] });
      if (result.data?.xp_earned) {
        showXPAnimation(result.data.xp_earned);
      }
      hapticFeedback('success');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => tasksService.deleteTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      router.push('/tasks');
      hapticFeedback('success');
    },
  });

  const createSubtaskMutation = useMutation({
    mutationFn: (title: string) => tasksService.createSubtask(taskId, { title }),
    onSuccess: () => {
      refetch();
      setShowAddSubtask(false);
      setNewSubtaskTitle('');
      hapticFeedback('success');
    },
  });

  const startFocusMutation = useMutation({
    mutationFn: (subtaskId: number) =>
      focusService.startSession({
        subtask_id: subtaskId,
        planned_duration_minutes: 25,
      }),
    onSuccess: (result) => {
      if (result.success && result.data) {
        setActiveSession(result.data.session);
        router.push('/focus');
        hapticFeedback('success');
      }
    },
  });

  const handleDecompose = () => {
    if (!latestMood) {
      setShowMoodModal(true);
    } else {
      decomposeMutation.mutate(latestMood.id);
    }
  };

  const handleMoodSubmit = async (mood: MoodLevel, energy: EnergyLevel, note?: string) => {
    setMoodLoading(true);
    try {
      const result = await moodService.createMoodCheck({ mood, energy, note });
      if (result.success && result.data) {
        setLatestMood(result.data.mood_check);
        setShowMoodModal(false);
        // Now decompose with the new mood
        decomposeMutation.mutate(result.data.mood_check.id);
        if (result.data.xp_earned) {
          showXPAnimation(result.data.xp_earned);
        }
      }
    } finally {
      setMoodLoading(false);
    }
  };

  const task = data?.data?.task;

  if (isLoading) {
    return (
      <div className="p-4">
        <Card className="h-32 animate-pulse bg-gray-100" />
      </div>
    );
  }

  if (!task) {
    return (
      <div className="p-4 text-center">
        <p className="text-gray-500">Задача не найдена</p>
        <Button onClick={() => router.push('/tasks')} className="mt-4">
          Назад к задачам
        </Button>
      </div>
    );
  }

  const subtasks = task.subtasks || [];

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.push('/tasks')}
          className="p-2 -ml-2 hover:bg-gray-700 rounded-full"
        >
          <ArrowLeft className="w-5 h-5 text-white" />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-lg font-bold text-white truncate">{task.title}</h1>
        </div>
        <button
          onClick={() => setShowDeleteConfirm(true)}
          className="p-2 hover:bg-red-50 rounded-full text-gray-400 hover:text-red-500"
        >
          <Trash2 className="w-5 h-5" />
        </button>
      </div>

      {/* Task Info */}
      <Card>
        <div className="flex items-center justify-between mb-3">
          <span className={`text-xs px-2 py-0.5 rounded-full ${PRIORITY_COLORS[task.priority]}`}>
            {task.priority === 'low' ? 'Низкий' : task.priority === 'medium' ? 'Средний' : 'Высокий'}
          </span>
          <span className="text-sm text-gray-500">
            {task.progress_percent}% выполнено
          </span>
        </div>
        <Progress value={task.progress_percent} color="primary" />
        {task.description && (
          <p className="text-sm text-gray-400 mt-3">{task.description}</p>
        )}
      </Card>

      {/* Decompose Button */}
      {subtasks.length === 0 && (
        <Button
          onClick={handleDecompose}
          isLoading={decomposeMutation.isPending}
          className="w-full"
        >
          <Wand2 className="w-4 h-4 mr-2" />
          Разбить на шаги с ИИ
        </Button>
      )}

      {/* Subtasks */}
      {subtasks.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-white">Шаги</h2>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowAddSubtask(true)}
                className="text-sm text-primary-500 hover:text-primary-600 flex items-center gap-1"
              >
                <Plus className="w-4 h-4" />
                Добавить
              </button>
              <button
                onClick={handleDecompose}
                className="text-sm text-gray-400 hover:text-gray-300 flex items-center gap-1"
              >
                <Wand2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="space-y-2">
            {subtasks.map((subtask) => (
              <SubtaskItem
                key={subtask.id}
                subtask={subtask}
                onToggle={() =>
                  toggleSubtaskMutation.mutate({
                    subtaskId: subtask.id,
                    completed: subtask.status !== 'completed',
                  })
                }
                onFocus={() => startFocusMutation.mutate(subtask.id)}
                disabled={toggleSubtaskMutation.isPending}
              />
            ))}
          </div>
        </div>
      )}

      {/* Add Subtask when no subtasks exist */}
      {subtasks.length === 0 && (
        <Button
          variant="secondary"
          onClick={() => setShowAddSubtask(true)}
          className="w-full mt-2"
        >
          <Plus className="w-4 h-4 mr-2" />
          Добавить шаг вручную
        </Button>
      )}

      {/* Mood Modal */}
      <Modal
        isOpen={showMoodModal}
        onClose={() => setShowMoodModal(false)}
        title="Сначала отметь настроение"
      >
        <p className="text-sm text-gray-500 mb-4">
          Мы подстроим разбивку задачи под твоё текущее состояние.
        </p>
        <MoodSelector onSubmit={handleMoodSubmit} isLoading={moodLoading} />
      </Modal>

      {/* Delete Confirmation */}
      <Modal
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        title="Удалить задачу"
      >
        <p className="text-gray-600 mb-4">
          Ты уверен, что хочешь удалить «{task.title}»? Это нельзя отменить.
        </p>
        <div className="flex gap-3">
          <Button
            variant="secondary"
            onClick={() => setShowDeleteConfirm(false)}
            className="flex-1"
          >
            Отмена
          </Button>
          <Button
            variant="danger"
            onClick={() => deleteMutation.mutate()}
            isLoading={deleteMutation.isPending}
            className="flex-1"
          >
            Удалить
          </Button>
        </div>
      </Modal>

      {/* Add Subtask Modal */}
      <Modal
        isOpen={showAddSubtask}
        onClose={() => {
          setShowAddSubtask(false);
          setNewSubtaskTitle('');
        }}
        title="Добавить шаг"
      >
        <div className="space-y-4">
          <input
            type="text"
            value={newSubtaskTitle}
            onChange={(e) => setNewSubtaskTitle(e.target.value)}
            placeholder="Название шага"
            className="w-full p-3 bg-gray-800 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
            autoFocus
          />
          <div className="flex gap-3">
            <Button
              variant="secondary"
              onClick={() => {
                setShowAddSubtask(false);
                setNewSubtaskTitle('');
              }}
              className="flex-1"
            >
              Отмена
            </Button>
            <Button
              onClick={() => createSubtaskMutation.mutate(newSubtaskTitle)}
              isLoading={createSubtaskMutation.isPending}
              disabled={!newSubtaskTitle.trim()}
              className="flex-1"
            >
              Добавить
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
