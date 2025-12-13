'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Swords,
  Trophy,
  Skull,
  Star,
  Medal,
  Flame,
  Crown,
  Shield,
  Check,
  Sparkles,
  X,
  Target,
} from 'lucide-react';
import { Card, Button } from '@/components/ui';
import { BattleCard } from '@/components/cards';
import { gamificationService } from '@/services';
import { useAppStore } from '@/lib/store';
import { hapticFeedback } from '@/lib/telegram';
import { cn } from '@/lib/utils';
import type {
  Monster,
  ActiveBattle,
  TurnResult,
  BattleLogEntry,
} from '@/services/gamification';

type Tab = 'battle' | 'leaderboard';
type GameState = 'select' | 'cards' | 'battle' | 'result';
type LeaderboardType = 'weekly' | 'all_time';

export default function ArenaPage() {
  const queryClient = useQueryClient();
  const { user } = useAppStore();

  // Tab state
  const [activeTab, setActiveTab] = useState<Tab>('battle');

  // Battle state
  const [gameState, setGameState] = useState<GameState>('select');
  const [selectedMonster, setSelectedMonster] = useState<Monster | null>(null);
  const [selectedCards, setSelectedCards] = useState<number[]>([]);
  const [activeBattle, setActiveBattle] = useState<ActiveBattle | null>(null);
  const [selectedPlayerCard, setSelectedPlayerCard] = useState<number | null>(null);
  const [selectedTargetCard, setSelectedTargetCard] = useState<string | null>(null);
  const [lastTurnLog, setLastTurnLog] = useState<BattleLogEntry[]>([]);
  const [battleResult, setBattleResult] = useState<TurnResult['result'] | null>(null);
  const [showTurnAnimation, setShowTurnAnimation] = useState(false);
  const [attackingCardId, setAttackingCardId] = useState<number | string | null>(null);
  const [attackedCardId, setAttackedCardId] = useState<number | string | null>(null);

  // Leaderboard state
  const [leaderboardType, setLeaderboardType] = useState<LeaderboardType>('weekly');

  // Battle queries
  const { data: monstersData, isLoading: monstersLoading } = useQuery({
    queryKey: ['arena', 'monsters'],
    queryFn: () => gamificationService.getMonsters(),
    enabled: !!user && activeTab === 'battle',
  });

  // Check for active battle on mount
  const { data: activeBattleData } = useQuery({
    queryKey: ['arena', 'active-battle'],
    queryFn: () => gamificationService.getActiveBattle(),
    enabled: !!user && activeTab === 'battle',
  });

  // Leaderboard query
  const { data: leaderboardData, isLoading: leaderboardLoading } = useQuery({
    queryKey: ['leaderboard', leaderboardType],
    queryFn: () => gamificationService.getLeaderboard(leaderboardType, 20),
    enabled: !!user && activeTab === 'leaderboard',
  });

  // Resume active battle if exists
  useEffect(() => {
    if (activeBattleData?.data?.battle) {
      setActiveBattle(activeBattleData.data.battle);
      setGameState('battle');
    }
  }, [activeBattleData]);

  // Start battle mutation
  const startBattleMutation = useMutation({
    mutationFn: ({ monsterId, cardIds }: { monsterId: number; cardIds: number[] }) =>
      gamificationService.startBattle(monsterId, cardIds),
    onSuccess: (response) => {
      if (response.success && response.data?.battle) {
        hapticFeedback('medium');
        setActiveBattle(response.data.battle);
        setGameState('battle');
      }
    },
  });

  // Execute turn mutation
  const executeTurnMutation = useMutation({
    mutationFn: ({ playerCardId, targetCardId }: { playerCardId: number; targetCardId: string }) =>
      gamificationService.executeTurn(playerCardId, targetCardId),
    onSuccess: (response) => {
      if (response.success && response.data) {
        hapticFeedback('medium');
        setLastTurnLog(response.data.turn_log);
        setShowTurnAnimation(true);

        // Trigger attack animations based on turn log
        const turnLog = response.data.turn_log;
        if (turnLog.length > 0) {
          // Player attack animation
          const playerAction = turnLog.find(log => log.actor === 'player');
          if (playerAction) {
            setAttackingCardId(selectedPlayerCard);
            setAttackedCardId(selectedTargetCard);
          }

          // Monster counter-attack animation after player attack
          setTimeout(() => {
            const monsterAction = turnLog.find(log => log.actor === 'monster');
            if (monsterAction) {
              setAttackingCardId(monsterAction.card_id || null);
              setAttackedCardId(monsterAction.target_id || null);
            }
          }, 600);
        }

        // Clear animations and update state
        setTimeout(() => {
          setShowTurnAnimation(false);
          setAttackingCardId(null);
          setAttackedCardId(null);
          setActiveBattle(response.data!.battle);
          setSelectedPlayerCard(null);
          setSelectedTargetCard(null);

          if (response.data!.status === 'won' || response.data!.status === 'lost') {
            setBattleResult(response.data!.result || null);
            setGameState('result');
            hapticFeedback(response.data!.status === 'won' ? 'success' : 'error');
          }
        }, 1500);
      }
    },
  });

  // Forfeit mutation
  const forfeitMutation = useMutation({
    mutationFn: () => gamificationService.forfeitBattle(),
    onSuccess: (response) => {
      if (response.success && response.data) {
        hapticFeedback('error');
        setBattleResult(response.data.result || null);
        setGameState('result');
      }
    },
  });

  const handleSelectMonster = (monster: Monster) => {
    setSelectedMonster(monster);
    setSelectedCards([]);
    setGameState('cards');
    hapticFeedback('light');
  };

  const handleToggleCard = (cardId: number) => {
    setSelectedCards((prev) => {
      if (prev.includes(cardId)) {
        return prev.filter((id) => id !== cardId);
      }
      if (prev.length >= 5) {
        return prev;
      }
      return [...prev, cardId];
    });
    hapticFeedback('light');
  };

  const handleStartBattle = () => {
    if (selectedMonster && selectedCards.length > 0) {
      startBattleMutation.mutate({
        monsterId: selectedMonster.id,
        cardIds: selectedCards,
      });
    }
  };

  const handleExecuteTurn = () => {
    if (selectedPlayerCard && selectedTargetCard) {
      executeTurnMutation.mutate({
        playerCardId: selectedPlayerCard,
        targetCardId: selectedTargetCard,
      });
    }
  };

  const handleBackToSelect = () => {
    setGameState('select');
    setSelectedMonster(null);
    setSelectedCards([]);
    setActiveBattle(null);
    setBattleResult(null);
    setSelectedPlayerCard(null);
    setSelectedTargetCard(null);
    queryClient.invalidateQueries({ queryKey: ['arena'] });
    queryClient.invalidateQueries({ queryKey: ['cards'] });
    queryClient.invalidateQueries({ queryKey: ['deck'] });
  };

  const handleBackToMonsters = () => {
    setGameState('select');
    setSelectedMonster(null);
    setSelectedCards([]);
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
  const deck = monstersData?.data?.deck || [];
  const leaderboard = leaderboardData?.data?.leaderboard || [];
  const isLoading = monstersLoading;

  // Get alive cards for battle UI
  const alivePlayerCards = activeBattle?.state.player_cards.filter((c) => c.alive) || [];
  const aliveMonsterCards = activeBattle?.state.monster_cards.filter((c) => c.alive) || [];

  const canAttack = selectedPlayerCard && selectedTargetCard && !executeTurnMutation.isPending;

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
        <p className="text-sm text-gray-400">Пошаговые бои картами</p>
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
          {/* Deck Status */}
          {gameState === 'select' && (
            <Card className="mb-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Shield className="w-5 h-5 text-purple-400" />
                  <span className="text-white font-medium">Твоя колода</span>
                </div>
                <div className="text-right">
                  <span className={cn(
                    'text-lg font-bold',
                    deck.length > 0 ? 'text-green-400' : 'text-red-400'
                  )}>
                    {deck.length} карт
                  </span>
                </div>
              </div>
              {deck.length === 0 && (
                <p className="text-sm text-red-400 mt-2">
                  Добавь карты в колоду в разделе &quot;Колода&quot;
                </p>
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
              ) : monsters.length === 0 ? (
                <Card className="text-center py-8">
                  <Swords className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-400">Монстры появятся скоро</p>
                </Card>
              ) : (
                <div className="space-y-3">
                  {monsters.map((monster) => (
                    <Card
                      key={monster.id}
                      className={`cursor-pointer transition-all ${
                        deck.length === 0
                          ? 'opacity-50 cursor-not-allowed'
                          : 'hover:bg-gray-700/50'
                      }`}
                      onClick={() => deck.length > 0 && handleSelectMonster(monster)}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-16 h-16 rounded-xl flex items-center justify-center overflow-hidden ${
                            monster.is_boss
                              ? 'bg-gradient-to-br from-red-500/20 to-orange-500/20 border border-red-500/30'
                              : 'bg-gray-700'
                          }`}
                        >
                          {monster.sprite_url ? (
                            <img src={monster.sprite_url} alt={monster.name} className="w-full h-full object-cover" />
                          ) : (
                            <span className="text-4xl">{monster.emoji}</span>
                          )}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h3 className="font-medium text-white">{monster.name}</h3>
                            {monster.is_boss && (
                              <Star className="w-4 h-4 text-yellow-500" />
                            )}
                          </div>
                          <div className="flex items-center gap-3 mt-1 text-xs">
                            <span className="text-purple-400">
                              {monster.is_boss ? '5 карт' : '3 карты'} в колоде
                            </span>
                          </div>
                          <div className="flex items-center gap-3 mt-1 text-xs">
                            <span className="text-red-400">ATK {monster.attack}</span>
                            <span className="text-green-400">HP {monster.hp}</span>
                          </div>
                        </div>
                        <div className="text-right text-xs">
                          <p className="text-amber-400">+{monster.xp_reward} XP</p>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </>
          )}

          {/* Card Selection */}
          {gameState === 'cards' && selectedMonster && (
            <>
              <div className="mb-4">
                <Button variant="ghost" size="sm" onClick={handleBackToMonsters}>
                  ← Назад к монстрам
                </Button>
              </div>

              <Card className="mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-lg bg-gray-700 flex items-center justify-center overflow-hidden">
                    {selectedMonster.sprite_url ? (
                      <img src={selectedMonster.sprite_url} alt={selectedMonster.name} className="w-full h-full object-cover" />
                    ) : (
                      <span className="text-2xl">{selectedMonster.emoji}</span>
                    )}
                  </div>
                  <div>
                    <h3 className="font-medium text-white">{selectedMonster.name}</h3>
                    <p className="text-xs text-purple-400">
                      У монстра {selectedMonster.is_boss ? '5' : '3'} карт в колоде
                    </p>
                  </div>
                </div>
              </Card>

              <h2 className="text-lg font-semibold text-white mb-2">
                Выбери карты для боя
              </h2>
              <p className="text-sm text-gray-400 mb-3">
                Выбрано: {selectedCards.length}/5 (мин. 1)
              </p>

              <div className="flex flex-wrap justify-center gap-3 mb-20">
                {deck.map((card) => {
                  const isSelected = selectedCards.includes(card.id);
                  const isLowHp = card.current_hp <= 0;

                  return (
                    <div key={card.id} className="relative">
                      <BattleCard
                        id={card.id}
                        name={card.name}
                        emoji={card.emoji}
                        imageUrl={card.image_url}
                        hp={card.current_hp}
                        maxHp={card.hp}
                        attack={card.attack}
                        rarity={card.rarity}
                        alive={!isLowHp}
                        selected={isSelected}
                        selectable={!isLowHp}
                        size="md"
                        onClick={() => !isLowHp && handleToggleCard(card.id)}
                      />
                      {isSelected && (
                        <div className="absolute -top-2 -right-2 w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center z-10">
                          <Check className="w-4 h-4 text-white" />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {selectedCards.length > 0 && (
                <div className="fixed bottom-24 left-4 right-4 max-w-md mx-auto">
                  <Button
                    className="w-full"
                    onClick={handleStartBattle}
                    isLoading={startBattleMutation.isPending}
                  >
                    <Swords className="w-5 h-5 mr-2" />
                    В бой! ({selectedCards.length} карт)
                  </Button>
                </div>
              )}
            </>
          )}

          {/* Turn-based Battle */}
          {gameState === 'battle' && activeBattle && (
            <div className="space-y-4">
              {/* Battle Header */}
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-400">
                  Раунд {activeBattle.current_round}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => forfeitMutation.mutate()}
                  disabled={forfeitMutation.isPending}
                >
                  <X className="w-4 h-4 mr-1" />
                  Сдаться
                </Button>
              </div>

              {/* Turn Animation */}
              {showTurnAnimation && lastTurnLog.length > 0 && (
                <Card className="bg-purple-500/20 border-purple-500/50 text-center py-6">
                  {lastTurnLog.map((log, i) => (
                    <div key={i} className="mb-2">
                      {log.actor === 'player' && (
                        <p className="text-white">
                          <span className="text-2xl">{log.card_emoji}</span>{' '}
                          {log.card_name} атакует{' '}
                          <span className="text-2xl">{log.target_emoji}</span>{' '}
                          {log.target_name}!
                          <span className={cn(
                            'block text-xl font-bold mt-1',
                            log.is_critical ? 'text-yellow-400' : 'text-red-400'
                          )}>
                            -{log.damage} {log.is_critical && '💥 Крит!'}
                          </span>
                        </p>
                      )}
                      {log.actor === 'monster' && (
                        <p className="text-white">
                          <span className="text-2xl">{log.card_emoji}</span>{' '}
                          {log.card_name} атакует{' '}
                          <span className="text-2xl">{log.target_emoji}</span>{' '}
                          {log.target_name}!
                          <span className={cn(
                            'block text-xl font-bold mt-1',
                            log.is_critical ? 'text-yellow-400' : 'text-orange-400'
                          )}>
                            -{log.damage} {log.is_critical && '💥 Крит!'}
                          </span>
                        </p>
                      )}
                      {log.actor === 'system' && (
                        <p className="text-red-400 font-medium">{log.message}</p>
                      )}
                    </div>
                  ))}
                </Card>
              )}

              {/* Monster's Deck */}
              <div>
                <h3 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                  <span className="text-xl">{activeBattle.monster?.emoji}</span>
                  Колода монстра ({aliveMonsterCards.length} карт)
                </h3>
                <div className="flex flex-wrap justify-center gap-3">
                  {activeBattle.state.monster_cards.map((card) => (
                    <BattleCard
                      key={card.id}
                      id={card.id}
                      name={card.name}
                      emoji={card.emoji}
                      hp={card.hp}
                      maxHp={card.max_hp}
                      attack={card.attack}
                      alive={card.alive}
                      selected={selectedTargetCard === card.id}
                      selectable={card.alive}
                      size="md"
                      isAttacking={attackingCardId === card.id}
                      isBeingAttacked={attackedCardId === card.id}
                      onClick={() => card.alive && setSelectedTargetCard(card.id)}
                    />
                  ))}
                </div>
              </div>

              {/* VS Divider */}
              <div className="flex items-center justify-center gap-4 py-2">
                <div className="h-px bg-gray-700 flex-1" />
                <span className="text-2xl font-bold text-purple-500">VS</span>
                <div className="h-px bg-gray-700 flex-1" />
              </div>

              {/* Player's Cards */}
              <div>
                <h3 className="text-sm font-medium text-gray-400 mb-3">
                  Твои карты ({alivePlayerCards.length} живых)
                </h3>
                <div className="flex flex-wrap justify-center gap-3">
                  {activeBattle.state.player_cards.map((card) => (
                    <BattleCard
                      key={card.id}
                      id={card.id}
                      name={card.name}
                      emoji={card.emoji}
                      imageUrl={card.image_url}
                      hp={card.hp}
                      maxHp={card.max_hp}
                      attack={card.attack}
                      rarity={card.rarity}
                      alive={card.alive}
                      selected={selectedPlayerCard === card.id}
                      selectable={card.alive}
                      size="md"
                      isAttacking={attackingCardId === card.id}
                      isBeingAttacked={attackedCardId === card.id}
                      onClick={() => card.alive && setSelectedPlayerCard(card.id as number)}
                    />
                  ))}
                </div>
              </div>

              {/* Attack Button */}
              <div className="fixed bottom-24 left-4 right-4 max-w-md mx-auto">
                <Button
                  className="w-full"
                  onClick={handleExecuteTurn}
                  disabled={!canAttack}
                  isLoading={executeTurnMutation.isPending}
                >
                  <Target className="w-5 h-5 mr-2" />
                  {selectedPlayerCard && selectedTargetCard
                    ? 'Атаковать!'
                    : 'Выбери карту и цель'}
                </Button>
              </div>
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
                  </>
                ) : (
                  <>
                    <Skull className="w-20 h-20 text-gray-500 mx-auto mb-4" />
                    <h2 className="text-2xl font-bold text-white mb-2">Поражение</h2>
                  </>
                )}
              </div>

              <Card className="w-full max-w-sm mb-4">
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
                  {battleResult.cards_lost.length > 0 && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">Потеряно карт</span>
                      <span className="text-red-500">{battleResult.cards_lost.length}</span>
                    </div>
                  )}
                  {battleResult.won && (
                    <div className="border-t border-gray-700 pt-2 mt-2">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Опыт</span>
                        <span className="text-amber-400">
                          +{battleResult.xp_earned} XP
                        </span>
                      </div>
                      {battleResult.level_up && (
                        <div className="text-center pt-2 text-amber-400 font-medium">
                          🎉 Новый уровень!
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </Card>

              {/* Reward card */}
              {battleResult.reward_card && (
                <Card className="w-full max-w-sm mb-4 bg-gradient-to-br from-amber-500/20 to-orange-500/20 border-amber-500/30">
                  <div className="flex items-center gap-3">
                    <Sparkles className="w-6 h-6 text-amber-400" />
                    <div>
                      <h3 className="font-medium text-white">Награда: новая карта!</h3>
                      <p className="text-sm text-amber-400">
                        {battleResult.reward_card.name} ({battleResult.reward_card.rarity})
                      </p>
                    </div>
                  </div>
                </Card>
              )}

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
                    <div className="w-8 flex items-center justify-center">
                      {getRankIcon(entry.rank)}
                    </div>
                    <div
                      className={cn(
                        'w-10 h-10 rounded-full flex items-center justify-center text-white font-bold',
                        entry.rank <= 3
                          ? 'bg-gradient-to-br from-purple-500 to-blue-500'
                          : 'bg-gray-700'
                      )}
                    >
                      {entry.first_name?.[0] || entry.username?.[0] || '?'}
                    </div>
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
