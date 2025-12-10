'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Scroll, Check, Gift, Sparkles } from 'lucide-react';
import { Card, Progress, Button } from '@/components/ui';
import { gamificationService } from '@/services';
import { hapticFeedback } from '@/lib/telegram';
import type { DailyQuest } from '@/services/gamification';

interface DailyQuestsProps {
  quests: DailyQuest[];
}

export function DailyQuests({ quests }: DailyQuestsProps) {
  const queryClient = useQueryClient();
  const [claimingId, setClaimingId] = useState<number | null>(null);

  const claimMutation = useMutation({
    mutationFn: (questId: number) => gamificationService.claimQuestReward(questId),
    onSuccess: (response, questId) => {
      if (response.success) {
        hapticFeedback('success');
        queryClient.invalidateQueries({ queryKey: ['quests'] });
        queryClient.invalidateQueries({ queryKey: ['user', 'stats'] });
        queryClient.invalidateQueries({ queryKey: ['character'] });
      }
      setClaimingId(null);
    },
    onError: () => {
      setClaimingId(null);
    },
  });

  const handleClaim = (questId: number) => {
    setClaimingId(questId);
    hapticFeedback('light');
    claimMutation.mutate(questId);
  };

  const completedCount = quests.filter((q) => q.completed).length;
  const claimedCount = quests.filter((q) => q.claimed).length;

  return (
    <Card variant="glass">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Scroll className="w-5 h-5 text-amber-500" />
          <h3 className="font-semibold text-white">Ежедневные квесты</h3>
        </div>
        <span className="text-xs text-gray-400">
          {completedCount}/{quests.length} выполнено
        </span>
      </div>

      <div className="space-y-3">
        {quests.map((quest) => (
          <div
            key={quest.id}
            className={`p-3 rounded-xl transition-all ${
              quest.claimed
                ? 'bg-gray-700/30 opacity-60'
                : quest.completed
                ? 'bg-amber-500/10 border border-amber-500/30'
                : 'bg-gray-700/50'
            }`}
          >
            <div className="flex items-start gap-3">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                  quest.claimed
                    ? 'bg-gray-600 text-gray-400'
                    : quest.completed
                    ? 'bg-amber-500/20 text-amber-400'
                    : 'bg-purple-500/20 text-purple-400'
                }`}
              >
                {quest.claimed ? (
                  <Check className="w-5 h-5" />
                ) : quest.completed ? (
                  <Gift className="w-5 h-5" />
                ) : (
                  <Sparkles className="w-5 h-5" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <h4
                  className={`font-medium text-sm ${
                    quest.claimed ? 'text-gray-500' : 'text-white'
                  }`}
                >
                  {quest.title}
                </h4>
                <p className="text-xs text-gray-400 mt-0.5">
                  {quest.themed_description || quest.description}
                </p>

                {!quest.completed && (
                  <div className="mt-2">
                    <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
                      <span>Прогресс</span>
                      <span>
                        {quest.current_count}/{quest.target_count}
                      </span>
                    </div>
                    <Progress
                      value={quest.current_count}
                      max={quest.target_count}
                      size="sm"
                      color="gradient"
                    />
                  </div>
                )}

                <div className="flex items-center justify-between mt-2">
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-amber-400">+{quest.xp_reward} XP</span>
                    <span className="text-purple-400">
                      +{quest.stat_points_reward} очков
                    </span>
                  </div>

                  {quest.completed && !quest.claimed && (
                    <Button
                      size="sm"
                      variant="primary"
                      onClick={() => handleClaim(quest.id)}
                      isLoading={claimingId === quest.id}
                      className="text-xs px-3 py-1"
                    >
                      Забрать
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {claimedCount === quests.length && quests.length > 0 && (
        <div className="mt-4 text-center text-sm text-gray-400">
          Все квесты на сегодня выполнены! Возвращайся завтра.
        </div>
      )}
    </Card>
  );
}
