'use client';

import { useState, useEffect, useCallback } from 'react';
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
  Calendar,
  Zap,
} from 'lucide-react';
import { Card, Button } from '@/components/ui';
import { BattleCard } from '@/components/cards';
import { gamificationService, eventsService } from '@/services';
import { useAppStore } from '@/lib/store';
import { hapticFeedback, showBackButton, hideBackButton } from '@/lib/telegram';
import { cn } from '@/lib/utils';
import { useLanguage } from '@/lib/i18n';
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
  const { t } = useLanguage();

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
  const [damageNumbers, setDamageNumbers] = useState<Record<string, { damage: number; isCritical: boolean }>>({});

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

  // Active event query
  const { data: eventData } = useQuery({
    queryKey: ['events', 'active'],
    queryFn: () => eventsService.getActiveEvent(),
    enabled: !!user,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Resume active battle if exists
  useEffect(() => {
    if (activeBattleData?.data?.battle) {
      setActiveBattle(activeBattleData.data.battle);
      setGameState('battle');
    }
  }, [activeBattleData]);

  // Refetch deck data on mount to ensure fresh HP values
  useEffect(() => {
    queryClient.invalidateQueries({ queryKey: ['arena', 'monsters'] });
    queryClient.invalidateQueries({ queryKey: ['deck'] });
    queryClient.invalidateQueries({ queryKey: ['cards'] });
  }, [queryClient]);

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

        const turnLog = response.data.turn_log;
        if (turnLog.length > 0) {
          // Player attack - show damage on monster card
          const playerAction = turnLog.find(log => log.actor === 'player' && log.action !== 'card_destroyed');
          if (playerAction && playerAction.target_id && playerAction.damage) {
            setAttackingCardId(selectedPlayerCard);
            setAttackedCardId(playerAction.target_id);
            setDamageNumbers(prev => ({
              ...prev,
              [String(playerAction.target_id)]: {
                damage: playerAction.damage!,
                isCritical: playerAction.is_critical || false
              }
            }));
          }

          // Monster counter-attack - show damage on player card after delay
          setTimeout(() => {
            const monsterAction = turnLog.find(log => log.actor === 'monster' && log.action !== 'card_destroyed');
            if (monsterAction && monsterAction.target_id && monsterAction.damage) {
              setAttackingCardId(monsterAction.card_id || null);
              setAttackedCardId(monsterAction.target_id);
              setDamageNumbers(prev => ({
                ...prev,
                [String(monsterAction.target_id)]: {
                  damage: monsterAction.damage!,
                  isCritical: monsterAction.is_critical || false
                }
              }));
            }
          }, 600);
        }

        // Clear animations and update state
        setTimeout(() => {
          setShowTurnAnimation(false);
          setAttackingCardId(null);
          setAttackedCardId(null);
          setDamageNumbers({});
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
    hapticFeedback('light');

    // If user has a deck, auto-start battle with deck cards
    if (deck.length > 0) {
      const deckCardIds = deck.map((c: { id: number }) => c.id);
      setSelectedCards(deckCardIds);
      startBattleMutation.mutate({
        monsterId: monster.id,
        cardIds: deckCardIds,
      });
    } else {
      // No deck - show card selection
      setSelectedCards([]);
      setGameState('cards');
    }
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

  const handleBackToMonsters = useCallback(() => {
    setGameState('select');
    setSelectedMonster(null);
    setSelectedCards([]);
  }, []);

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
  const activeEvent = eventData?.data?.event || null;
  const isLoading = monstersLoading;

  // Get alive cards for battle UI
  const alivePlayerCards = activeBattle?.state.player_cards.filter((c) => c.alive) || [];
  const aliveMonsterCards = activeBattle?.state.monster_cards.filter((c) => c.alive) || [];

  const canAttack = selectedPlayerCard && selectedTargetCard && !executeTurnMutation.isPending;

  // Show/hide Telegram back button based on game state
  useEffect(() => {
    if (gameState === 'cards') {
      showBackButton(handleBackToMonsters);
      return () => hideBackButton();
    } else {
      hideBackButton();
    }
  }, [gameState, handleBackToMonsters]);

  if (!user) {
    return (
      <div className="p-4 text-center">
        <p className="text-gray-500">{t('loginToEnterArena')}</p>
      </div>
    );
  }

  return (
    <div className="p-4 pb-4">
      {/* Header */}
      <div className="text-center mb-4">
        <Swords className="w-10 h-10 text-purple-500 mx-auto mb-2" />
        <h1 className="text-2xl font-bold text-white">{t('arena')}</h1>
        <p className="text-sm text-gray-400">{t('arenaSubtitle')}</p>
      </div>

      {/* Active Event Banner */}
      {activeEvent && gameState === 'select' && (
        <div
          className="mb-4 rounded-xl overflow-hidden border"
          style={{
            background: `linear-gradient(135deg, ${activeEvent.theme_color}20, ${activeEvent.theme_color}40)`,
            borderColor: `${activeEvent.theme_color}60`,
          }}
        >
          <div className="p-4">
            <div className="flex items-start gap-3">
              <span className="text-3xl">{activeEvent.emoji}</span>
              <div className="flex-1">
                <h3 className="font-bold text-white">{activeEvent.name}</h3>
                {activeEvent.description && (
                  <p className="text-xs text-gray-300 mt-0.5 line-clamp-2">
                    {activeEvent.description}
                  </p>
                )}
                <div className="flex flex-wrap items-center gap-3 mt-2">
                  {activeEvent.xp_multiplier > 1 && (
                    <div
                      className="flex items-center gap-1 px-2 py-1 rounded-full text-xs font-bold text-white"
                      style={{ backgroundColor: activeEvent.theme_color }}
                    >
                      <Zap className="w-3 h-3" />
                      XP x{activeEvent.xp_multiplier}
                    </div>
                  )}
                  <div className="flex items-center gap-1 text-xs text-gray-300">
                    <Calendar className="w-3 h-3" />
                    {activeEvent.days_remaining > 0
                      ? `${activeEvent.days_remaining} ${t('daysLeft')}`
                      : t('lastDay')}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

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
            {t('battle')}
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
            {t('rating')}
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
                  <span className="text-white font-medium">{t('yourDeck')}</span>
                </div>
                <div className="text-right">
                  <span className={cn(
                    'text-lg font-bold',
                    deck.length > 0 ? 'text-green-400' : 'text-red-400'
                  )}>
                    {deck.length} {t('cards')}
                  </span>
                </div>
              </div>
              {deck.length === 0 && (
                <p className="text-sm text-red-400 mt-2">
                  {t('addCardsToDeck')}
                </p>
              )}
            </Card>
          )}

          {/* Monster Selection */}
          {gameState === 'select' && (
            <>
              <h2 className="text-lg font-semibold text-white mb-3">
                {t('selectOpponent')}
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
                  <p className="text-gray-400">{t('monstersComingSoon')}</p>
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
                              {monster.is_boss ? '5' : '3'} {t('cardsInMonsterDeck')}
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
                      {t('monsterHasCards')} {selectedMonster.is_boss ? '5' : '3'} {t('cardsInMonsterDeck')}
                    </p>
                  </div>
                </div>
              </Card>

              <h2 className="text-lg font-semibold text-white mb-2">
                {t('selectCardsForBattle')}
              </h2>
              <p className="text-sm text-gray-400 mb-3">
                {t('selected')}: {selectedCards.length}/5 ({t('minOne')})
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
                    {t('toBattle')} ({selectedCards.length} {t('cards')})
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
                  {t('round')} {activeBattle.current_round}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => forfeitMutation.mutate()}
                  disabled={forfeitMutation.isPending}
                >
                  <X className="w-4 h-4 mr-1" />
                  {t('forfeit')}
                </Button>
              </div>

              {/* Monster's Deck */}
              <div>
                <h3 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                  <span className="text-xl">{activeBattle.monster?.emoji}</span>
                  {t('monsterDeck')} ({aliveMonsterCards.length} {t('cards')})
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
                      damageReceived={damageNumbers[String(card.id)]?.damage || null}
                      isCriticalHit={damageNumbers[String(card.id)]?.isCritical || false}
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
                  {t('yourCards')} ({alivePlayerCards.length} {t('alive')})
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
                      damageReceived={damageNumbers[String(card.id)]?.damage || null}
                      isCriticalHit={damageNumbers[String(card.id)]?.isCritical || false}
                      onClick={() => card.alive && setSelectedPlayerCard(card.id as number)}
                    />
                  ))}
                </div>
              </div>

              {/* Attack Button */}
              <div className="fixed bottom-24 left-4 right-4 max-w-md mx-auto z-30">
                <Button
                  className={`w-full ${!canAttack ? 'bg-gray-600 hover:bg-gray-600 shadow-none' : ''}`}
                  onClick={handleExecuteTurn}
                  disabled={!canAttack}
                  isLoading={executeTurnMutation.isPending}
                >
                  <Target className="w-5 h-5 mr-2" />
                  {selectedPlayerCard && selectedTargetCard
                    ? t('attackButton')
                    : t('selectCardAndTarget')}
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
                    <h2 className="text-2xl font-bold text-white mb-2">{t('victory')}!</h2>
                  </>
                ) : (
                  <>
                    <Skull className="w-20 h-20 text-gray-500 mx-auto mb-4" />
                    <h2 className="text-2xl font-bold text-white mb-2">{t('defeat')}</h2>
                  </>
                )}
              </div>

              <Card className="w-full max-w-sm mb-4">
                <h3 className="font-medium text-white mb-3">{t('battleResults')}</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">{t('rounds')}</span>
                    <span className="text-white">{battleResult.rounds}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">{t('damageDealt')}</span>
                    <span className="text-green-400">{battleResult.damage_dealt}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">{t('damageTaken')}</span>
                    <span className="text-red-400">{battleResult.damage_taken}</span>
                  </div>
                  {battleResult.cards_lost.length > 0 && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">{t('cardsLost')}</span>
                      <span className="text-red-500">{battleResult.cards_lost.length}</span>
                    </div>
                  )}
                  {battleResult.won && (
                    <div className="border-t border-gray-700 pt-2 mt-2">
                      <div className="flex justify-between">
                        <span className="text-gray-400">{t('experience')}</span>
                        <span className="text-amber-400">
                          +{battleResult.xp_earned} XP
                        </span>
                      </div>
                      {battleResult.level_up && (
                        <div className="text-center pt-2 text-amber-400 font-medium">
                          🎉 {t('newLevel')}
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
                      <h3 className="font-medium text-white">{t('rewardNewCard')}</h3>
                      <p className="text-sm text-amber-400">
                        {battleResult.reward_card.name} ({battleResult.reward_card.rarity})
                      </p>
                    </div>
                  </div>
                </Card>
              )}

              <Button className="w-full max-w-sm" onClick={handleBackToSelect}>
                {t('returnToSelect')}
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
              {t('weekly')}
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
              {t('allTime')}
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
              <p className="text-gray-400">{t('noParticipants')}</p>
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
                        {isCurrentUser && ` (${t('you')})`}
                      </p>
                      <div className="flex items-center gap-2 text-xs text-gray-400">
                        <span>{t('level')} {entry.level}</span>
                        {entry.streak_days > 0 && (
                          <span className="flex items-center gap-0.5">
                            <Flame className="w-3 h-3 text-orange-500" />
                            {entry.streak_days}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-red-400">{entry.monsters_killed || 0}</p>
                      <p className="text-xs text-gray-500">{t('monsters')}</p>
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
