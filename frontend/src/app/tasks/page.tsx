'use client';

import { useState } from 'react';
import { Plus, Filter } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { Button, Card, Modal } from '@/components/ui';
import { TaskCard, TaskForm } from '@/components/tasks';
import { tasksService } from '@/services';
import { hapticFeedback } from '@/lib/telegram';
import { useAppStore } from '@/lib/store';
import type { TaskPriority, TaskStatus } from '@/domain/types';

type FilterStatus = TaskStatus | 'all';

export default function TasksPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, showXPAnimation } = useAppStore();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');

  const { data, isLoading } = useQuery({
    queryKey: ['tasks', filterStatus],
    queryFn: () =>
      tasksService.getTasks(filterStatus !== 'all' ? { status: filterStatus } : {}),
    enabled: !!user,
  });

  const createMutation = useMutation({
    mutationFn: (input: { title: string; description: string; priority: TaskPriority }) =>
      tasksService.createTask(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setShowCreateModal(false);
      hapticFeedback('success');
    },
  });

  const handleCreateTask = (title: string, description: string, priority: TaskPriority) => {
    createMutation.mutate({ title, description, priority });
  };

  const filters: { value: FilterStatus; label: string }[] = [
    { value: 'all', label: 'Все' },
    { value: 'pending', label: 'Ожидают' },
    { value: 'in_progress', label: 'В работе' },
    { value: 'completed', label: 'Готово' },
  ];

  const tasks = data?.data?.tasks || [];

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Задачи</h1>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="w-4 h-4 mr-1" />
          Новая
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
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {/* Task List */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="h-24 animate-pulse bg-gray-100" />
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
              ? 'Пока нет задач'
              : 'Нет задач в этой категории'}
          </p>
          <Button onClick={() => setShowCreateModal(true)}>
            Создать первую задачу
          </Button>
        </Card>
      )}

      {/* Create Task Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Создать задачу"
      >
        <TaskForm
          onSubmit={handleCreateTask}
          isLoading={createMutation.isPending}
        />
      </Modal>
    </div>
  );
}
