'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Wand2, Trash2, Plus, Play, Check, Timer, Infinity, Pencil, Sparkles, Heart, Swords, ChevronUp, ChevronDown } from 'lucide-react';
import { Button, Card, Modal, Progress } from '@/components/ui';
import { SubtaskItem } from '@/components/tasks';
import { MoodSelector } from '@/components/mood';
import { tasksService, focusService, moodService } from '@/services';
import { useAppStore } from '@/lib/store';
import { hapticFeedback, showBackButton, hideBackButton } from '@/lib/telegram';
import { PRIORITY_COLORS, TASK_TYPE_EMOJIS, TASK_TYPE_LABELS, TASK_TYPE_COLORS, DEFAULT_FOCUS_DURATION } from '@/domain/constants';
import type { MoodLevel, EnergyLevel, TaskType } from '@/domain/types';

// Card type for earned card modal
interface EarnedCard {
  id: number;
  name: string;
  description: string;
  genre: string;
  rarity: string;
  hp: number;
  attack: number;
  emoji: string;
  image_url?: string | null;
}

// Rarity colors and labels
const RARITY_COLORS: Record<string, string> = {
  common: 'from-gray-500 to-gray-600',
  uncommon: 'from-green-500 to-green-600',
  rare: 'from-blue-500 to-blue-600',
  epic: 'from-purple-500 to-purple-600',
  legendary: 'from-yellow-500 to-orange-500',
};

const RARITY_LABELS: Record<string, string> = {
  common: 'Обычная',
  uncommon: 'Необычная',
  rare: 'Редкая',
  epic: 'Эпическая',
  legendary: 'Легендарная',
};

const TASK_TYPES: TaskType[] = [
  'creative', 'analytical', 'communication', 'physical',
  'learning', 'planning', 'coding', 'writing'
];

export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const taskId = Number(params.id);

  const { latestMood, setLatestMood, setActiveSession, showXPAnimation } = useAppStore();
  const [showMoodModal, setShowMoodModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showAddSubtask, setShowAddSubtask] = useState(false);
  const [showTypeModal, setShowTypeModal] = useState(false);
  const [showDurationModal, setShowDurationModal] = useState(false);
  const [pendingFocusSubtaskId, setPendingFocusSubtaskId] = useState<number | null>(null);
  const [selectedDuration, setSelectedDuration] = useState<number | null>(DEFAULT_FOCUS_DURATION);
  const [newSubtaskTitle, setNewSubtaskTitle] = useState('');
  const [moodLoading, setMoodLoading] = useState(false);
  const [showEditTask, setShowEditTask] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [showEditSubtask, setShowEditSubtask] = useState(false);
  const [editingSubtask, setEditingSubtask] = useState<{ id: number; title: string; estimated_minutes: number } | null>(null);
  const [earnedCard, setEarnedCard] = useState<EarnedCard | null>(null);
  const [showCardModal, setShowCardModal] = useState(false);
  const [showPriorityModal, setShowPriorityModal] = useState(false);

  // Show Telegram back button
  useEffect(() => {
    const handleBack = () => {
      router.push('/tasks');
    };
    showBackButton(handleBack);
    return () => {
      hideBackButton();
    };
  }, [router]);

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
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      if (result.data?.xp_earned) {
        showXPAnimation(result.data.xp_earned);
      }
      // Show card earned modal if card was generated
      if (result.data?.card_earned) {
        setEarnedCard(result.data.card_earned);
        setShowCardModal(true);
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
    mutationFn: ({ subtaskId, duration }: { subtaskId: number; duration: number | null }) =>
      focusService.startSession({
        subtask_id: subtaskId,
        // null duration means "work without timer" - use very long duration
        planned_duration_minutes: duration ?? 480,
      }),
    onSuccess: (result) => {
      if (result.success && result.data) {
        setActiveSession(result.data.session);
        setShowDurationModal(false);
        setPendingFocusSubtaskId(null);
        router.push('/focus');
        hapticFeedback('success');
      }
    },
  });

  const startTaskFocusMutation = useMutation({
    mutationFn: (duration: number | null) =>
      focusService.startSession({
        task_id: taskId,
        // null duration means "work without timer" - use very long duration
        planned_duration_minutes: duration ?? 480,
      }),
    onSuccess: (result) => {
      if (result.success && result.data) {
        setActiveSession(result.data.session);
        setShowDurationModal(false);
        router.push('/focus');
        hapticFeedback('success');
      }
    },
  });

  // Open duration modal before starting focus
  const handleStartFocus = (subtaskId?: number) => {
    setPendingFocusSubtaskId(subtaskId ?? null);
    setSelectedDuration(DEFAULT_FOCUS_DURATION);
    setShowDurationModal(true);
  };

  // Confirm duration and start focus
  const confirmStartFocus = () => {
    if (pendingFocusSubtaskId !== null) {
      startFocusMutation.mutate({ subtaskId: pendingFocusSubtaskId, duration: selectedDuration });
    } else {
      startTaskFocusMutation.mutate(selectedDuration);
    }
  };

  const completeTaskMutation = useMutation({
    mutationFn: () =>
      tasksService.updateTask(taskId, { status: 'completed' }),
    onSuccess: (result) => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['user', 'stats'] });
      queryClient.invalidateQueries({ queryKey: ['daily', 'goals'] });
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      if (result.data?.xp_earned) {
        showXPAnimation(result.data.xp_earned);
      }
      // Show card earned modal if card was generated
      if (result.data?.card_earned) {
        setEarnedCard(result.data.card_earned);
        setShowCardModal(true);
      }
      hapticFeedback('success');
    },
  });

  const updateTypeMutation = useMutation({
    mutationFn: (taskType: TaskType) =>
      tasksService.updateTask(taskId, { task_type: taskType }),
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setShowTypeModal(false);
      hapticFeedback('success');
    },
  });

  const updatePriorityMutation = useMutation({
    mutationFn: (priority: 'low' | 'medium' | 'high') =>
      tasksService.updateTask(taskId, { priority }),
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setShowPriorityModal(false);
      hapticFeedback('success');
    },
  });

  const updateTaskMutation = useMutation({
    mutationFn: (data: { title?: string; description?: string }) =>
      tasksService.updateTask(taskId, data),
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setShowEditTask(false);
      hapticFeedback('success');
    },
  });

  const updateSubtaskMutation = useMutation({
    mutationFn: ({ subtaskId, data }: { subtaskId: number; data: { title?: string; estimated_minutes?: number } }) =>
      tasksService.updateSubtask(subtaskId, data),
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setShowEditSubtask(false);
      setEditingSubtask(null);
      hapticFeedback('success');
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
        <Card className="h-32 animate-pulse" />
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
    <div className="p-4 space-y-4 pt-safe">
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
          onClick={() => {
            setEditTitle(task.title);
            setEditDescription(task.description || '');
            setShowEditTask(true);
          }}
          className="p-2 hover:bg-gray-700 rounded-full text-gray-400 hover:text-white"
        >
          <Pencil className="w-5 h-5" />
        </button>
        <button
          onClick={() => setShowDeleteConfirm(true)}
          className="p-2 hover:bg-red-500/20 rounded-full text-gray-400 hover:text-red-500"
        >
          <Trash2 className="w-5 h-5" />
        </button>
      </div>

      {/* Task Info */}
      <Card>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            {task.task_type && (
              <button
                onClick={() => setShowTypeModal(true)}
                className={`text-xs px-2 py-0.5 rounded-full transition-opacity hover:opacity-80 ${TASK_TYPE_COLORS[task.task_type]}`}
              >
                {TASK_TYPE_EMOJIS[task.task_type]} {TASK_TYPE_LABELS[task.task_type]}
              </button>
            )}
            {!task.task_type && (
              <button
                onClick={() => setShowTypeModal(true)}
                className="text-xs px-2 py-0.5 rounded-full bg-gray-600/50 text-gray-400 border border-dashed border-gray-500 hover:bg-gray-600"
              >
                + Тип
              </button>
            )}
            <button
              onClick={() => setShowPriorityModal(true)}
              className={`text-xs px-2 py-0.5 rounded-full transition-opacity hover:opacity-80 ${PRIORITY_COLORS[task.priority]}`}
            >
              {task.priority === 'low' ? 'Низкий' : task.priority === 'medium' ? 'Средний' : 'Высокий'}
            </button>
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              task.status === 'completed'
                ? 'bg-green-500/20 text-green-400'
                : task.status === 'in_progress'
                ? 'bg-blue-500/20 text-blue-400'
                : 'bg-gray-500/20 text-gray-400'
            }`}>
              {task.status === 'completed' ? 'Выполнена' : task.status === 'in_progress' ? 'В работе' : 'Ожидает'}
            </span>
          </div>
          <span className="text-sm text-gray-500">
            {task.progress_percent}% выполнено
          </span>
        </div>
        <Progress value={task.progress_percent} color="primary" />
      </Card>

      {/* Action Buttons */}
      {task.status !== 'completed' && (
        <div className="flex gap-3">
          <Button
            variant="primary"
            onClick={() => handleStartFocus()}
            isLoading={startTaskFocusMutation.isPending}
            className="flex-1"
          >
            <Play className="w-4 h-4 mr-2" />
            Начать фокус
          </Button>
          <Button
            variant="secondary"
            onClick={() => completeTaskMutation.mutate()}
            isLoading={completeTaskMutation.isPending}
            className="flex-1"
          >
            <Check className="w-4 h-4 mr-2" />
            Завершить
          </Button>
        </div>
      )}

      {/* Decompose Button */}
      {subtasks.length === 0 && task.status !== 'completed' && (
        <Button
          onClick={handleDecompose}
          isLoading={decomposeMutation.isPending}
          className="w-full"
        >
          <Wand2 className="w-4 h-4 mr-2" />
          Разбить на шаги с ИИ
        </Button>
      )}

      {/* Description */}
      {task.description && (
        <div className="bg-gray-800/50 rounded-xl p-3">
          <p className="text-sm text-gray-300 whitespace-pre-wrap">{task.description}</p>
        </div>
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
                onFocus={() => handleStartFocus(subtask.id)}
                onEdit={() => {
                  setEditingSubtask({
                    id: subtask.id,
                    title: subtask.title,
                    estimated_minutes: subtask.estimated_minutes,
                  });
                  setShowEditSubtask(true);
                }}
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

      {/* Edit Task Modal */}
      <Modal
        isOpen={showEditTask}
        onClose={() => setShowEditTask(false)}
        title="Редактировать задачу"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Название
            </label>
            <input
              type="text"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              placeholder="Название задачи"
              className="w-full p-3 bg-gray-800 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Описание
            </label>
            <textarea
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              placeholder="Описание задачи (необязательно)"
              rows={4}
              className="w-full p-3 bg-gray-800 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
            />
          </div>
          <div className="flex gap-3">
            <Button
              variant="secondary"
              onClick={() => setShowEditTask(false)}
              className="flex-1"
            >
              Отмена
            </Button>
            <Button
              onClick={() => updateTaskMutation.mutate({
                title: editTitle.trim(),
                description: editDescription.trim() || undefined,
              })}
              isLoading={updateTaskMutation.isPending}
              disabled={!editTitle.trim()}
              className="flex-1"
            >
              Сохранить
            </Button>
          </div>
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

      {/* Edit Subtask Modal */}
      <Modal
        isOpen={showEditSubtask}
        onClose={() => {
          setShowEditSubtask(false);
          setEditingSubtask(null);
        }}
        title="Редактировать шаг"
      >
        {editingSubtask && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Название
              </label>
              <input
                type="text"
                value={editingSubtask.title}
                onChange={(e) => setEditingSubtask({ ...editingSubtask, title: e.target.value })}
                placeholder="Название шага"
                className="w-full p-3 bg-gray-800 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                autoFocus
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Время (минуты)
              </label>
              <input
                type="number"
                min={1}
                max={480}
                value={editingSubtask.estimated_minutes}
                onChange={(e) => setEditingSubtask({ ...editingSubtask, estimated_minutes: Math.max(1, parseInt(e.target.value) || 1) })}
                className="w-full p-3 bg-gray-800 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div className="flex gap-3">
              <Button
                variant="secondary"
                onClick={() => {
                  setShowEditSubtask(false);
                  setEditingSubtask(null);
                }}
                className="flex-1"
              >
                Отмена
              </Button>
              <Button
                onClick={() => updateSubtaskMutation.mutate({
                  subtaskId: editingSubtask.id,
                  data: {
                    title: editingSubtask.title.trim(),
                    estimated_minutes: editingSubtask.estimated_minutes,
                  },
                })}
                isLoading={updateSubtaskMutation.isPending}
                disabled={!editingSubtask.title.trim()}
                className="flex-1"
              >
                Сохранить
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Task Type Modal */}
      <Modal
        isOpen={showTypeModal}
        onClose={() => setShowTypeModal(false)}
        title="Тип задачи"
      >
        <p className="text-sm text-gray-500 mb-4">
          Выбери тип задачи для более точной разбивки на шаги
        </p>
        <div className="grid grid-cols-2 gap-2">
          {TASK_TYPES.map((type) => (
            <button
              key={type}
              onClick={() => updateTypeMutation.mutate(type)}
              disabled={updateTypeMutation.isPending}
              className={`p-3 rounded-xl text-left transition-all ${
                task.task_type === type
                  ? `${TASK_TYPE_COLORS[type]} ring-2 ring-offset-2 ring-offset-gray-900`
                  : 'bg-gray-800 hover:bg-gray-700 text-gray-300'
              }`}
            >
              <span className="text-lg mr-2">{TASK_TYPE_EMOJIS[type]}</span>
              <span className="text-sm font-medium">{TASK_TYPE_LABELS[type]}</span>
            </button>
          ))}
        </div>
      </Modal>

      {/* Duration Selection Modal */}
      <Modal
        isOpen={showDurationModal}
        onClose={() => {
          setShowDurationModal(false);
          setPendingFocusSubtaskId(null);
        }}
        title="Выбери длительность"
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-2">
            {[15, 25, 45, 60].map((d) => (
              <button
                key={d}
                onClick={() => setSelectedDuration(d)}
                className={`p-3 rounded-xl text-center transition-all ${
                  selectedDuration === d
                    ? 'bg-primary-500 text-white ring-2 ring-primary-500 ring-offset-2 ring-offset-gray-900'
                    : 'bg-gray-800 hover:bg-gray-700 text-gray-300'
                }`}
              >
                <Timer className="w-5 h-5 mx-auto mb-1" />
                <span className="text-sm font-medium">{d} мин</span>
              </button>
            ))}
          </div>

          <button
            onClick={() => setSelectedDuration(null)}
            className={`w-full p-3 rounded-xl text-center transition-all ${
              selectedDuration === null
                ? 'bg-primary-500 text-white ring-2 ring-primary-500 ring-offset-2 ring-offset-gray-900'
                : 'bg-gray-800 hover:bg-gray-700 text-gray-300'
            }`}
          >
            <Infinity className="w-5 h-5 mx-auto mb-1" />
            <span className="text-sm font-medium">Без таймера</span>
          </button>

          <Button
            onClick={confirmStartFocus}
            isLoading={startFocusMutation.isPending || startTaskFocusMutation.isPending}
            className="w-full"
          >
            <Play className="w-4 h-4 mr-2" />
            Начать
          </Button>
        </div>
      </Modal>

      {/* Priority Modal */}
      <Modal
        isOpen={showPriorityModal}
        onClose={() => setShowPriorityModal(false)}
        title="Приоритет задачи"
      >
        <div className="space-y-2">
          {([
            { value: 'high' as const, label: 'Высокий', icon: <ChevronUp className="w-4 h-4" /> },
            { value: 'medium' as const, label: 'Средний', icon: null },
            { value: 'low' as const, label: 'Низкий', icon: <ChevronDown className="w-4 h-4" /> },
          ]).map((priority) => (
            <button
              key={priority.value}
              onClick={() => updatePriorityMutation.mutate(priority.value)}
              disabled={updatePriorityMutation.isPending}
              className={`w-full p-3 rounded-xl text-left flex items-center gap-3 transition-all ${
                task.priority === priority.value
                  ? `${PRIORITY_COLORS[priority.value]} ring-2 ring-offset-2 ring-offset-gray-900`
                  : 'bg-gray-800 hover:bg-gray-700 text-gray-300'
              }`}
            >
              <span className={`w-8 h-8 rounded-full flex items-center justify-center ${PRIORITY_COLORS[priority.value]}`}>
                {priority.icon || <span className="w-2 h-2 rounded-full bg-current" />}
              </span>
              <span className="font-medium">{priority.label}</span>
            </button>
          ))}
        </div>
      </Modal>

      {/* Card Earned Modal */}
      <Modal
        isOpen={showCardModal}
        onClose={() => {
          setShowCardModal(false);
          setEarnedCard(null);
        }}
        title="Новая карта!"
      >
        {earnedCard && (
          <div className="space-y-4">
            {/* Card Preview */}
            <div className={`relative rounded-2xl p-4 bg-gradient-to-br ${RARITY_COLORS[earnedCard.rarity] || RARITY_COLORS.common} overflow-hidden`}>
              {/* Sparkle effect for rare cards */}
              {['rare', 'epic', 'legendary'].includes(earnedCard.rarity) && (
                <div className="absolute inset-0 overflow-hidden">
                  <Sparkles className="absolute top-2 right-2 w-6 h-6 text-white/30 animate-pulse" />
                  <Sparkles className="absolute bottom-4 left-4 w-4 h-4 text-white/20 animate-pulse delay-300" />
                </div>
              )}

              <div className="relative z-10 text-center">
                {/* Card Image or Emoji */}
                {earnedCard.image_url ? (
                  <div className="w-32 h-32 mx-auto mb-3 rounded-xl overflow-hidden border-2 border-white/30 shadow-lg">
                    <img
                      src={`${process.env.NEXT_PUBLIC_API_URL?.replace('/api/v1', '')}${earnedCard.image_url}`}
                      alt={earnedCard.name}
                      className="w-full h-full object-cover"
                    />
                  </div>
                ) : (
                  <div className="text-6xl mb-3 animate-bounce">
                    {earnedCard.emoji}
                  </div>
                )}

                {/* Name */}
                <h3 className="text-xl font-bold text-white mb-1">
                  {earnedCard.name}
                </h3>

                {/* Rarity */}
                <span className="inline-block px-3 py-1 rounded-full bg-black/20 text-white/90 text-sm mb-3">
                  {RARITY_LABELS[earnedCard.rarity] || 'Обычная'}
                </span>

                {/* Description */}
                {earnedCard.description && (
                  <p className="text-white/80 text-sm mb-3">
                    {earnedCard.description}
                  </p>
                )}

                {/* Stats */}
                <div className="flex justify-center gap-6 mt-4">
                  <div className="flex items-center gap-2 bg-black/20 px-3 py-2 rounded-lg">
                    <Heart className="w-5 h-5 text-red-300" />
                    <span className="text-white font-bold">{earnedCard.hp}</span>
                  </div>
                  <div className="flex items-center gap-2 bg-black/20 px-3 py-2 rounded-lg">
                    <Swords className="w-5 h-5 text-orange-300" />
                    <span className="text-white font-bold">{earnedCard.attack}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Action Button */}
            <Button
              onClick={() => {
                setShowCardModal(false);
                setEarnedCard(null);
              }}
              className="w-full"
            >
              <Sparkles className="w-4 h-4 mr-2" />
              Отлично!
            </Button>
          </div>
        )}
      </Modal>
    </div>
  );
}
