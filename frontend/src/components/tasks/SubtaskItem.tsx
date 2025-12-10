'use client';

import { CheckCircle2, Circle, Clock, Play, Pencil } from 'lucide-react';
import clsx from 'clsx';
import type { Subtask } from '@/domain/types';

interface SubtaskItemProps {
  subtask: Subtask;
  onToggle: () => void;
  onFocus: () => void;
  onEdit?: () => void;
  disabled?: boolean;
}

export function SubtaskItem({ subtask, onToggle, onFocus, onEdit, disabled }: SubtaskItemProps) {
  const isCompleted = subtask.status === 'completed';
  const isInProgress = subtask.status === 'in_progress';

  return (
    <div
      className={clsx(
        'flex items-center gap-3 p-3 rounded-xl transition-colors',
        isCompleted ? 'bg-green-500/10' : isInProgress ? 'bg-primary-500/10' : 'bg-gray-800',
        !disabled && !isCompleted && 'hover:bg-gray-700'
      )}
    >
      <button
        onClick={onToggle}
        disabled={disabled}
        className="flex-shrink-0"
      >
        {isCompleted ? (
          <CheckCircle2 className="w-6 h-6 text-green-500" />
        ) : (
          <Circle
            className={clsx(
              'w-6 h-6',
              isInProgress ? 'text-primary-500' : 'text-gray-500'
            )}
          />
        )}
      </button>

      <div
        className="flex-1 min-w-0 cursor-pointer"
        onClick={(e) => {
          if (onEdit && !isCompleted) {
            e.stopPropagation();
            onEdit();
          }
        }}
      >
        <p
          className={clsx(
            'font-medium',
            isCompleted ? 'text-gray-500 line-through' : 'text-white'
          )}
        >
          {subtask.title}
        </p>
        <p className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
          <Clock className="w-3 h-3" />
          {subtask.estimated_minutes} мин
        </p>
      </div>

      {!isCompleted && onEdit && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onEdit();
          }}
          disabled={disabled}
          className="flex-shrink-0 p-2 rounded-full text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
        >
          <Pencil className="w-4 h-4" />
        </button>
      )}

      {!isCompleted && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onFocus();
          }}
          disabled={disabled}
          className="flex-shrink-0 p-2 rounded-full bg-primary-500 text-white hover:bg-primary-600 transition-colors"
        >
          <Play className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
