'use client';

import { useState } from 'react';
import { Calendar } from 'lucide-react';
import { Button, Input, Textarea } from '@/components/ui';
import type { TaskPriority } from '@/domain/types';

interface TaskFormProps {
  onSubmit: (title: string, description: string, priority: TaskPriority, dueDate: string) => void;
  isLoading?: boolean;
  initialTitle?: string;
  initialDescription?: string;
  initialPriority?: TaskPriority;
  initialDueDate?: string;
  submitLabel?: string;
}

const formatDateForInput = (date: Date): string => {
  return date.toISOString().split('T')[0];
};

const formatDateDisplay = (dateStr: string): string => {
  const date = new Date(dateStr);
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);

  if (dateStr === formatDateForInput(today)) return 'Сегодня';
  if (dateStr === formatDateForInput(tomorrow)) return 'Завтра';

  return date.toLocaleDateString('ru-RU', { weekday: 'short', day: 'numeric', month: 'short' });
};

export function TaskForm({
  onSubmit,
  isLoading,
  initialTitle = '',
  initialDescription = '',
  initialPriority = 'medium',
  initialDueDate,
  submitLabel = 'Создать задачу',
}: TaskFormProps) {
  const [title, setTitle] = useState(initialTitle);
  const [description, setDescription] = useState(initialDescription);
  const [priority, setPriority] = useState<TaskPriority>(initialPriority);
  const [dueDate, setDueDate] = useState(initialDueDate || formatDateForInput(new Date()));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (title.trim()) {
      onSubmit(title.trim(), description.trim(), priority, dueDate);
    }
  };

  const today = formatDateForInput(new Date());
  const tomorrow = formatDateForInput(new Date(Date.now() + 86400000));

  const priorities: { value: TaskPriority; label: string; color: string }[] = [
    { value: 'low', label: 'Низкий', color: 'bg-green-500/20 text-green-400 ring-green-500' },
    { value: 'medium', label: 'Средний', color: 'bg-yellow-500/20 text-yellow-400 ring-yellow-500' },
    { value: 'high', label: 'Высокий', color: 'bg-red-500/20 text-red-400 ring-red-500' },
  ];

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        label="Название задачи"
        placeholder="Что нужно сделать?"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        maxLength={500}
        required
        autoFocus
      />

      <Textarea
        label="Описание (необязательно)"
        placeholder="Добавьте подробности..."
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        rows={3}
      />

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Приоритет
        </label>
        <div className="flex gap-2">
          {priorities.map((p) => (
            <button
              key={p.value}
              type="button"
              onClick={() => setPriority(p.value)}
              className={`flex-1 py-2 px-3 text-sm font-medium rounded-xl transition-all ${
                priority === p.value
                  ? `${p.color} ring-2`
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Когда выполнить
        </label>
        <div className="flex gap-2 mb-2">
          <button
            type="button"
            onClick={() => setDueDate(today)}
            className={`flex-1 py-2 px-3 text-sm font-medium rounded-xl transition-all ${
              dueDate === today
                ? 'bg-primary-500/20 text-primary-400 ring-2 ring-primary-500'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Сегодня
          </button>
          <button
            type="button"
            onClick={() => setDueDate(tomorrow)}
            className={`flex-1 py-2 px-3 text-sm font-medium rounded-xl transition-all ${
              dueDate === tomorrow
                ? 'bg-primary-500/20 text-primary-400 ring-2 ring-primary-500'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Завтра
          </button>
          <label
            className={`flex-1 py-2 px-3 text-sm font-medium rounded-xl transition-all cursor-pointer flex items-center justify-center gap-1 ${
              dueDate !== today && dueDate !== tomorrow
                ? 'bg-primary-500/20 text-primary-400 ring-2 ring-primary-500'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            <Calendar className="w-4 h-4" />
            {dueDate !== today && dueDate !== tomorrow ? formatDateDisplay(dueDate) : 'Другой'}
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="sr-only"
              min={today}
            />
          </label>
        </div>
      </div>

      <Button
        type="submit"
        className="w-full"
        isLoading={isLoading}
        disabled={!title.trim()}
      >
        {submitLabel}
      </Button>
    </form>
  );
}
