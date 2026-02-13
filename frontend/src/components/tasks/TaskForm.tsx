'use client';

import { useState } from 'react';
import { Calendar, Bell, Sparkles, ListPlus, X, Plus } from 'lucide-react';
import { Button, Input, Textarea } from '@/components/ui';
import { useLanguage } from '@/lib/i18n';

interface TaskFormProps {
  onSubmit: (title: string, description: string, dueDate: string, scheduledAt?: string, autoDecompose?: boolean, subtasks?: string[]) => void;
  isLoading?: boolean;
  initialTitle?: string;
  initialDescription?: string;
  initialDueDate?: string;
  initialScheduledAt?: string;
  submitLabel?: string;
}

const formatDateForInput = (date: Date): string => {
  // Use local timezone, not UTC
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
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

  // Auto-decompose state
  const [autoDecompose, setAutoDecompose] = useState(false);
  const showAutoDecompose = description.length >= 50;

  // Subtask state
  const [showSubtasks, setShowSubtasks] = useState(false);
  const [subtasks, setSubtasks] = useState<string[]>(['']);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (title.trim()) {
      let scheduledAt: string | undefined;
      if (enableReminder && reminderDate && reminderTime) {
        // Create Date from local date and time, then convert to UTC ISO string
        const localDate = new Date(`${reminderDate}T${reminderTime}:00`);
        scheduledAt = localDate.toISOString();
      }
      const validSubtasks = subtasks.filter(s => s.trim());
      onSubmit(title.trim(), description.trim(), dueDate, scheduledAt, showAutoDecompose && autoDecompose, validSubtasks.length > 0 ? validSubtasks : undefined);
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

      {/* Auto-decompose toggle - appears when description is long enough */}
      {showAutoDecompose && (
        <label className="flex items-center justify-between cursor-pointer p-3 rounded-xl bg-purple-500/10 border border-purple-500/30">
          <span className="flex items-center gap-2 text-sm font-medium text-purple-300">
            <Sparkles className="w-4 h-4 text-purple-400" />
            {t('autoDecomposeWithAI')}
          </span>
          <div className="relative">
            <input
              type="checkbox"
              checked={autoDecompose}
              onChange={(e) => setAutoDecompose(e.target.checked)}
              className="sr-only"
            />
            <div className={`w-10 h-5 rounded-full transition-colors ${autoDecompose ? 'bg-purple-500' : 'bg-gray-600'}`}>
              <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${autoDecompose ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </div>
          </div>
        </label>
      )}

      {/* Subtasks */}
      <div>
        <button
          type="button"
          onClick={() => setShowSubtasks(!showSubtasks)}
          className="flex items-center gap-2 text-sm font-medium text-gray-300 hover:text-white transition-colors"
        >
          <ListPlus className="w-4 h-4 text-primary-400" />
          {t('addSubtasks')}
        </button>
        {showSubtasks && (
          <div className="space-y-2 mt-2">
            {subtasks.map((st, idx) => (
              <div key={idx} className="flex gap-2">
                <input
                  type="text"
                  value={st}
                  onChange={(e) => {
                    const updated = [...subtasks];
                    updated[idx] = e.target.value;
                    setSubtasks(updated);
                  }}
                  placeholder={t('subtaskPlaceholder')}
                  className="flex-1 px-3 py-2 rounded-xl bg-gray-700 border border-gray-600 text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
                <button
                  type="button"
                  onClick={() => {
                    const remaining = subtasks.filter((_, i) => i !== idx);
                    if (remaining.length === 0) {
                      setShowSubtasks(false);
                      setSubtasks(['']);
                    } else {
                      setSubtasks(remaining);
                    }
                  }}
                  className="p-2 text-gray-400 hover:text-red-400 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={() => setSubtasks([...subtasks, ''])}
              className="flex items-center gap-1 text-xs text-primary-400 hover:text-primary-300 transition-colors"
            >
              <Plus className="w-3 h-3" />
              {t('addAnotherSubtask')}
            </button>
          </div>
        )}
      </div>

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
        <label className="flex items-center justify-between cursor-pointer p-3 rounded-xl bg-gray-800/50 border border-gray-700">
          <span className="flex items-center gap-2 text-sm font-medium text-gray-300">
            <Bell className="w-4 h-4 text-primary-400" />
            {t('setReminder')}
          </span>
          <div className="relative">
            <input
              type="checkbox"
              checked={enableReminder}
              onChange={(e) => setEnableReminder(e.target.checked)}
              className="sr-only"
            />
            <div className={`w-10 h-5 rounded-full transition-colors ${enableReminder ? 'bg-primary-500' : 'bg-gray-600'}`}>
              <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${enableReminder ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </div>
          </div>
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
              <input
                type="time"
                value={reminderTime}
                onChange={(e) => setReminderTime(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-gray-700 border border-gray-600 text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
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
