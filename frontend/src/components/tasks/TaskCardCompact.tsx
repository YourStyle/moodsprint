'use client';

import { Archive, Sparkles, CheckCircle2, Play, RotateCcw } from 'lucide-react';
import { MiniTimer } from '@/components/focus/MiniTimer';
import type { FocusSession } from '@/domain/types';

export interface TaskCardCompactTask {
  id: number;
  title: string;
  progress_percent: number;
  estimated_minutes?: number;
  status: string;
  subtasks_count: number;
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

/**
 * Compact task card used in the main task list (non-ultra-compact mode).
 * Shows task status icon, title, optional progress bar, and inline action buttons.
 * Renders a MiniTimer when a focus session is active for this task.
 *
 * Usage:
 *   <TaskCardCompact
 *     task={task}
 *     onClick={() => router.push(`/tasks/${task.id}`)}
 *     onStart={() => startFocus(task.id)}
 *     onCompleteTask={() => completeTask(task.id)}
 *     activeSession={session}
 *     onPause={() => pauseSession(session.id)}
 *     onResume={() => resumeSession(session.id)}
 *     onComplete={() => completeTask(task.id)}
 *     onStop={() => cancelSession(session.id)}
 *   />
 */
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
  const isCompleted = task.status === 'completed';
  const isArchived = task.status === 'archived';
  const hasSubtasks = task.subtasks_count > 0;
  const hasActiveSession = !!activeSession;

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

        {/* Title + progress bar */}
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
