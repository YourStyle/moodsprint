'use client';

import { Check, Clock, ListTodo, Heart } from 'lucide-react';
import { Card, Progress } from '@/components/ui';
import type { DailyGoal } from '@/domain/types';

interface DailyGoalsProps {
  goals: DailyGoal[];
  allCompleted: boolean;
}

const goalIcons: Record<string, typeof Clock> = {
  focus_minutes: Clock,
  subtasks: ListTodo,
  mood_check: Heart,
};

export function DailyGoals({ goals, allCompleted }: DailyGoalsProps) {
  return (
    <Card variant="glass">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-white">Ежедневные цели</h3>
        {allCompleted && (
          <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded-full border border-green-500/30">
            +30 XP бонус!
          </span>
        )}
      </div>

      <div className="space-y-3">
        {goals.map((goal) => {
          const Icon = goalIcons[goal.type] || ListTodo;

          return (
            <div key={goal.type} className="flex items-center gap-3">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                  goal.completed
                    ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                    : 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                }`}
              >
                {goal.completed ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <Icon className="w-4 h-4" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className={goal.completed ? 'text-gray-500 line-through' : 'text-gray-300'}>
                    {goal.title}
                  </span>
                  <span className="text-gray-500 text-xs">
                    {goal.current}/{goal.target}
                  </span>
                </div>
                <Progress
                  value={goal.current}
                  max={goal.target}
                  size="sm"
                  color={goal.completed ? 'success' : 'gradient'}
                />
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
