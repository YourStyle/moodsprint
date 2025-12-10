'use client';

import { useState } from 'react';
import { Calendar, Clock, Bell } from 'lucide-react';
import { Button, Input, Textarea } from '@/components/ui';
import type { TaskPriority, PreferredTime } from '@/domain/types';

interface TaskFormProps {
  onSubmit: (title: string, description: string, priority: TaskPriority, dueDate: string, preferredTime?: PreferredTime, scheduledAt?: string) => void;
  isLoading?: boolean;
  initialTitle?: string;
  initialDescription?: string;
  initialPriority?: TaskPriority;
  initialDueDate?: string;
  initialPreferredTime?: PreferredTime;
  initialScheduledAt?: string;
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
  initialPreferredTime,
  initialScheduledAt,
  submitLabel = 'Создать задачу',
}: TaskFormProps) {
  const [title, setTitle] = useState(initialTitle);
  const [description, setDescription] = useState(initialDescription);
  const [priority, setPriority] = useState<TaskPriority>(initialPriority);
  const [dueDate, setDueDate] = useState(initialDueDate || formatDateForInput(new Date()));
  const [preferredTime, setPreferredTime] = useState<PreferredTime | undefined>(initialPreferredTime);
  const [scheduledAt, setScheduledAt] = useState<string>(initialScheduledAt || '');
  const [showReminder, setShowReminder] = useState(!!initialScheduledAt);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (title.trim()) {
      // Convert local datetime to UTC ISO string for server
      let scheduledAtUtc: string | undefined;
      if (showReminder && scheduledAt) {
        // scheduledAt is in local time format "YYYY-MM-DDTHH:mm"
        // Convert to UTC ISO string
        const localDate = new Date(scheduledAt);
        scheduledAtUtc = localDate.toISOString();
      }
      onSubmit(title.trim(), description.trim(), priority, dueDate, preferredTime, scheduledAtUtc);
    }
  };

  const today = formatDateForInput(new Date());
  const tomorrow = formatDateForInput(new Date(Date.now() + 86400000));

  const priorities: { value: TaskPriority; label: string; color: string }[] = [
    { value: 'low', label: 'Низкий', color: 'bg-green-500/20 text-green-400 ring-green-500' },
    { value: 'medium', label: 'Средний', color: 'bg-yellow-500/20 text-yellow-400 ring-yellow-500' },
    { value: 'high', label: 'Высокий', color: 'bg-red-500/20 text-red-400 ring-red-500' },
  ];

  const timeSlots: { value: PreferredTime; label: string; icon: string }[] = [
    { value: 'morning', label: 'Утро', icon: '🌅' },
    { value: 'afternoon', label: 'День', icon: '☀️' },
    { value: 'evening', label: 'Вечер', icon: '🌆' },
    { value: 'night', label: 'Ночь', icon: '🌙' },
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

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          <Bell className="w-4 h-4 inline mr-1" />
          Напоминание
        </label>
        <button
          type="button"
          onClick={() => {
            setShowReminder(!showReminder);
            if (!showReminder && !scheduledAt) {
              // Set default to today at next hour (local time for datetime-local input)
              const now = new Date();
              now.setHours(now.getHours() + 1, 0, 0, 0);
              // Format as local datetime string for datetime-local input
              const year = now.getFullYear();
              const month = String(now.getMonth() + 1).padStart(2, '0');
              const day = String(now.getDate()).padStart(2, '0');
              const hours = String(now.getHours()).padStart(2, '0');
              const minutes = String(now.getMinutes()).padStart(2, '0');
              setScheduledAt(`${year}-${month}-${day}T${hours}:${minutes}`);
            }
          }}
          className={`w-full py-2 px-3 text-sm font-medium rounded-xl transition-all mb-2 ${
            showReminder
              ? 'bg-primary-500/20 text-primary-400 ring-2 ring-primary-500'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          {showReminder ? '🔔 Напомнить в заданное время' : '🔕 Без напоминания'}
        </button>
        {showReminder && (
          <div className="mt-2">
            <input
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              min={(() => {
                const now = new Date();
                const year = now.getFullYear();
                const month = String(now.getMonth() + 1).padStart(2, '0');
                const day = String(now.getDate()).padStart(2, '0');
                const hours = String(now.getHours()).padStart(2, '0');
                const minutes = String(now.getMinutes()).padStart(2, '0');
                return `${year}-${month}-${day}T${hours}:${minutes}`;
              })()}
            />
            <p className="text-xs text-gray-500 mt-1">
              Бот напомнит о задаче в указанное время
            </p>
          </div>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          <Clock className="w-4 h-4 inline mr-1" />
          Предпочтительное время (для &quot;Есть время?&quot;)
        </label>
        <div className="flex gap-2">
          {timeSlots.map((slot) => (
            <button
              key={slot.value}
              type="button"
              onClick={() => setPreferredTime(preferredTime === slot.value ? undefined : slot.value)}
              className={`flex-1 py-2 px-2 text-sm font-medium rounded-xl transition-all ${
                preferredTime === slot.value
                  ? 'bg-primary-500/20 text-primary-400 ring-2 ring-primary-500'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              <span className="block text-base">{slot.icon}</span>
              <span className="text-xs">{slot.label}</span>
            </button>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Когда лучше предлагать эту задачу
        </p>
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
