'use client';

import { useState } from 'react';
import { Calendar, Bell, Clock } from 'lucide-react';
import { Button, Input, Textarea } from '@/components/ui';
import { useLanguage } from '@/lib/i18n';

interface TaskFormProps {
  onSubmit: (title: string, description: string, dueDate: string, scheduledAt?: string) => void;
  isLoading?: boolean;
  initialTitle?: string;
  initialDescription?: string;
  initialDueDate?: string;
  initialScheduledAt?: string;
  submitLabel?: string;
}

const formatDateForInput = (date: Date): string => {
  return date.toISOString().split('T')[0];
};

const formatTimeForInput = (date: Date): string => {
  return date.toTimeString().slice(0, 5); // HH:MM
};

export function TaskForm({
  onSubmit,
  isLoading,
  initialTitle = '',
  initialDescription = '',
  initialDueDate,
  initialScheduledAt,
  submitLabel,
}: TaskFormProps) {
  const { t, language } = useLanguage();
  const [title, setTitle] = useState(initialTitle);
  const [description, setDescription] = useState(initialDescription);
  const [dueDate, setDueDate] = useState(initialDueDate || formatDateForInput(new Date()));

  // Reminder state
  const [enableReminder, setEnableReminder] = useState(!!initialScheduledAt);
  const [reminderDate, setReminderDate] = useState(
    initialScheduledAt ? initialScheduledAt.split('T')[0] : formatDateForInput(new Date())
  );
  const [reminderTime, setReminderTime] = useState(
    initialScheduledAt ? initialScheduledAt.split('T')[1]?.slice(0, 5) : formatTimeForInput(new Date(Date.now() + 3600000))
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (title.trim()) {
      let scheduledAt: string | undefined;
      if (enableReminder && reminderDate && reminderTime) {
        // Create ISO string from local date and time
        scheduledAt = `${reminderDate}T${reminderTime}:00`;
      }
      onSubmit(title.trim(), description.trim(), dueDate, scheduledAt);
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

      {/* Reminder section */}
      <div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={enableReminder}
            onChange={(e) => setEnableReminder(e.target.checked)}
            className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-primary-500 focus:ring-primary-500 focus:ring-offset-gray-800"
          />
          <span className="flex items-center gap-1.5 text-sm font-medium text-gray-300">
            <Bell className="w-4 h-4" />
            {t('setReminder')}
          </span>
        </label>

        {enableReminder && (
          <div className="mt-3 grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                {t('date')}
              </label>
              <input
                type="date"
                value={reminderDate}
                onChange={(e) => setReminderDate(e.target.value)}
                min={today}
                className="w-full px-3 py-2 rounded-xl bg-gray-700 border border-gray-600 text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                {t('time')}
              </label>
              <div className="relative">
                <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="time"
                  value={reminderTime}
                  onChange={(e) => setReminderTime(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 rounded-xl bg-gray-700 border border-gray-600 text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
            </div>
          </div>
        )}
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
