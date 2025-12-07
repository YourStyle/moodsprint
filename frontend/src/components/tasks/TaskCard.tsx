'use client';

import { ChevronRight, Clock, CheckCircle2 } from 'lucide-react';
import { Card, Progress } from '@/components/ui';
import { PRIORITY_COLORS } from '@/domain/constants';
import type { Task } from '@/domain/types';

interface TaskCardProps {
  task: Task;
  onClick: () => void;
}

export function TaskCard({ task, onClick }: TaskCardProps) {
  const isCompleted = task.status === 'completed';

  return (
    <Card
      className={`cursor-pointer hover:shadow-md transition-all ${
        isCompleted ? 'opacity-60' : ''
      }`}
      onClick={onClick}
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-1">
          {isCompleted ? (
            <CheckCircle2 className="w-5 h-5 text-green-500" />
          ) : (
            <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h3
              className={`font-medium text-gray-900 ${
                isCompleted ? 'line-through text-gray-500' : ''
              }`}
            >
              {task.title}
            </h3>
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${PRIORITY_COLORS[task.priority]}`}
            >
              {task.priority}
            </span>
          </div>

          {task.description && (
            <p className="text-sm text-gray-500 mt-1 line-clamp-2">
              {task.description}
            </p>
          )}

          {task.subtasks_count > 0 && (
            <div className="mt-3 space-y-2">
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  {task.subtasks_completed}/{task.subtasks_count} steps
                </span>
                <span>{task.progress_percent}%</span>
              </div>
              <Progress
                value={task.progress_percent}
                size="sm"
                color={isCompleted ? 'success' : 'primary'}
              />
            </div>
          )}
        </div>

        <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
      </div>
    </Card>
  );
}
