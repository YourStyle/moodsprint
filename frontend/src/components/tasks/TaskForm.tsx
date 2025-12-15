'use client';

import { useState } from 'react';
import { Calendar } from 'lucide-react';
import { Button, Input, Textarea } from '@/components/ui';
import { useLanguage } from '@/lib/i18n';

interface TaskFormProps {
  onSubmit: (title: string, description: string, dueDate: string) => void;
  isLoading?: boolean;
  initialTitle?: string;
  initialDescription?: string;
  initialDueDate?: string;
  submitLabel?: string;
}

const formatDateForInput = (date: Date): string => {
  return date.toISOString().split('T')[0];
};

export function TaskForm({
  onSubmit,
  isLoading,
  initialTitle = '',
  initialDescription = '',
  initialDueDate,
  submitLabel,
}: TaskFormProps) {
  const { t, language } = useLanguage();
  const [title, setTitle] = useState(initialTitle);
  const [description, setDescription] = useState(initialDescription);
  const [dueDate, setDueDate] = useState(initialDueDate || formatDateForInput(new Date()));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (title.trim()) {
      onSubmit(title.trim(), description.trim(), dueDate);
    }
  };

  const today = formatDateForInput(new Date());
  const tomorrow = formatDateForInput(new Date(Date.now() + 86400000));

  const formatDateDisplay = (dateStr: string): string => {
    const date = new Date(dateStr);
    const locale = language === 'ru' ? 'ru-RU' : 'en-US';
    return date.toLocaleDateString(locale, { weekday: 'short', day: 'numeric', month: 'short' });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        label={t('taskTitle')}
        placeholder={t('taskPlaceholder')}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        maxLength={500}
        required
        autoFocus
      />

      <Textarea
        label={t('taskDescription')}
        placeholder={t('descriptionPlaceholder')}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        rows={3}
      />

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          {t('whenToComplete')}
        </label>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setDueDate(today)}
            className={`flex-1 py-2 px-3 text-sm font-medium rounded-xl transition-all ${
              dueDate === today
                ? 'bg-primary-500/20 text-primary-400 ring-2 ring-primary-500'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {t('today')}
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
            {t('tomorrow')}
          </button>
          <label
            className={`flex-1 py-2 px-3 text-sm font-medium rounded-xl transition-all cursor-pointer flex items-center justify-center gap-1 ${
              dueDate !== today && dueDate !== tomorrow
                ? 'bg-primary-500/20 text-primary-400 ring-2 ring-primary-500'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            <Calendar className="w-4 h-4" />
            {dueDate !== today && dueDate !== tomorrow ? formatDateDisplay(dueDate) : t('other')}
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
        {submitLabel || t('createTask')}
      </Button>
    </form>
  );
}
