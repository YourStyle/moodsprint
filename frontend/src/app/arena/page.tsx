'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Swords,
  Heart,
  Trophy,
  Skull,
  Star,
  Medal,
  Flame,
  Crown,
} from 'lucide-react';
import { Card, Button, Progress } from '@/components/ui';
import { gamificationService } from '@/services';
import { useAppStore } from '@/lib/store';
import { hapticFeedback } from '@/lib/telegram';
import { cn } from '@/lib/utils';
import type {
  Monster,
  BattleResult,
  BattleLogEntry,
} from '@/services/gamification';

type Tab = 'battle' | 'leaderboard';
type GameState = 'select' | 'battle' | 'result';
type LeaderboardType = 'weekly' | 'all_time';

export default function ArenaPage() {
  const queryClient = useQueryClient();
  const { user } = useAppStore();

  // Tab state
  const [activeTab, setActiveTab] = useState<Tab>('battle');

  // Battle state
  const [gameState, setGameState] = useState<GameState>('select');
  const [selectedMonster, setSelectedMonster] = useState<Monster | null>(null);
  const [battleResult, setBattleResult] = useState<BattleResult | null>(null);
  const [currentLogIndex, setCurrentLogIndex] = useState(0);
  const [showingLog, setShowingLog] = useState(false);

  // Leaderboard state
  const [leaderboardType, setLeaderboardType] = useState<LeaderboardType>('weekly');

  // Battle queries
  const { data: monstersData, isLoading: monstersLoading } = useQuery({
    queryKey: ['arena', 'monsters'],
    queryFn: () => gamificationService.getMonsters(),
    enabled: !!user && activeTab === 'battle',
  });

  const { data: characterData, isLoading: characterLoading } = useQuery({
    queryKey: ['character'],
    queryFn: () => gamificationService.getCharacter(),
    enabled: !!user,
  });

  // Leaderboard query
  const { data: leaderboardData, isLoading: leaderboardLoading } = useQuery({
    queryKey: ['leaderboard', leaderboardType],
    queryFn: () => gamificationService.getLeaderboard(leaderboardType, 20),
    enabled: !!user && activeTab === 'leaderboard',
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
    queryClient.invalidateQueries({ queryKey: ['arena', 'monsters'] });
  };

  const handleTabChange = (tab: Tab) => {
    setActiveTab(tab);
    hapticFeedback('light');
  };

  // Leaderboard helpers
  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1:
        return <Crown className="w-5 h-5 text-yellow-400" />;
      case 2:
        return <Medal className="w-5 h-5 text-gray-300" />;
      case 3:
        return <Medal className="w-5 h-5 text-amber-600" />;
      default:
        return <span className="w-5 h-5 flex items-center justify-center text-sm text-gray-400">{rank}</span>;
    }
  };

  const getRankBg = (rank: number) => {
    switch (rank) {
      case 1:
        return 'bg-gradient-to-r from-yellow-500/20 to-amber-500/20 border-yellow-500/30';
      case 2:
        return 'bg-gradient-to-r from-gray-400/20 to-gray-300/20 border-gray-400/30';
      case 3:
        return 'bg-gradient-to-r from-amber-600/20 to-orange-600/20 border-amber-600/30';
      default:
        return 'bg-gray-800/50 border-gray-700/50';
    }
  };

  const monsters = monstersData?.data?.monsters || [];
  const character = characterData?.data?.character;
  const leaderboard = leaderboardData?.data?.leaderboard || [];
  const isLoading = monstersLoading || characterLoading;

  if (!user) {
    return (
      <div className="p-4 text-center">
        <p className="text-gray-500">Войдите чтобы попасть на арену</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-4 pt-safe pb-24">
      {/* Header */}
      <div className="text-center mb-4">
        <Swords className="w-10 h-10 text-purple-500 mx-auto mb-2" />
        <h1 className="text-2xl font-bold text-white">Арена</h1>
        <p className="text-sm text-gray-400">Сражайся и получай награды</p>
      </div>

      {/* Tab Switcher */}
      {gameState === 'select' && (
        <div className="flex gap-2 p-1 bg-gray-800 rounded-xl mb-4">
          <button
            onClick={() => handleTabChange('battle')}
            className={cn(
              'flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2',
              activeTab === 'battle'
                ? 'bg-purple-500 text-white'
                : 'text-gray-400 hover:text-white'
            )}
          >
            <Swords className="w-4 h-4" />
            Бой
          </button>
          <button
            onClick={() => handleTabChange('leaderboard')}
            className={cn(
              'flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2',
              activeTab === 'leaderboard'
                ? 'bg-purple-500 text-white'
                : 'text-gray-400 hover:text-white'
            )}
          >
            <Trophy className="w-4 h-4" />
            Рейтинг
          </button>
        </div>
      )}

      {/* Battle Tab */}
      {activeTab === 'battle' && (
        <>
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
                        {monster.sprite_url ? (
                          <img
                            src={monster.sprite_url}
                            alt={monster.name}
                            className={`w-16 h-16 rounded-xl object-cover ${
                              monster.is_boss
                                ? 'border-2 border-red-500/50'
                                : ''
                            }`}
                          />
                        ) : (
                          <div
                            className={`w-16 h-16 rounded-xl flex items-center justify-center text-4xl ${
                              monster.is_boss
                                ? 'bg-gradient-to-br from-red-500/20 to-orange-500/20 border border-red-500/30'
                                : 'bg-gray-700'
                            }`}
                          >
                            {monster.emoji}
                          </div>
                        )}
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h3 className="font-medium text-white">{monster.name}</h3>
                            {monster.is_boss && (
                              <Star className="w-4 h-4 text-yellow-500" />
                            )}
                          </div>
                          {monster.description && (
                            <p className="text-xs text-gray-500 line-clamp-1">{monster.description}</p>
                          )}
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
                <div className="fixed bottom-24 left-4 right-4 max-w-md mx-auto">
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
                  {battleResult.monster.sprite_url ? (
                    <img
                      src={battleResult.monster.sprite_url}
                      alt={battleResult.monster.name}
                      className="w-20 h-20 rounded-xl object-cover mb-2"
                    />
                  ) : (
                    <div className="w-20 h-20 rounded-xl bg-gray-700 flex items-center justify-center text-4xl mb-2">
                      {battleResult.monster.emoji}
                    </div>
                  )}
                  <p className="text-sm text-white">{battleResult.monster.name}</p>
                </div>
              </div>

              {/* Current action */}
              {battleResult.battle_log[currentLogIndex] && (() => {
                const log = battleResult.battle_log[currentLogIndex];
                const isPlayer = log.actor === 'player';
                const isCrit = log.is_critical || log.action === 'critical' || log.action === 'critical_combo';
                const isCombo = log.is_combo || log.action === 'combo' || log.action === 'critical_combo';
                const isMiss = log.action === 'miss';
                const isSpecial = log.action === 'special';

                let emoji = isPlayer ? '⚔️' : '💥';
                let actionText = isPlayer ? 'Вы атакуете!' : `${battleResult.monster.name} атакует!`;

                if (isMiss) {
                  emoji = '💨';
                  actionText = isPlayer ? 'Вы промахнулись!' : 'Вы уклонились!';
                } else if (isCrit && isCombo) {
                  emoji = '🔥';
                  actionText = isPlayer ? 'Критическое комбо!' : 'Мощный удар!';
                } else if (isCrit) {
                  emoji = '💫';
                  actionText = isPlayer ? 'Критический удар!' : 'Критический удар!';
                } else if (isCombo) {
                  emoji = '⚡';
                  actionText = isPlayer ? 'Комбо!' : 'Серия атак!';
                } else if (isSpecial) {
                  emoji = '✨';
                  actionText = isPlayer ? 'Особая атака!' : 'Особая атака!';
                }

                return (
                  <Card className={cn(
                    "text-center p-6 transition-all",
                    isCrit && "ring-2 ring-yellow-500 bg-yellow-500/10",
                    isCombo && !isCrit && "ring-2 ring-blue-500 bg-blue-500/10",
                    isMiss && "bg-gray-700/50"
                  )}>
                    <div className={cn(
                      "text-4xl mb-4",
                      isCrit && "animate-pulse"
                    )}>
                      {emoji}
                    </div>
                    <p className="text-white font-medium">{actionText}</p>
                    {log.message && (
                      <p className="text-sm text-purple-400 mt-1">{log.message}</p>
                    )}
                    {!isMiss && (
                      <p className={cn(
                        "text-2xl font-bold mt-2",
                        isCrit ? "text-yellow-400" : isCombo ? "text-blue-400" : "text-red-400"
                      )}>
                        -{log.damage}
                      </p>
                    )}
                    <p className="text-sm text-gray-400 mt-2">
                      Раунд {log.round}
                    </p>
                  </Card>
                );
              })()}
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
        </>
      )}

      {/* Leaderboard Tab */}
      {activeTab === 'leaderboard' && gameState === 'select' && (
        <>
          {/* Leaderboard Type Toggle */}
          <div className="flex gap-2 p-1 bg-gray-800 rounded-xl mb-4">
            <button
              onClick={() => setLeaderboardType('weekly')}
              className={cn(
                'flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all',
                leaderboardType === 'weekly'
                  ? 'bg-purple-500 text-white'
                  : 'text-gray-400 hover:text-white'
              )}
            >
              За неделю
            </button>
            <button
              onClick={() => setLeaderboardType('all_time')}
              className={cn(
                'flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all',
                leaderboardType === 'all_time'
                  ? 'bg-purple-500 text-white'
                  : 'text-gray-400 hover:text-white'
              )}
            >
              Все время
            </button>
          </div>

          {/* Leaderboard */}
          {leaderboardLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <Card key={i} className="animate-pulse">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-gray-700 rounded-full" />
                    <div className="flex-1">
                      <div className="h-4 bg-gray-700 rounded w-1/3 mb-2" />
                      <div className="h-3 bg-gray-700 rounded w-1/4" />
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          ) : leaderboard.length === 0 ? (
            <Card className="text-center py-8">
              <Star className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400">Пока нет участников</p>
              <p className="text-sm text-gray-500 mt-1">
                Будь первым в рейтинге!
              </p>
            </Card>
          ) : (
            <div className="space-y-2">
              {leaderboard.map((entry) => {
                const isCurrentUser = entry.user_id === user.id;

                return (
                  <div
                    key={entry.user_id}
                    className={cn(
                      'flex items-center gap-3 p-3 rounded-xl border transition-all',
                      getRankBg(entry.rank),
                      isCurrentUser && 'ring-2 ring-purple-500'
                    )}
                  >
                    {/* Rank */}
                    <div className="w-8 flex items-center justify-center">
                      {getRankIcon(entry.rank)}
                    </div>

                    {/* Avatar */}
                    <div
                      className={cn(
                        'w-10 h-10 rounded-full flex items-center justify-center text-white font-bold',
                        entry.rank === 1
                          ? 'bg-gradient-to-br from-yellow-400 to-amber-500'
                          : entry.rank === 2
                          ? 'bg-gradient-to-br from-gray-300 to-gray-400'
                          : entry.rank === 3
                          ? 'bg-gradient-to-br from-amber-500 to-orange-600'
                          : 'bg-gradient-to-br from-purple-500 to-blue-500'
                      )}
                    >
                      {entry.first_name?.[0] || entry.username?.[0] || '?'}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <p className={cn(
                        'font-medium truncate',
                        isCurrentUser ? 'text-purple-400' : 'text-white'
                      )}>
                        {entry.first_name || entry.username}
                        {isCurrentUser && ' (вы)'}
                      </p>
                      <div className="flex items-center gap-2 text-xs text-gray-400">
                        <span>Ур. {entry.level}</span>
                        {entry.streak_days > 0 && (
                          <span className="flex items-center gap-0.5">
                            <Flame className="w-3 h-3 text-orange-500" />
                            {entry.streak_days}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* XP */}
                    <div className="text-right">
                      <p className="font-bold text-amber-400">{entry.xp.toLocaleString()}</p>
                      <p className="text-xs text-gray-500">XP</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
