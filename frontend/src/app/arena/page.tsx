'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Swords,
  Shield,
  Heart,
  Zap,
  Trophy,
  ArrowLeft,
  Skull,
  Star,
} from 'lucide-react';
import { Card, Button, Progress } from '@/components/ui';
import { gamificationService } from '@/services';
import { useAppStore } from '@/lib/store';
import { hapticFeedback } from '@/lib/telegram';
import type {
  Monster,
  BattleResult,
  BattleLogEntry,
  CharacterStats,
} from '@/services/gamification';

type GameState = 'select' | 'battle' | 'result';

export default function ArenaPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user } = useAppStore();
  const [gameState, setGameState] = useState<GameState>('select');
  const [selectedMonster, setSelectedMonster] = useState<Monster | null>(null);
  const [battleResult, setBattleResult] = useState<BattleResult | null>(null);
  const [currentLogIndex, setCurrentLogIndex] = useState(0);
  const [showingLog, setShowingLog] = useState(false);

  const { data: monstersData, isLoading: monstersLoading } = useQuery({
    queryKey: ['arena', 'monsters'],
    queryFn: () => gamificationService.getMonsters(),
    enabled: !!user,
  });

  const { data: characterData, isLoading: characterLoading } = useQuery({
    queryKey: ['character'],
    queryFn: () => gamificationService.getCharacter(),
    enabled: !!user,
  });

  const battleMutation = useMutation({
    mutationFn: (monsterId: number) => gamificationService.battle(monsterId),
    onSuccess: (response) => {
      if (response.success && response.data) {
        hapticFeedback('medium');
        setBattleResult(response.data);
        setShowingLog(true);
        setCurrentLogIndex(0);
        setGameState('battle');

        // Animate through battle log
        animateBattle(response.data.battle_log);
      }
    },
  });

  const animateBattle = (log: BattleLogEntry[]) => {
    log.forEach((entry, index) => {
      setTimeout(() => {
        setCurrentLogIndex(index);
        hapticFeedback('light');
        if (index === log.length - 1) {
          setTimeout(() => {
            setShowingLog(false);
            setGameState('result');
            hapticFeedback(battleResult?.won ? 'success' : 'error');
          }, 1500);
        }
      }, (index + 1) * 800);
    });
  };

  const handleSelectMonster = (monster: Monster) => {
    setSelectedMonster(monster);
    hapticFeedback('light');
  };

  const handleStartBattle = () => {
    if (selectedMonster) {
      battleMutation.mutate(selectedMonster.id);
    }
  };

  const handleBackToSelect = () => {
    setGameState('select');
    setSelectedMonster(null);
    setBattleResult(null);
    queryClient.invalidateQueries({ queryKey: ['character'] });
    queryClient.invalidateQueries({ queryKey: ['user', 'stats'] });
  };

  const monsters = monstersData?.data?.monsters || [];
  const character = characterData?.data?.character;

  if (!user) {
    return (
      <div className="p-4 text-center">
        <p className="text-gray-500">Войдите чтобы попасть на арену</p>
      </div>
    );
  }

  const isLoading = monstersLoading || characterLoading;

  return (
    <div className="min-h-screen p-4 pt-safe pb-safe">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => router.back()}
          className="w-10 h-10 rounded-full bg-gray-800 flex items-center justify-center"
        >
          <ArrowLeft className="w-5 h-5 text-white" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-white">Арена</h1>
          <p className="text-sm text-gray-400">Сражайся и получай награды</p>
        </div>
      </div>

      {/* Character Status */}
      {character && gameState === 'select' && (
        <Card className="mb-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-2xl">
                {user.first_name?.[0] || '?'}
              </div>
              <div>
                <p className="font-medium text-white">{user.first_name}</p>
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <span className="text-red-400">ATK {character.attack_power}</span>
                  <span className="text-blue-400">DEF {character.defense}</span>
                  <span className="text-yellow-400">SPD {character.speed}</span>
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="flex items-center gap-1 text-sm">
                <Heart className="w-4 h-4 text-red-500" />
                <span className="text-white">
                  {character.current_hp}/{character.max_hp}
                </span>
              </div>
              <Progress
                value={character.current_hp}
                max={character.max_hp}
                size="sm"
                color="error"
                className="w-24"
              />
            </div>
          </div>
          {character.current_hp <= 0 && (
            <div className="text-center text-sm text-red-400 mt-2">
              Восстановите здоровье в профиле перед боем!
            </div>
          )}
        </Card>
      )}

      {/* Monster Selection */}
      {gameState === 'select' && (
        <>
          <h2 className="text-lg font-semibold text-white mb-3">
            Выбери противника
          </h2>

          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Card key={i} className="animate-pulse">
                  <div className="flex items-center gap-3">
                    <div className="w-16 h-16 bg-gray-700 rounded-xl" />
                    <div className="flex-1">
                      <div className="h-4 bg-gray-700 rounded w-1/3 mb-2" />
                      <div className="h-3 bg-gray-700 rounded w-1/2" />
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {monsters.map((monster) => (
                <Card
                  key={monster.id}
                  className={`cursor-pointer transition-all ${
                    selectedMonster?.id === monster.id
                      ? 'ring-2 ring-purple-500 bg-purple-500/10'
                      : 'hover:bg-gray-700/50'
                  }`}
                  onClick={() => handleSelectMonster(monster)}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-16 h-16 rounded-xl flex items-center justify-center text-4xl ${
                        monster.is_boss
                          ? 'bg-gradient-to-br from-red-500/20 to-orange-500/20 border border-red-500/30'
                          : 'bg-gray-700'
                      }`}
                    >
                      {monster.emoji}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-white">{monster.name}</h3>
                        {monster.is_boss && (
                          <Star className="w-4 h-4 text-yellow-500" />
                        )}
                      </div>
                      <p className="text-xs text-gray-400">Уровень {monster.level}</p>
                      <div className="flex items-center gap-3 mt-1 text-xs">
                        <span className="text-red-400">ATK {monster.attack}</span>
                        <span className="text-blue-400">DEF {monster.defense}</span>
                        <span className="text-green-400">HP {monster.hp}</span>
                      </div>
                    </div>
                    <div className="text-right text-xs">
                      <p className="text-amber-400">+{monster.xp_reward} XP</p>
                      <p className="text-purple-400">
                        +{monster.stat_points_reward} очков
                      </p>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {selectedMonster && character && character.current_hp > 0 && (
            <div className="fixed bottom-20 left-4 right-4">
              <Button
                className="w-full"
                onClick={handleStartBattle}
                isLoading={battleMutation.isPending}
              >
                <Swords className="w-5 h-5 mr-2" />
                Сразиться с {selectedMonster.name}
              </Button>
            </div>
          )}
        </>
      )}

      {/* Battle Animation */}
      {gameState === 'battle' && showingLog && battleResult && (
        <div className="flex flex-col items-center justify-center min-h-[60vh]">
          <div className="flex items-center justify-between w-full max-w-sm mb-8">
            {/* Player */}
            <div className="text-center">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-3xl mb-2">
                {user.first_name?.[0] || '?'}
              </div>
              <p className="text-sm text-white">{user.first_name}</p>
            </div>

            <div className="text-2xl font-bold text-white">VS</div>

            {/* Monster */}
            <div className="text-center">
              <div className="w-20 h-20 rounded-xl bg-gray-700 flex items-center justify-center text-4xl mb-2">
                {battleResult.monster.emoji}
              </div>
              <p className="text-sm text-white">{battleResult.monster.name}</p>
            </div>
          </div>

          {/* Current action */}
          {battleResult.battle_log[currentLogIndex] && (
            <Card className="text-center p-6">
              <div className="text-4xl mb-4">
                {battleResult.battle_log[currentLogIndex].actor === 'player'
                  ? '⚔️'
                  : '💥'}
              </div>
              <p className="text-white">
                {battleResult.battle_log[currentLogIndex].actor === 'player'
                  ? 'Вы атакуете!'
                  : `${battleResult.monster.name} атакует!`}
              </p>
              <p className="text-2xl font-bold text-red-400 mt-2">
                -{battleResult.battle_log[currentLogIndex].damage}
              </p>
              <p className="text-sm text-gray-400 mt-2">
                Раунд {battleResult.battle_log[currentLogIndex].round}
              </p>
            </Card>
          )}
        </div>
      )}

      {/* Battle Result */}
      {gameState === 'result' && battleResult && (
        <div className="flex flex-col items-center justify-center min-h-[60vh]">
          <div className="text-center mb-6">
            {battleResult.won ? (
              <>
                <Trophy className="w-20 h-20 text-yellow-500 mx-auto mb-4" />
                <h2 className="text-2xl font-bold text-white mb-2">Победа!</h2>
                <p className="text-gray-400">
                  Вы победили {battleResult.monster.name}
                </p>
              </>
            ) : (
              <>
                <Skull className="w-20 h-20 text-gray-500 mx-auto mb-4" />
                <h2 className="text-2xl font-bold text-white mb-2">Поражение</h2>
                <p className="text-gray-400">
                  {battleResult.monster.name} оказался сильнее
                </p>
              </>
            )}
          </div>

          <Card className="w-full max-w-sm mb-6">
            <h3 className="font-medium text-white mb-3">Итоги боя</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Раундов</span>
                <span className="text-white">{battleResult.rounds}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Нанесено урона</span>
                <span className="text-green-400">{battleResult.damage_dealt}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Получено урона</span>
                <span className="text-red-400">{battleResult.damage_taken}</span>
              </div>
              {battleResult.won && (
                <>
                  <div className="border-t border-gray-700 pt-2 mt-2">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Опыт</span>
                      <span className="text-amber-400">
                        +{battleResult.xp_earned} XP
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Очки характеристик</span>
                      <span className="text-purple-400">
                        +{battleResult.stat_points_earned}
                      </span>
                    </div>
                  </div>
                  {battleResult.level_up && (
                    <div className="text-center pt-2 text-amber-400 font-medium">
                      Новый уровень!
                    </div>
                  )}
                </>
              )}
            </div>
          </Card>

          <Button className="w-full max-w-sm" onClick={handleBackToSelect}>
            Вернуться к выбору
          </Button>
        </div>
      )}
    </div>
  );
}
