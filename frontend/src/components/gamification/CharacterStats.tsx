'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Swords, Shield, Zap, Brain, Heart, Plus, Minus } from 'lucide-react';
import { Card, Progress, Button } from '@/components/ui';
import { gamificationService } from '@/services';
import { hapticFeedback } from '@/lib/telegram';
import { useTranslation, type TranslationKey } from '@/lib/i18n';
import type { CharacterStats as CharacterStatsType } from '@/services/gamification';

interface CharacterStatsProps {
  character: CharacterStatsType;
}

type StatName = 'strength' | 'agility' | 'intelligence';

const statConfig: Record<
  StatName,
  { labelKey: TranslationKey; icon: typeof Swords; color: string; descKey: TranslationKey }
> = {
  strength: {
    labelKey: 'statStrength',
    icon: Swords,
    color: 'text-red-400',
    descKey: 'statStrengthDesc',
  },
  agility: {
    labelKey: 'statDexterity',
    icon: Zap,
    color: 'text-yellow-400',
    descKey: 'statDexterityDesc',
  },
  intelligence: {
    labelKey: 'statIntelligence',
    icon: Brain,
    color: 'text-blue-400',
    descKey: 'statIntelligenceDesc',
  },
};

export function CharacterStats({ character }: CharacterStatsProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [selectedStat, setSelectedStat] = useState<StatName | null>(null);
  const [pointsToAdd, setPointsToAdd] = useState(1);

  const distributeMutation = useMutation({
    mutationFn: ({ stat, points }: { stat: StatName; points: number }) =>
      gamificationService.distributeStat(stat, points),
    onSuccess: (response) => {
      if (response.success) {
        hapticFeedback('success');
        queryClient.invalidateQueries({ queryKey: ['character'] });
        setSelectedStat(null);
        setPointsToAdd(1);
      }
    },
  });

  const healMutation = useMutation({
    mutationFn: () => gamificationService.healCharacter(true),
    onSuccess: (response) => {
      if (response.success) {
        hapticFeedback('success');
        queryClient.invalidateQueries({ queryKey: ['character'] });
      }
    },
  });

  const handleDistribute = () => {
    if (selectedStat && pointsToAdd > 0) {
      distributeMutation.mutate({ stat: selectedStat, points: pointsToAdd });
    }
  };

  const hpPercent = Math.round((character.current_hp / character.max_hp) * 100);
  const needsHealing = character.current_hp < character.max_hp;

  return (
    <Card variant="glass">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-purple-500" />
          <h3 className="font-semibold text-white">{t('characteristics')}</h3>
        </div>
        {character.available_stat_points > 0 && (
          <span className="text-xs bg-purple-500/20 text-purple-400 px-2 py-1 rounded-full border border-purple-500/30">
            {t('statPoints').replace('{count}', String(character.available_stat_points))}
          </span>
        )}
      </div>

      {/* HP Bar */}
      <div className="mb-4 p-3 bg-gray-700/50 rounded-xl">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Heart className="w-4 h-4 text-red-500" />
            <span className="text-sm text-white">{t('health')}</span>
          </div>
          <span className="text-sm text-gray-400">
            {character.current_hp}/{character.max_hp}
          </span>
        </div>
        <Progress
          value={character.current_hp}
          max={character.max_hp}
          size="md"
          color={hpPercent > 50 ? 'success' : hpPercent > 25 ? 'warning' : 'error'}
        />
        {needsHealing && (
          <Button
            size="sm"
            variant="secondary"
            onClick={() => healMutation.mutate()}
            isLoading={healMutation.isPending}
            className="mt-2 w-full text-xs"
          >
            {t('restoreHealth')}
          </Button>
        )}
      </div>

      {/* Stats */}
      <div className="space-y-3">
        {(Object.keys(statConfig) as StatName[]).map((statName) => {
          const config = statConfig[statName];
          const Icon = config.icon;
          const value = character[statName];
          const isSelected = selectedStat === statName;

          return (
            <div
              key={statName}
              className={`p-3 rounded-xl transition-all cursor-pointer ${
                isSelected
                  ? 'bg-purple-500/20 border border-purple-500/30'
                  : 'bg-gray-700/50 hover:bg-gray-700/70'
              }`}
              onClick={() => {
                if (character.available_stat_points > 0) {
                  setSelectedStat(isSelected ? null : statName);
                  setPointsToAdd(1);
                }
              }}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Icon className={`w-4 h-4 ${config.color}`} />
                  <span className="text-sm text-white">{t(config.labelKey)}</span>
                </div>
                <span className={`text-lg font-bold ${config.color}`}>{value}</span>
              </div>
              <Progress value={value} max={100} size="sm" color="gradient" />
              <p className="text-xs text-gray-500 mt-1">{t(config.descKey)}</p>

              {isSelected && character.available_stat_points > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-600">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setPointsToAdd(Math.max(1, pointsToAdd - 1));
                        }}
                        className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center text-white hover:bg-gray-500"
                      >
                        <Minus className="w-4 h-4" />
                      </button>
                      <span className="text-white font-bold w-8 text-center">
                        {pointsToAdd}
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setPointsToAdd(
                            Math.min(
                              character.available_stat_points,
                              100 - value,
                              pointsToAdd + 1
                            )
                          );
                        }}
                        className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center text-white hover:bg-gray-500"
                      >
                        <Plus className="w-4 h-4" />
                      </button>
                    </div>
                    <Button
                      size="sm"
                      variant="primary"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDistribute();
                      }}
                      isLoading={distributeMutation.isPending}
                    >
                      {t('add')}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Battle Stats */}
      <div className="mt-4 grid grid-cols-3 gap-2">
        <div className="text-center p-2 bg-gray-700/30 rounded-lg">
          <p className="text-lg font-bold text-red-400">{character.attack_power}</p>
          <p className="text-xs text-gray-400">{t('attack')}</p>
        </div>
        <div className="text-center p-2 bg-gray-700/30 rounded-lg">
          <p className="text-lg font-bold text-blue-400">{character.defense}</p>
          <p className="text-xs text-gray-400">{t('defense')}</p>
        </div>
        <div className="text-center p-2 bg-gray-700/30 rounded-lg">
          <p className="text-lg font-bold text-yellow-400">{character.speed}</p>
          <p className="text-xs text-gray-400">{t('speed')}</p>
        </div>
      </div>

      {/* Battle record */}
      <div className="mt-3 flex items-center justify-center gap-4 text-sm">
        <span className="text-green-400">
          {t('winsCount').replace('{count}', String(character.battles_won))}
        </span>
        <span className="text-gray-500">|</span>
        <span className="text-red-400">
          {t('lossesCount').replace('{count}', String(character.battles_lost))}
        </span>
      </div>
    </Card>
  );
}
