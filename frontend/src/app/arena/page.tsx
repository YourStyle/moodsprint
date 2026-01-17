'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter, useSearchParams } from 'next/navigation';
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
  Plus,
  Map,
} from 'lucide-react';
import { Card, Button, ScrollBackdrop } from '@/components/ui';
import { BattleCard } from '@/components/cards';
import { BattleEvent } from '@/components/battle/BattleEvent';
import { LoreSheet, DialogueSheet } from '@/components/campaign';
import { FeatureBanner } from '@/components/features';
import { gamificationService, eventsService, campaignService } from '@/services';
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
import type { LevelCompletionResult } from '@/services/campaign';

// localStorage key for hiding 0 HP cards warning
const HIDE_LOW_HP_WARNING_KEY = 'moodsprint_hide_low_hp_warning';

type Tab = 'battle' | 'leaderboard';
type GameState = 'select' | 'cards' | 'battle' | 'result';
type LeaderboardType = 'weekly' | 'all_time';

export default function ArenaPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { user, setHideNavigation } = useAppStore();
  const { t } = useLanguage();

  // Campaign mode
  const campaignLevelId = searchParams.get('campaign_level');
  const [campaignMode, setCampaignMode] = useState(!!campaignLevelId);
  const [campaignBattleConfig, setCampaignBattleConfig] = useState<{
    monster_id: number;
    monster_name: string;
    is_boss: boolean;
    scaled_stats: { hp: number; attack: number; defense: number; xp_reward: number };
  } | null>(null);
  const [campaignResult, setCampaignResult] = useState<LevelCompletionResult | null>(null);
  const [showCampaignOutro, setShowCampaignOutro] = useState(false);
  const [showDialogueAfter, setShowDialogueAfter] = useState(false);

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
  const [damageNumbers, setDamageNumbers] = useState<Record<string, { damage: number; isCritical: boolean; key: number }>>({});

  // Heal targeting state
  const [healTargetMode, setHealTargetMode] = useState(false);
  const [healingCardId, setHealingCardId] = useState<number | null>(null);
  const [healNumbers, setHealNumbers] = useState<Record<string, number>>({});

  // Ability targeting state (for poison, double_strike)
  const [abilityTargetMode, setAbilityTargetMode] = useState(false);
  const [abilityCardId, setAbilityCardId] = useState<number | null>(null);
  const [currentAbilityType, setCurrentAbilityType] = useState<string | null>(null);

  // Random battle events
  const [battleEvent, setBattleEvent] = useState<{
    id: string;
    type: 'buff' | 'debuff' | 'heal' | 'revive' | 'damage';
    target: 'player' | 'monster';
    title: string;
    description: string;
    emoji: string;
  } | null>(null);

  // Battle events pool
  const battleEvents = [
    { type: 'buff' as const, target: 'player' as const, title: 'Прилив сил!', description: '+20% к атаке на этот ход', emoji: '💪' },
    { type: 'buff' as const, target: 'player' as const, title: 'Божественное благословение', description: 'Следующая атака нанесёт критический урон', emoji: '✨' },
    { type: 'debuff' as const, target: 'monster' as const, title: 'Монстр ослаблен', description: '-20% к защите противника', emoji: '😵' },
    { type: 'heal' as const, target: 'player' as const, title: 'Исцеляющий ветер', description: 'Все карты восстановили немного HP', emoji: '🍀' },
    { type: 'damage' as const, target: 'player' as const, title: 'Ловушка!', description: 'Случайная карта получила урон', emoji: '💥' },
    { type: 'damage' as const, target: 'monster' as const, title: 'Метеорит!', description: 'Монстр получил урон с небес', emoji: '☄️' },
  ];

  // Leaderboard state
  const [leaderboardType, setLeaderboardType] = useState<LeaderboardType>('weekly');

  // Campaign loading state
  const [campaignLoading, setCampaignLoading] = useState(!!campaignLevelId);

  // Error state
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Low HP cards warning state
  const [showLowHpWarning, setShowLowHpWarning] = useState(false);
  const [pendingMonster, setPendingMonster] = useState<Monster | null>(null);

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

  // Resume active battle if exists and is still active
  useEffect(() => {
    if (activeBattleData?.data?.battle) {
      const battle = activeBattleData.data.battle;
      // Only resume if battle is truly active (not won or lost)
      if (battle.status === 'active') {
        setActiveBattle(battle);
        setGameState('battle');
      }
    }
  }, [activeBattleData]);

  // Refetch deck data on mount to ensure fresh HP values
  useEffect(() => {
    queryClient.invalidateQueries({ queryKey: ['arena', 'monsters'] });
    queryClient.invalidateQueries({ queryKey: ['deck'] });
    queryClient.invalidateQueries({ queryKey: ['cards'] });
  }, [queryClient]);

  // Preload monster images when data is fetched
  useEffect(() => {
    if (monstersData?.data?.monsters) {
      monstersData.data.monsters.forEach((monster) => {
        if (monster.sprite_url) {
          const img = new Image();
          img.src = monster.sprite_url;
        }
      });
    }
  }, [monstersData]);

  // Start battle mutation
  const startBattleMutation = useMutation({
    mutationFn: ({ monsterId, cardIds, campaignLevelId }: { monsterId: number; cardIds: number[]; campaignLevelId?: number }) =>
      gamificationService.startBattle(monsterId, cardIds, campaignLevelId),
    onSuccess: (response) => {
      if (response.success && response.data?.battle) {
        hapticFeedback('medium');
        setActiveBattle(response.data.battle);
        setGameState('battle');
      } else if (!response.success && response.error) {
        // Handle API error response (including rate limit)
        hapticFeedback('error');
        setErrorMessage(response.error.message || 'Не удалось начать бой');
        // Reset battle started ref so user can try again
        battleStartedRef.current = false;
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
                isCritical: playerAction.is_critical || false,
                key: Date.now()
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
                  isCritical: monsterAction.is_critical || false,
                  key: Date.now()
                }
              }));
            }
          }, 600);
        }

        // Clear animations and update state
        setTimeout(async () => {
          setShowTurnAnimation(false);
          setAttackingCardId(null);
          setAttackedCardId(null);
          setDamageNumbers({});
          setActiveBattle(response.data!.battle);
          setSelectedPlayerCard(null);
          setSelectedTargetCard(null);

          // Trigger random battle event (10% chance)
          if (response.data!.status === 'continue') {
            triggerRandomEvent();
          }

          if (response.data!.status === 'won' || response.data!.status === 'lost') {
            const result = response.data!.result;
            setBattleResult(result || null);

            // Handle campaign level completion
            if (campaignMode && campaignLevelId) {
              try {
                const completionData = {
                  won: response.data!.status === 'won',
                  rounds: result?.rounds || 0,
                  hp_remaining: response.data!.battle.state.player_cards
                    .filter(c => c.alive)
                    .reduce((sum, c) => sum + c.hp, 0),
                  cards_lost: result?.cards_lost?.length || 0,
                };

                const completionResponse = await campaignService.completeLevel(
                  Number(campaignLevelId),
                  completionData
                );

                if (completionResponse.success && completionResponse.data) {
                  setCampaignResult(completionResponse.data);

                  // Show dialogue_after first, then story_outro
                  if (completionResponse.data.dialogue_after?.length) {
                    setShowDialogueAfter(true);
                  } else if (completionResponse.data.story_outro) {
                    setShowCampaignOutro(true);
                  }
                }
              } catch (error) {
                console.error('Failed to complete campaign level:', error);
              }
            }

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
    hapticFeedback('light');
    setErrorMessage(null); // Clear any previous error

    // If user has a deck, check for low HP cards first
    if (deck.length > 0) {
      const lowHpCards = deck.filter((c: { current_hp: number }) => c.current_hp <= 0);
      const hideWarning = typeof window !== 'undefined' && localStorage.getItem(HIDE_LOW_HP_WARNING_KEY) === 'true';

      if (lowHpCards.length > 0 && !hideWarning) {
        // Show warning modal
        setPendingMonster(monster);
        setShowLowHpWarning(true);
        return;
      }

      // Proceed with battle
      setSelectedMonster(monster);
      const deckCardIds = deck.map((c: { id: number }) => c.id);
      setSelectedCards(deckCardIds);
      startBattleMutation.mutate({
        monsterId: monster.id,
        cardIds: deckCardIds,
        campaignLevelId: campaignLevelId ? Number(campaignLevelId) : undefined,
      });
    } else {
      // No deck - show card selection
      setSelectedMonster(monster);
      setSelectedCards([]);
      setGameState('cards');
    }
  };

  // Handle low HP warning actions
  const handleLowHpWarningContinue = () => {
    setShowLowHpWarning(false);
    if (pendingMonster && deck.length > 0) {
      setSelectedMonster(pendingMonster);
      const deckCardIds = deck.map((c: { id: number }) => c.id);
      setSelectedCards(deckCardIds);
      startBattleMutation.mutate({
        monsterId: pendingMonster.id,
        cardIds: deckCardIds,
        campaignLevelId: campaignLevelId ? Number(campaignLevelId) : undefined,
      });
    }
    setPendingMonster(null);
  };

  const handleLowHpWarningDontShow = () => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(HIDE_LOW_HP_WARNING_KEY, 'true');
    }
    handleLowHpWarningContinue();
  };

  const handleLowHpWarningGoHome = () => {
    setShowLowHpWarning(false);
    setPendingMonster(null);
    router.push('/');
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
        campaignLevelId: campaignLevelId ? Number(campaignLevelId) : undefined,
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
    // In campaign mode, go back to campaign page
    // Use replace to avoid keeping arena in history (prevents back button returning to battle)
    if (campaignMode) {
      router.replace('/campaign');
      return;
    }

    setGameState('select');
    setSelectedMonster(null);
    setSelectedCards([]);
    setActiveBattle(null);
    setBattleResult(null);
    setSelectedPlayerCard(null);
    setSelectedTargetCard(null);
    setCampaignResult(null);
    setShowCampaignOutro(false);
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

  // Handle ability button click
  const handleAbilityClick = async (cardId: number, abilityType: string) => {
    hapticFeedback('medium');

    if (abilityType === 'heal') {
      // Enter heal target mode (select ally)
      setHealTargetMode(true);
      setHealingCardId(cardId);
      setCurrentAbilityType('heal');
    } else if (abilityType === 'shield') {
      // Shield can target any ally - enter heal target mode (reuse for ally targeting)
      setHealTargetMode(true);
      setHealingCardId(cardId);
      setCurrentAbilityType('shield');
    } else if (abilityType === 'poison' || abilityType === 'double_strike') {
      // If enemy target is already selected, execute immediately
      if (selectedTargetCard) {
        await executeAbilityOnTarget(cardId, abilityType, selectedTargetCard);
      } else {
        // Enter ability target mode (select enemy)
        setAbilityTargetMode(true);
        setAbilityCardId(cardId);
        setCurrentAbilityType(abilityType);
      }
    }
  };

  // Execute ability on target (for poison, double_strike)
  const executeAbilityOnTarget = async (cardId: number, abilityType: string, targetId: string) => {
    hapticFeedback('success');

    // Clear selections
    setSelectedPlayerCard(null);
    setSelectedTargetCard(null);
    setAbilityTargetMode(false);
    setAbilityCardId(null);
    setCurrentAbilityType(null);

    try {
      const response = await gamificationService.useAbility(cardId, targetId);
      if (response.success && response.data) {
        const turnLog = response.data.turn_log || [];
        setLastTurnLog(turnLog);
        setShowTurnAnimation(true);

        // Update battle state IMMEDIATELY so HP bars update
        if (response.data.battle) {
          setActiveBattle(response.data.battle);
        }

        // Player ability animation
        const abilityAction = turnLog.find(log => log.actor === 'player' && log.action === 'ability');
        if (abilityAction) {
          setAttackingCardId(cardId);
          setAttackedCardId(targetId);

          // Special handling for double_strike - show two damage numbers
          if (abilityAction.ability === 'double_strike' && abilityAction.damage1 !== undefined) {
            // First hit
            setDamageNumbers(prev => ({
              ...prev,
              [String(targetId)]: {
                damage: abilityAction.damage1!,
                isCritical: false,
                key: Date.now()
              }
            }));
            // Second hit after delay
            setTimeout(() => {
              setDamageNumbers(prev => ({
                ...prev,
                [String(targetId)]: {
                  damage: abilityAction.damage2!,
                  isCritical: false,
                  key: Date.now()
                }
              }));
            }, 400);
          } else if (abilityAction.damage) {
            setDamageNumbers(prev => ({
              ...prev,
              [String(targetId)]: {
                damage: abilityAction.damage!,
                isCritical: false,
                key: Date.now()
              }
            }));
          }
        }

        // Monster counter-attack after delay (longer for double_strike)
        const monsterDelay = abilityAction?.ability === 'double_strike' ? 1000 : 600;
        setTimeout(() => {
          const monsterAction = turnLog.find(log => log.actor === 'monster' && log.action !== 'card_destroyed');
          if (monsterAction && monsterAction.target_id && monsterAction.damage) {
            setAttackingCardId(monsterAction.card_id || null);
            setAttackedCardId(monsterAction.target_id);
            setDamageNumbers(prev => ({
              ...prev,
              [String(monsterAction.target_id)]: {
                damage: monsterAction.damage!,
                isCritical: monsterAction.is_critical || false,
                key: Date.now()
              }
            }));
          }
        }, monsterDelay);

        // Clear animations (longer for double_strike)
        const clearDelay = abilityAction?.ability === 'double_strike' ? 1800 : 1500;
        setTimeout(() => {
          setShowTurnAnimation(false);
          setAttackingCardId(null);
          setAttackedCardId(null);
          setDamageNumbers({});
        }, clearDelay);

        // Check if battle ended (longer delay for double_strike)
        if (response.data.status === 'won' || response.data.status === 'lost') {
          const resultDelay = abilityAction?.ability === 'double_strike' ? 1900 : 1600;
          setTimeout(() => {
            setBattleResult(response.data!.result || null);
            setGameState('result');
            hapticFeedback(response.data!.status === 'won' ? 'success' : 'error');
          }, resultDelay);
        }
      }
    } catch (error) {
      console.error(`Failed to use ${abilityType}:`, error);
    }
  };

  // Handle heal/shield target selection (both target allies)
  const handleHealTarget = async (targetCardId: number) => {
    if (!healingCardId) return;

    hapticFeedback('success');

    // Store and exit heal mode immediately for better UX
    const usedCardId = healingCardId;
    const isShield = currentAbilityType === 'shield';
    setHealTargetMode(false);
    setHealingCardId(null);
    setCurrentAbilityType(null);
    setSelectedPlayerCard(null);

    // Execute ability via API
    try {
      const response = await gamificationService.useAbility(usedCardId, targetCardId);
      if (response.success && response.data) {
        const turnLog = response.data.turn_log || [];
        setLastTurnLog(turnLog);
        setShowTurnAnimation(true);

        // Update battle state IMMEDIATELY so HP bars update right away
        if (response.data.battle) {
          setActiveBattle(response.data.battle);
        }

        // Show heal number on target (only for heal, not shield)
        if (!isShield && response.data.heal_amount) {
          setHealNumbers(prev => ({
            ...prev,
            [String(targetCardId)]: response.data!.heal_amount || 0
          }));
        }

        // Monster counter-attack after ability (with delay for animation)
        setTimeout(() => {
          const monsterAction = turnLog.find(log => log.actor === 'monster' && log.action !== 'card_destroyed');
          if (monsterAction && monsterAction.target_id && monsterAction.damage) {
            setAttackingCardId(monsterAction.card_id || null);
            setAttackedCardId(monsterAction.target_id);
            setDamageNumbers(prev => ({
              ...prev,
              [String(monsterAction.target_id)]: {
                damage: monsterAction.damage!,
                isCritical: monsterAction.is_critical || false,
                key: Date.now()
              }
            }));
          }
        }, 500);

        // Clear animations
        setTimeout(() => {
          setShowTurnAnimation(false);
          setAttackingCardId(null);
          setAttackedCardId(null);
          setHealNumbers({});
          setDamageNumbers({});
        }, 1500);

        // Check if battle ended
        if (response.data.status === 'won' || response.data.status === 'lost') {
          setTimeout(() => {
            setBattleResult(response.data!.result || null);
            setGameState('result');
            hapticFeedback(response.data!.status === 'won' ? 'success' : 'error');
          }, 1600);
        }
      }
    } catch (error) {
      console.error('Failed to use ability:', error);
    }
  };

  // Cancel heal/shield target mode
  const cancelHealMode = () => {
    setHealTargetMode(false);
    setHealingCardId(null);
    setCurrentAbilityType(null);
  };

  // Handle ability target selection (poison, double_strike - targets enemy)
  const handleAbilityTarget = async (targetCardId: string) => {
    if (!abilityCardId || !currentAbilityType) return;
    await executeAbilityOnTarget(abilityCardId, currentAbilityType, targetCardId);
  };

  // Cancel ability target mode
  const cancelAbilityMode = () => {
    setAbilityTargetMode(false);
    setAbilityCardId(null);
    setCurrentAbilityType(null);
  };

  // Trigger random battle event (10% chance per turn)
  const triggerRandomEvent = useCallback(() => {
    if (Math.random() < 0.1) { // 10% chance
      const randomEvent = battleEvents[Math.floor(Math.random() * battleEvents.length)];
      setBattleEvent({
        ...randomEvent,
        id: `event-${Date.now()}`
      });
    }
  }, [battleEvents]);

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

  // Sort monsters: event monsters first, then regular monsters
  const monsters = (monstersData?.data?.monsters || []).sort((a, b) => {
    if (a.is_event_monster && !b.is_event_monster) return -1;
    if (!a.is_event_monster && b.is_event_monster) return 1;
    return 0;
  });
  const deck = monstersData?.data?.deck || [];
  const leaderboard = leaderboardData?.data?.leaderboard || [];
  const activeEvent = eventData?.data?.event || null;
  const isLoading = monstersLoading;

  // Get alive cards for battle UI
  const alivePlayerCards = activeBattle?.state.player_cards.filter((c) => c.alive) || [];
  const aliveMonsterCards = activeBattle?.state.monster_cards.filter((c) => c.alive) || [];

  const canAttack = selectedPlayerCard && selectedTargetCard && !executeTurnMutation.isPending;

  // Campaign mode initialization
  useEffect(() => {
    if (!campaignLevelId || !user) {
      setCampaignLoading(false);
      return;
    }

    const initCampaignBattle = async () => {
      try {
        // Get battle config for this campaign level
        const configResponse = await campaignService.getLevelBattleConfig(Number(campaignLevelId));
        if (!configResponse.success || !configResponse.data) {
          console.error('Failed to get campaign battle config:', configResponse);
          setCampaignLoading(false);
          setCampaignMode(false);
          router.replace('/campaign');
          return;
        }

        const config = configResponse.data;
        setCampaignBattleConfig(config);
        setCampaignMode(true);

        // Find the monster in the list or create a virtual monster
        const existingMonster = monsters.find(m => m.id === config.monster_id);

        // Create monster object with campaign stats
        const scaledMonster: Monster = existingMonster ? {
          ...existingMonster,
          hp: config.scaled_stats.hp,
          attack: config.scaled_stats.attack,
          xp_reward: config.scaled_stats.xp_reward,
          is_boss: config.is_boss,
        } : {
          // Fallback: create virtual monster from config
          id: config.monster_id,
          name: config.monster_name,
          emoji: '👹',
          genre: 'campaign',
          level: 1,
          hp: config.scaled_stats.hp,
          attack: config.scaled_stats.attack,
          defense: config.scaled_stats.defense,
          speed: 10,
          xp_reward: config.scaled_stats.xp_reward,
          stat_points_reward: 0,
          sprite_url: null,
          is_boss: config.is_boss,
          is_event_monster: false,
        };

        setSelectedMonster(scaledMonster);
        setCampaignLoading(false);
      } catch (error) {
        console.error('Campaign battle init error:', error);
        setCampaignLoading(false);
        setCampaignMode(false);
        router.replace('/campaign');
      }
    };

    if (monstersData?.data?.monsters && monstersData.data.deck && monstersData.data.deck.length > 0) {
      initCampaignBattle();
    } else if (monstersData?.data && (!monstersData.data.deck || monstersData.data.deck.length === 0)) {
      // No deck available - redirect to campaign
      console.error('No deck available for campaign battle');
      setCampaignLoading(false);
      router.replace('/campaign');
    }
  }, [campaignLevelId, user, monstersData, router, monsters]);

  // Auto-start battle in campaign mode when monster and deck are ready
  const battleStartedRef = useRef(false);
  const lastCampaignLevelRef = useRef<string | null>(null);

  // Reset battle started ref when campaign level changes
  useEffect(() => {
    if (campaignLevelId !== lastCampaignLevelRef.current) {
      battleStartedRef.current = false;
      lastCampaignLevelRef.current = campaignLevelId;
    }
  }, [campaignLevelId]);

  useEffect(() => {
    if (!campaignMode || !selectedMonster || !campaignBattleConfig) return;
    if (gameState !== 'select') return;
    if (battleStartedRef.current) return; // Already started

    if (deck.length > 0 && !activeBattle) {
      battleStartedRef.current = true;
      const deckCardIds = deck.map((c: { id: number }) => c.id);
      setSelectedCards(deckCardIds);
      startBattleMutation.mutate({
        monsterId: selectedMonster.id,
        cardIds: deckCardIds,
        campaignLevelId: campaignLevelId ? Number(campaignLevelId) : undefined,
      });
    }
  }, [campaignMode, selectedMonster, campaignBattleConfig, gameState, deck, activeBattle, campaignLevelId]);

  // Show/hide Telegram back button based on game state
  useEffect(() => {
    if (gameState === 'cards') {
      showBackButton(handleBackToMonsters);
      return () => hideBackButton();
    } else {
      hideBackButton();
    }
  }, [gameState, handleBackToMonsters]);

  // Hide navigation during battle and result screens
  useEffect(() => {
    const shouldHide = gameState === 'battle' || gameState === 'result';
    setHideNavigation(shouldHide);
    return () => setHideNavigation(false);
  }, [gameState, setHideNavigation]);

  if (!user) {
    return (
      <div className="p-4 text-center">
        <p className="text-gray-500">{t('loginToEnterArena')}</p>
      </div>
    );
  }

  // Campaign loading screen
  if (campaignMode && (campaignLoading || (gameState === 'select' && !activeBattle))) {
    return (
      <div className="p-4 flex flex-col items-center justify-center min-h-[60vh]">
        <Map className="w-16 h-16 text-purple-500 animate-pulse mb-4" />
        <h2 className="text-xl font-bold text-white mb-2">Загрузка уровня...</h2>
        <p className="text-gray-400 text-sm">Подготовка к битве</p>
        {selectedMonster && (
          <div className="mt-6 text-center">
            <div className="w-20 h-20 rounded-xl bg-gradient-to-br from-red-500/20 to-orange-500/20 border border-red-500/30 flex items-center justify-center mx-auto mb-2 overflow-hidden">
              {selectedMonster.sprite_url ? (
                <img src={selectedMonster.sprite_url} alt={selectedMonster.name} className="w-full h-full object-cover" />
              ) : (
                <span className="text-4xl">{selectedMonster.emoji}</span>
              )}
            </div>
            <p className="text-white font-medium">{selectedMonster.name}</p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="p-4 pb-4">
      <ScrollBackdrop />
      {/* Header - hidden during battle and result */}
      {gameState !== 'battle' && gameState !== 'result' && (
        <div className="text-center mb-4">
          <Swords className="w-10 h-10 text-purple-500 mx-auto mb-2" />
          <h1 className="text-2xl font-bold text-white">{t('arena')}</h1>
          <p className="text-sm text-gray-400">{t('arenaSubtitle')}</p>
        </div>
      )}

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
        <div className="flex gap-1 p-1 bg-gray-800 rounded-xl mb-4">
          <button
            onClick={() => handleTabChange('battle')}
            className={cn(
              'flex-1 py-2 px-2 sm:px-4 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-1.5',
              activeTab === 'battle'
                ? 'bg-purple-500 text-white'
                : 'text-gray-400 hover:text-white'
            )}
          >
            <Swords className="w-4 h-4" />
            <span>{t('battle')}</span>
          </button>
          <button
            onClick={() => handleTabChange('leaderboard')}
            className={cn(
              'flex-1 py-2 px-2 sm:px-4 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-1.5',
              activeTab === 'leaderboard'
                ? 'bg-purple-500 text-white'
                : 'text-gray-400 hover:text-white'
            )}
          >
            <Trophy className="w-4 h-4" />
            <span>{t('rating')}</span>
          </button>
        </div>
      )}

      {/* Campaign Banner */}
      {gameState === 'select' && (
        <div className="mb-4">
          <FeatureBanner type="campaign" />
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
                  {/* Event monsters first */}
                  {monsters.filter(m => m.is_event_monster).length > 0 && (
                    <div className="mb-2">
                      <h3 className="text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-amber-400" />
                        {t('eventMonsters')}
                      </h3>
                    </div>
                  )}
                  {monsters.map((monster) => (
                    <Card
                      key={monster.id}
                      className={cn(
                        'cursor-pointer transition-all',
                        deck.length === 0
                          ? 'opacity-50 cursor-not-allowed'
                          : 'hover:bg-gray-700/50',
                        monster.is_event_monster && 'ring-2 ring-amber-500/50 bg-gradient-to-r from-amber-500/10 to-orange-500/10'
                      )}
                      onClick={() => deck.length > 0 && handleSelectMonster(monster)}
                    >
                      {/* Event badge */}
                      {monster.is_event_monster && (
                        <div className="flex items-center gap-1.5 mb-2 px-2 py-1 bg-amber-500/20 rounded-lg w-fit">
                          <span className="text-sm">{monster.event_emoji || '🎄'}</span>
                          <span className="text-xs font-medium text-amber-400">{monster.event_name || t('event')}</span>
                        </div>
                      )}
                      <div className="flex items-center gap-3">
                        <div
                          className={cn(
                            'w-16 h-16 rounded-xl flex items-center justify-center overflow-hidden',
                            monster.is_event_monster
                              ? 'bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/30'
                              : monster.is_boss
                                ? 'bg-gradient-to-br from-red-500/20 to-orange-500/20 border border-red-500/30'
                                : 'bg-gray-700'
                          )}
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
                            {monster.is_event_monster && (
                              <Sparkles className="w-4 h-4 text-amber-400" />
                            )}
                          </div>
                          <div className="flex items-center gap-3 mt-1 text-xs">
                            <span className="text-purple-400">
                              {monster.is_boss ? '5' : '3'} {t('cardsInMonsterDeck')}
                            </span>
                            {monster.guaranteed_rarity && (
                              <span className="text-amber-400">
                                🎁 {monster.guaranteed_rarity}
                              </span>
                            )}
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
                  {abilityTargetMode && currentAbilityType && (
                    <span className="ml-2 text-purple-400 animate-pulse">
                      — Выберите цель для {currentAbilityType === 'poison' ? 'яда' : 'атаки'}
                    </span>
                  )}
                </h3>
                <div className="flex flex-wrap justify-center gap-3">
                  {activeBattle.state.monster_cards.map((card) => {
                    const isAbilityTarget = abilityTargetMode && card.alive;

                    return (
                      <div key={card.id} className="relative">
                        <BattleCard
                          id={card.id}
                          name={card.name}
                          emoji={card.emoji}
                          hp={card.hp}
                          maxHp={card.max_hp}
                          attack={card.attack}
                          alive={card.alive}
                          selected={selectedTargetCard === card.id}
                          selectable={card.alive && !healTargetMode}
                          size="md"
                          isAttacking={attackingCardId === card.id}
                          isBeingAttacked={attackedCardId === card.id}
                          damageReceived={damageNumbers[String(card.id)]?.damage || null}
                          damageKey={damageNumbers[String(card.id)]?.key}
                          isCriticalHit={damageNumbers[String(card.id)]?.isCritical || false}
                          hasShield={card.has_shield || false}
                          statusEffects={card.status_effects || []}
                          onClick={() => {
                            if (abilityTargetMode && card.alive) {
                              handleAbilityTarget(card.id);
                            } else if (card.alive && !healTargetMode) {
                              setSelectedTargetCard(card.id);
                            }
                          }}
                        />
                        {/* Ability target highlight */}
                        {isAbilityTarget && (
                          <div className={cn(
                            'absolute inset-0 rounded-xl pointer-events-none z-10',
                            'border-2 animate-pulse',
                            currentAbilityType === 'poison'
                              ? 'border-green-500 shadow-[0_0_15px_rgba(34,197,94,0.5)]'
                              : 'border-orange-500 shadow-[0_0_15px_rgba(249,115,22,0.5)]'
                          )} />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* VS Divider */}
              <div className="flex items-center justify-center gap-4 py-2">
                <div className="h-px bg-gray-700 flex-1" />
                <span className="text-2xl font-bold text-purple-500">VS</span>
                <div className="h-px bg-gray-700 flex-1" />
              </div>

              {/* Player's Cards */}
              <div className="pb-28">
                <h3 className="text-sm font-medium text-gray-400 mb-3">
                  {t('yourCards')} ({alivePlayerCards.length} {t('alive')})
                  {healTargetMode && (
                    <span className="ml-2 text-green-400 animate-pulse">
                      — Выберите карту для лечения
                    </span>
                  )}
                  {abilityTargetMode && (
                    <span className="ml-2 text-purple-400 animate-pulse">
                      — Выберите врага сверху
                    </span>
                  )}
                </h3>
                <div className="flex flex-wrap justify-center gap-3">
                  {activeBattle.state.player_cards.map((card) => {
                    const isHealingCard = healingCardId === card.id;
                    const isShieldMode = currentAbilityType === 'shield';
                    // For heal: can target alive allies with HP < max (not the healer)
                    // For shield: can target any alive ally (including self if not the shielder)
                    const canBeTargeted = healTargetMode && card.alive && !isHealingCard &&
                      (isShieldMode ? !card.has_shield : card.hp < card.max_hp);

                    const isUsingAbility = abilityCardId === card.id;

                    return (
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
                        selected={selectedPlayerCard === card.id || isUsingAbility}
                        selectable={card.alive && !healTargetMode && !abilityTargetMode}
                        size="md"
                        isAttacking={attackingCardId === card.id}
                        isBeingAttacked={attackedCardId === card.id}
                        damageReceived={damageNumbers[String(card.id)]?.damage || null}
                        damageKey={damageNumbers[String(card.id)]?.key}
                        isCriticalHit={damageNumbers[String(card.id)]?.isCritical || false}
                        onClick={() => {
                          if (healTargetMode || abilityTargetMode) return;
                          card.alive && setSelectedPlayerCard(card.id as number);
                        }}
                        // Ability props
                        ability={card.ability || null}
                        abilityInfo={card.ability_info || null}
                        abilityCooldown={card.ability_cooldown || 0}
                        hasShield={card.has_shield || false}
                        statusEffects={card.status_effects || []}
                        // Heal/Shield targeting
                        isHealTarget={canBeTargeted}
                        isShieldTarget={canBeTargeted && isShieldMode}
                        healReceived={healNumbers[String(card.id)] || null}
                        onHealClick={() => canBeTargeted && handleHealTarget(card.id as number)}
                      />
                    );
                  })}
                </div>
              </div>

              {/* Action Buttons with background overlay */}
              <div className="fixed bottom-0 left-0 right-0 z-30 safe-area-bottom">
                <div className="bg-gray-900/95 backdrop-blur-md border-t border-gray-700/50 pt-3 pb-4 px-4">
                  <div className="max-w-md mx-auto space-y-2">
                    {/* Ability action buttons - show when card with ready ability is selected */}
                    {selectedPlayerCard && !healTargetMode && !abilityTargetMode && (() => {
                      const selectedCard = activeBattle?.state.player_cards.find(c => c.id === selectedPlayerCard);
                      if (!selectedCard?.ability || !selectedCard?.ability_info || (selectedCard.ability_cooldown || 0) > 0) {
                        return null;
                      }
                      const abilityType = selectedCard.ability;
                      const abilityInfo = selectedCard.ability_info;

                      // Get ability-specific styling and icon
                      const getAbilityStyle = () => {
                        switch (abilityType) {
                          case 'heal':
                            return 'bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 border-green-400';
                          case 'shield':
                            return 'bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 border-blue-400';
                          case 'poison':
                            return 'bg-gradient-to-r from-green-600 to-lime-500 hover:from-green-700 hover:to-lime-600 border-green-500';
                          case 'double_strike':
                            return 'bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 border-orange-400';
                          default:
                            return 'bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 border-purple-400';
                        }
                      };

                      return (
                        <Button
                          className={cn('w-full border', getAbilityStyle())}
                          onClick={() => handleAbilityClick(selectedPlayerCard, abilityType)}
                        >
                          <Sparkles className="w-5 h-5 mr-2" />
                          {abilityInfo.name}
                        </Button>
                      );
                    })()}

                    {/* Cancel or Attack button */}
                    {healTargetMode ? (
                      <Button
                        className="w-full bg-gray-700 hover:bg-gray-600"
                        onClick={cancelHealMode}
                      >
                        <X className="w-5 h-5 mr-2" />
                        Отменить {currentAbilityType === 'shield' ? 'щит' : 'лечение'}
                      </Button>
                    ) : abilityTargetMode ? (
                      <Button
                        className="w-full bg-gray-700 hover:bg-gray-600"
                        onClick={cancelAbilityMode}
                      >
                        <X className="w-5 h-5 mr-2" />
                        Отменить {currentAbilityType === 'poison' ? 'яд' : 'двойной удар'}
                      </Button>
                    ) : (
                      <Button
                        className={cn(
                          'w-full',
                          !canAttack
                            ? 'bg-gray-700 hover:bg-gray-700 text-gray-400 shadow-none'
                            : 'bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 shadow-lg shadow-purple-500/25'
                        )}
                        onClick={handleExecuteTurn}
                        disabled={!canAttack}
                        isLoading={executeTurnMutation.isPending}
                      >
                        <Target className="w-5 h-5 mr-2" />
                        {selectedPlayerCard && selectedTargetCard
                          ? t('attackButton')
                          : t('selectCardAndTarget')}
                      </Button>
                    )}
                  </div>
                </div>
              </div>

              {/* Random Battle Event */}
              {battleEvent && (
                <BattleEvent
                  event={battleEvent}
                  onComplete={() => setBattleEvent(null)}
                />
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
                    <h2 className="text-2xl font-bold text-white mb-2">{t('victory')}!</h2>
                    {/* Campaign stars */}
                    {campaignMode && campaignResult?.stars_earned && (
                      <div className="flex items-center justify-center gap-1 mt-2">
                        {[1, 2, 3].map((star) => (
                          <Star
                            key={star}
                            className={cn(
                              'w-8 h-8',
                              star <= (campaignResult.stars_earned || 0)
                                ? 'text-yellow-400 fill-yellow-400'
                                : 'text-gray-600'
                            )}
                          />
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <Skull className="w-20 h-20 text-gray-500 mx-auto mb-4" />
                    <h2 className="text-2xl font-bold text-white mb-2">{t('defeat')}</h2>
                    <p className="text-gray-400 text-sm max-w-xs mx-auto">
                      Ты всегда можешь навалять этому монстру, выполнив пару своих задач ;)
                    </p>
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
                          +{campaignResult?.xp_earned || battleResult.xp_earned} XP
                        </span>
                      </div>
                      {/* Campaign sparks */}
                      {campaignMode && campaignResult?.sparks_earned && campaignResult.sparks_earned > 0 && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Искры</span>
                          <span className="text-purple-400">
                            +{campaignResult.sparks_earned} ✨
                          </span>
                        </div>
                      )}
                      {battleResult.level_up && (
                        <div className="text-center pt-2 text-amber-400 font-medium">
                          🎉 {t('newLevel')}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </Card>

              {/* Campaign chapter completed */}
              {campaignMode && campaignResult?.chapter_completed && (
                <Card className="w-full max-w-sm mb-4 bg-gradient-to-br from-purple-500/20 to-blue-500/20 border-purple-500/30">
                  <div className="flex items-center gap-3">
                    <Map className="w-6 h-6 text-purple-400" />
                    <div>
                      <h3 className="font-medium text-white">Глава завершена!</h3>
                      <p className="text-sm text-purple-400">
                        Открыта следующая глава кампании
                      </p>
                    </div>
                  </div>
                </Card>
              )}

              {/* Campaign rewards */}
              {campaignMode && campaignResult?.rewards && campaignResult.rewards.length > 0 && (
                <Card className="w-full max-w-sm mb-4 bg-gradient-to-br from-amber-500/20 to-orange-500/20 border-amber-500/30">
                  <div className="flex items-center gap-3 mb-2">
                    <Sparkles className="w-6 h-6 text-amber-400" />
                    <h3 className="font-medium text-white">Награды</h3>
                  </div>
                  <div className="space-y-1">
                    {campaignResult.rewards.map((reward, idx) => (
                      <div key={idx} className="text-sm text-amber-400">
                        {reward.name || reward.type}: {reward.amount || 'Получено!'}
                      </div>
                    ))}
                  </div>
                </Card>
              )}

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

              {/* Show "Create Task" button only on defeat and not in campaign */}
              {!battleResult.won && !campaignMode && (
                <Button
                  variant="gradient"
                  className="w-full max-w-sm mb-3"
                  onClick={() => router.push('/')}
                >
                  <Plus className="w-5 h-5 mr-2" />
                  Создать задачу
                </Button>
              )}

              <Button className="w-full max-w-sm" variant={battleResult.won ? 'primary' : 'secondary'} onClick={handleBackToSelect}>
                {campaignMode ? (
                  <>
                    <Map className="w-5 h-5 mr-2" />
                    Вернуться в кампанию
                  </>
                ) : (
                  t('returnToSelect')
                )}
              </Button>
            </div>
          )}

          {/* Campaign Dialogue After */}
          {campaignMode && showDialogueAfter && campaignResult?.dialogue_after && (
            <DialogueSheet
              isOpen={showDialogueAfter}
              onClose={() => {
                setShowDialogueAfter(false);
                // Show story_outro after dialogue_after if available
                if (campaignResult?.story_outro) {
                  setShowCampaignOutro(true);
                }
              }}
              onContinue={() => {
                setShowDialogueAfter(false);
                // Show story_outro after dialogue_after if available
                if (campaignResult?.story_outro) {
                  setShowCampaignOutro(true);
                }
              }}
              monsterName={selectedMonster?.name || 'Монстр'}
              monsterEmoji={selectedMonster?.emoji || '👾'}
              monsterImageUrl={selectedMonster?.sprite_url || undefined}
              dialogue={campaignResult.dialogue_after.map(d => ({
                speaker: d.speaker,
                text: d.text,
                emoji: d.emoji,
              }))}
              title="После победы"
              continueButtonText={campaignResult?.story_outro ? 'Продолжить' : 'Готово'}
            />
          )}

          {/* Campaign Outro LoreSheet */}
          {campaignMode && showCampaignOutro && campaignResult?.story_outro && (
            <LoreSheet
              isOpen={showCampaignOutro}
              onClose={() => setShowCampaignOutro(false)}
              type="level_complete"
              title="Эпилог"
              text={campaignResult.story_outro}
              emoji="📜"
              starsEarned={campaignResult.stars_earned}
            />
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

      {/* Error Toast */}
      {errorMessage && (
        <div className="fixed bottom-24 left-4 right-4 z-50 animate-in fade-in slide-in-from-bottom-4">
          <div className="max-w-md mx-auto bg-red-500/90 backdrop-blur-sm text-white px-4 py-3 rounded-xl flex items-center justify-between gap-3 shadow-lg">
            <div className="flex items-center gap-2">
              <X className="w-5 h-5 flex-shrink-0" />
              <span className="text-sm">{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="p-1 hover:bg-white/20 rounded-lg transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Low HP Cards Warning Modal */}
      {showLowHpWarning && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in">
          <div className="bg-gray-800 rounded-2xl p-6 max-w-sm w-full border border-gray-700 shadow-xl animate-in zoom-in-95">
            <div className="text-center mb-4">
              <div className="w-16 h-16 bg-amber-500/20 rounded-full flex items-center justify-center mx-auto mb-3">
                <Shield className="w-8 h-8 text-amber-400" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">Некоторые карты ослаблены</h3>
              <p className="text-sm text-gray-400">
                У вас есть карты с 0 HP в колоде. Они не смогут участвовать в бою, пока не восстановят здоровье.
              </p>
            </div>

            <div className="space-y-2">
              <Button
                variant="gradient"
                className="w-full"
                onClick={handleLowHpWarningGoHome}
              >
                <Plus className="w-5 h-5 mr-2" />
                Выполнить задачи
              </Button>
              <Button
                variant="primary"
                className="w-full"
                onClick={handleLowHpWarningContinue}
              >
                Продолжить
              </Button>
              <button
                onClick={handleLowHpWarningDontShow}
                className="w-full text-sm text-gray-500 hover:text-gray-300 py-2 transition-colors"
              >
                Не показывать снова
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
