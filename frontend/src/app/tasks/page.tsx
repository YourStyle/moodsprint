'use client';

import { useState } from 'react';
import { Plus, Filter } from 'lucide-react';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { Button, Card, Modal } from '@/components/ui';
import { TaskCard, TaskForm } from '@/components/tasks';
import { tasksService } from '@/services';
import { hapticFeedback } from '@/lib/telegram';
import { useAppStore } from '@/lib/store';
import { useLanguage } from '@/lib/i18n';
import type { TaskStatus } from '@/domain/types';

type FilterStatus = TaskStatus | 'all';

export default function TasksPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, showXPAnimation } = useAppStore();
  const { t } = useLanguage();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');

  const { data, isLoading } = useQuery({
    queryKey: ['tasks', filterStatus],
    queryFn: () =>
      tasksService.getTasks(filterStatus !== 'all' ? { status: filterStatus } : {}),
    enabled: !!user,
    placeholderData: keepPreviousData,
  });

  const createMutation = useMutation({
    mutationFn: (input: { title: string; description: string; due_date: string }) =>
      tasksService.createTask(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setShowCreateModal(false);
      hapticFeedback('success');
    },
  });

  const handleCreateTask = (title: string, description: string, dueDate: string) => {
    createMutation.mutate({ title, description, due_date: dueDate });
  };

  const filters: { value: FilterStatus; labelKey: 'all' | 'statusPending' | 'statusInProgress' | 'statusCompleted' }[] = [
    { value: 'all', labelKey: 'all' },
    { value: 'pending', labelKey: 'statusPending' },
    { value: 'in_progress', labelKey: 'statusInProgress' },
    { value: 'completed', labelKey: 'statusCompleted' },
  ];

  const rawTasks = data?.data?.tasks || [];

  // Sort tasks: by priority (high > medium > low), completed tasks at the end
  const priorityOrder: Record<string, number> = { high: 0, medium: 1, low: 2 };

  const tasks = [...rawTasks].sort((a, b) => {
    // Completed tasks go to the end
    if (a.status === 'completed' && b.status !== 'completed') return 1;
    if (a.status !== 'completed' && b.status === 'completed') return -1;

    // Sort by priority (high first)
    const priorityA = priorityOrder[a.priority] ?? 1;
    const priorityB = priorityOrder[b.priority] ?? 1;
    if (priorityA !== priorityB) return priorityA - priorityB;

    // Then by due date (earliest first)
    if (a.due_date && b.due_date) {
      return new Date(a.due_date).getTime() - new Date(b.due_date).getTime();
    }
    if (a.due_date) return -1;
    if (b.due_date) return 1;

    return 0;
  });

  return (
    <div className="p-4 space-y-4 pt-safe">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">{t('tasks')}</h1>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="w-4 h-4 mr-1" />
          {t('newTask')}
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 overflow-x-auto pb-2 -mx-4 px-4">
        {filters.map((filter) => (
          <button
            key={filter.value}
            onClick={() => setFilterStatus(filter.value)}
            className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
              filterStatus === filter.value
                ? 'bg-primary-500 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {t(filter.labelKey)}
          </button>
        ))}
      </div>

      {/* Task List */}
      {isLoading && !data ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="h-24 animate-pulse" />
          ))}
        </div>
      ) : tasks.length > 0 ? (
        <div className="space-y-3">
          {tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onClick={() => router.push(`/tasks/${task.id}`)}
            />
          ))}
        </div>
      ) : (
        <Card className="text-center py-12">
          <div className="text-4xl mb-4">📝</div>
          <p className="text-gray-500 mb-4">
            {filterStatus === 'all'
              ? t('noTasksYet')
              : t('noTasksInCategory')}
          </p>
          <Button onClick={() => setShowCreateModal(true)}>
            {t('createFirstTask')}
          </Button>
        </Card>
      )}

      {/* Create Task Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title={t('createTask')}
      >
        <TaskForm
          onSubmit={handleCreateTask}
          isLoading={createMutation.isPending}
        />
      </Modal>
    </div>
  );
}
