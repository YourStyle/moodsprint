'use client';

import { Archive, Sparkles, CheckCircle2, Play, RotateCcw, Flame, Users } from 'lucide-react';
import { MiniTimer } from '@/components/focus/MiniTimer';
import { useTranslation } from '@/lib/i18n';
import type { TranslationKey } from '@/lib/i18n';
import type { FocusSession } from '@/domain/types';

export interface TaskCardCompactTask {
  id: number;
  title: string;
  progress_percent: number;
  estimated_minutes?: number;
  status: string;
  subtasks_count: number;
  due_date?: string | null;
  shared_with_count?: number;
}

export interface TaskCardCompactProps {
  task: TaskCardCompactTask;
  onClick: () => void;
  onStart?: () => void;
  onCompleteTask?: () => void;
  onRestore?: () => void;
  activeSession?: FocusSession;
  onPause?: () => void;
  onResume?: () => void;
  onComplete?: () => void;
  onStop?: () => void;
  isNew?: boolean;
}

function getDeadlineInfo(dueDate: string | null | undefined, t: (key: TranslationKey) => string) {
  if (!dueDate) return null;
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const due = new Date(dueDate + 'T00:00:00');
  const diffMs = due.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return { label: t('overdue'), color: 'text-red-400', bg: 'bg-red-500/20' };
  if (diffDays <= 1) return { label: diffDays === 0 ? t('today') : `1${t('daysShort')}`, color: 'text-red-400', bg: 'bg-red-500/20' };
  if (diffDays <= 3) return { label: `${diffDays}${t('daysShort')}`, color: 'text-orange-400', bg: 'bg-orange-500/20' };
  if (diffDays <= 7) return { label: `${diffDays}${t('daysShort')}`, color: 'text-yellow-400', bg: 'bg-yellow-500/20' };
  return { label: `${diffDays}${t('daysShort')}`, color: 'text-gray-400', bg: 'bg-gray-700/50' };
}

export function TaskCardCompact({
  task,
  onClick,
  onStart,
  onCompleteTask,
  onRestore,
  activeSession,
  onPause,
  onResume,
  onComplete,
  onStop,
  isNew,
}: TaskCardCompactProps) {
  const { t } = useTranslation();
  const isCompleted = task.status === 'completed';
  const isArchived = task.status === 'archived';
  const hasSubtasks = task.subtasks_count > 0;
  const hasActiveSession = !!activeSession;
  const deadline = !isCompleted && !isArchived ? getDeadlineInfo(task.due_date, t) : null;

  return (
    <div
      className={`bg-dark-700/50 rounded-xl p-3 border ${
        hasActiveSession
          ? 'border-primary-500/50'
          : isArchived
          ? 'border-orange-500/30'
          : 'border-gray-800'
      } ${isCompleted || isArchived ? 'opacity-60' : ''}`}
    >
      <div className="flex items-center gap-3" onClick={onClick}>
        {/* Status icon */}
        <div
          className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
            isCompleted
              ? 'bg-green-500/20'
              : isArchived
              ? 'bg-orange-500/20'
              : hasActiveSession
              ? 'bg-primary-500/30'
              : 'bg-purple-500/20'
          }`}
        >
          {isCompleted ? (
            <span className="text-sm text-green-400">&#10003;</span>
          ) : isArchived ? (
            <Archive className="w-4 h-4 text-orange-400" />
          ) : hasActiveSession ? (
            <div className="w-3 h-3 rounded-full bg-primary-500 animate-pulse" />
          ) : (
            <Sparkles className="w-4 h-4 text-purple-400" />
          )}
        </div>

        {/* Title + badges + progress bar */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <h3
              className={`text-sm font-medium truncate ${
                isCompleted ? 'text-gray-500 line-through' : 'text-white'
              }`}
            >
              {task.title}
            </h3>
            {isNew && (
              <span className="px-1.5 py-0.5 bg-primary-500/30 text-primary-400 text-[10px] font-bold rounded-full flex-shrink-0">
                NEW
              </span>
            )}
            {deadline && (
              <span className={`flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-medium flex-shrink-0 ${deadline.bg} ${deadline.color}`}>
                <Flame className="w-2.5 h-2.5" />
                {deadline.label}
              </span>
            )}
            {(task.shared_with_count ?? 0) > 0 && (
              <span className="flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-medium flex-shrink-0 bg-primary-500/20 text-primary-400">
                <Users className="w-2.5 h-2.5" />
                {task.shared_with_count}
              </span>
            )}
          </div>
          {!isCompleted && hasSubtasks && !hasActiveSession && (
            <div className="mt-1 h-1 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-500 rounded-full transition-all"
                style={{ width: `${task.progress_percent}%` }}
              />
            </div>
          )}
        </div>

        {/* Action area */}
        {hasActiveSession && activeSession && onPause && onResume && onComplete && onStop ? (
          <MiniTimer
            session={activeSession}
            onPause={onPause}
            onResume={onResume}
            onComplete={onComplete}
            onStop={onStop}
          />
        ) : isArchived && onRestore ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRestore();
            }}
            className="w-8 h-8 rounded-lg bg-orange-500/20 hover:bg-orange-500/30 flex items-center justify-center transition-colors flex-shrink-0"
          >
            <RotateCcw className="w-4 h-4 text-orange-400" />
          </button>
        ) : !isCompleted ? (
          <div className="flex items-center gap-1.5">
            {onCompleteTask && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onCompleteTask();
                }}
                className="w-8 h-8 rounded-lg bg-green-500/20 hover:bg-green-500/30 flex items-center justify-center transition-colors flex-shrink-0"
              >
                <CheckCircle2 className="w-4 h-4 text-green-400" />
              </button>
            )}
            {onStart && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onStart();
                }}
                className="w-8 h-8 rounded-lg bg-primary-500 hover:bg-primary-600 flex items-center justify-center transition-colors flex-shrink-0"
              >
                <Play className="w-4 h-4 text-white" fill="white" />
              </button>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
