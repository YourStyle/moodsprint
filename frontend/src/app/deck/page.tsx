'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Layers,
  Plus,
  Minus,
  Sparkles,
  Filter,
  HeartPulse,
  Heart,
  Merge,
  ArrowRight,
  X,
  Check,
  AlertTriangle,
  Lock,
} from 'lucide-react';
import { Card, Button, Modal, ScrollBackdrop } from '@/components/ui';
import { DeckCard, CardInfoSheet } from '@/components/cards';
import { FeatureBanner } from '@/components/features';
import { cardsService, mergeService } from '@/services';
import { useAppStore } from '@/lib/store';
import { hapticFeedback } from '@/lib/telegram';
import { cn } from '@/lib/utils';
import { useLanguage } from '@/lib/i18n';
import type { Card as CardType, HealStatus } from '@/services/cards';

type Tab = 'collection' | 'deck' | 'merge';
type RarityFilter = 'all' | 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary';
type GenreFilter = 'all' | string;

const ALL_GENRES = ['magic', 'fantasy', 'scifi', 'cyberpunk', 'anime'];
const GENRE_EMOJIS: Record<string, string> = {
  magic: '✨',
  fantasy: '⚔️',
  scifi: '🚀',
  cyberpunk: '🌆',
  anime: '🌸',
};
const GENRE_KEYS: Record<string, string> = {
  magic: 'genreMagic',
  fantasy: 'genreFantasy',
  scifi: 'genreScifi',
  cyberpunk: 'genreCyberpunk',
  anime: 'genreAnime',
};

interface MergePreview {
  card1: CardType;
  card2: CardType;
  chances: Record<string, number>;
  bonuses: { type: string; value: string }[];
  can_merge: boolean;
}

const RARITY_COLORS = {
  common: '#9CA3AF',
  uncommon: '#22C55E',
  rare: '#3B82F6',
  epic: '#A855F7',
  legendary: '#F59E0B',
};

const RARITY_KEYS = {
  common: 'rarityCommon',
  uncommon: 'rarityUncommon',
  rare: 'rarityRare',
  epic: 'rarityEpic',
  legendary: 'rarityLegendary',
} as const;

export default function DeckPage() {
  const queryClient = useQueryClient();
  const { user, isTelegramEnvironment } = useAppStore();
  const { t } = useLanguage();

  const [activeTab, setActiveTab] = useState<Tab>('collection');
  const [rarityFilter, setRarityFilter] = useState<RarityFilter>('all');
  const [genreFilter, setGenreFilter] = useState<GenreFilter>('all');
  const [selectedCard, setSelectedCard] = useState<CardType | null>(null);
  const [infoCard, setInfoCard] = useState<CardType | null>(null);

  // Merge state
  const [mergeCard1, setMergeCard1] = useState<CardType | null>(null);
  const [mergeCard2, setMergeCard2] = useState<CardType | null>(null);
  const [mergePreview, setMergePreview] = useState<MergePreview | null>(null);
  const [mergeResult, setMergeResult] = useState<CardType | null>(null);
  const [showMergeResult, setShowMergeResult] = useState(false);

  // Fetch cards
  const { data: cardsData, isLoading: cardsLoading } = useQuery({
    queryKey: ['cards'],
    queryFn: () => cardsService.getCards(),
    enabled: !!user,
    staleTime: 5 * 60 * 1000,
  });

  // Fetch deck
  const { data: deckData, isLoading: deckLoading } = useQuery({
    queryKey: ['deck'],
    queryFn: () => cardsService.getDeck(),
    enabled: !!user,
  });

  // Fetch heal status
  const { data: healStatusData, refetch: refetchHealStatus } = useQuery({
    queryKey: ['heal-status'],
    queryFn: () => cardsService.getHealStatus(),
    enabled: !!user,
    staleTime: 2 * 60 * 1000,
  });

  // Fetch card templates (for locked cards in collection)
  const { data: templatesData } = useQuery({
    queryKey: ['card-templates'],
    queryFn: () => cardsService.getTemplates(),
    enabled: !!user && activeTab === 'collection',
    staleTime: 10 * 60 * 1000,
  });

  // Add to deck mutation
  const addToDeckMutation = useMutation({
    mutationFn: (cardId: number) => cardsService.addToDeck(cardId),
    onSuccess: () => {
      hapticFeedback('success');
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      queryClient.invalidateQueries({ queryKey: ['deck'] });
      setSelectedCard(null);
    },
  });

  // Remove from deck mutation
  const removeFromDeckMutation = useMutation({
    mutationFn: (cardId: number) => cardsService.removeFromDeck(cardId),
    onSuccess: () => {
      hapticFeedback('light');
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      queryClient.invalidateQueries({ queryKey: ['deck'] });
      setSelectedCard(null);
    },
  });

  // Heal all cards mutation
  const healAllMutation = useMutation({
    mutationFn: () => cardsService.healAllCards(),
    onSuccess: () => {
      hapticFeedback('success');
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      queryClient.invalidateQueries({ queryKey: ['deck'] });
      refetchHealStatus();
    },
  });

  // Set showcase mutation
  const setShowcaseMutation = useMutation({
    mutationFn: ({ cardId, slot }: { cardId: number; slot: number }) =>
      cardsService.setShowcase(cardId, slot),
    onSuccess: () => {
      hapticFeedback('success');
      queryClient.invalidateQueries({ queryKey: ['showcase'] });
    },
  });

  const setCompanionMutation = useMutation({
    mutationFn: (cardId: number) => cardsService.setCompanion(cardId),
    onSuccess: () => {
      hapticFeedback('success');
      queryClient.invalidateQueries({ queryKey: ['cards'] });
    },
  });

  const removeCompanionMutation = useMutation({
    mutationFn: () => cardsService.removeCompanion(),
    onSuccess: () => {
      hapticFeedback('light');
      queryClient.invalidateQueries({ queryKey: ['cards'] });
    },
  });

  // Merge preview mutation
  const mergePreviewMutation = useMutation({
    mutationFn: ({ card1Id, card2Id }: { card1Id: number; card2Id: number }) =>
      mergeService.previewMerge(card1Id, card2Id),
    onSuccess: (result) => {
      if (result.success && result.data) {
        setMergePreview(result.data as unknown as MergePreview);
      } else {
        console.error('Merge preview failed:', result);
        setMergePreview(null);
      }
    },
    onError: (error) => {
      console.error('Merge preview error:', error);
      setMergePreview(null);
    },
  });

  // Merge cards mutation
  const mergeCardsMutation = useMutation({
    mutationFn: ({ card1Id, card2Id }: { card1Id: number; card2Id: number }) =>
      mergeService.mergeCards(card1Id, card2Id),
    onSuccess: (result) => {
      if (result.success && result.data) {
        hapticFeedback('success');
        setMergeResult(result.data.new_card as unknown as CardType);
        setShowMergeResult(true);
        setMergeCard1(null);
        setMergeCard2(null);
        setMergePreview(null);
        queryClient.invalidateQueries({ queryKey: ['cards'] });
        queryClient.invalidateQueries({ queryKey: ['deck'] });
      }
    },
  });

  const cards = cardsData?.data?.cards || [];
  const deck = deckData?.data?.deck || [];
  const deckStats = deckData?.data?.stats;
  const maxDeckSize = deckData?.data?.max_size || 5;
  const rarityCounts = cardsData?.data?.rarity_counts || {};
  const healStatus = healStatusData?.data;
  const templates = templatesData?.data?.templates || [];
  const collectedTemplateIds = templatesData?.data?.collected_template_ids || [];
  const unlockedGenres = templatesData?.data?.unlocked_genres || [];
  const unlockedGenresSet = useMemo(() => new Set(unlockedGenres), [unlockedGenres]);

  // Genres sorted: unlocked first (in unlock order, primary first), then locked
  const sortedGenres = useMemo(() => {
    const locked = ALL_GENRES.filter(g => !unlockedGenresSet.has(g));
    return [...unlockedGenres, ...locked];
  }, [unlockedGenres, unlockedGenresSet]);

  // Build collection: owned cards + unowned templates (locked, previously owned, or genre-locked)
  const { allCollectionCards } = useMemo(() => {
    const ownedCardTemplateIds = new Set(cards.map((c) => c.template_id).filter(Boolean));
    const collectedSet = new Set(collectedTemplateIds);
    const unownedCards: (CardType & { _isLocked?: boolean; _isPreviouslyOwned?: boolean; _isGenreLocked?: boolean })[] = templates
      .filter((tmpl) => !ownedCardTemplateIds.has(tmpl.id))
      .map((tmpl) => {
        const wasCollected = collectedSet.has(tmpl.id);
        const genreLocked = !unlockedGenresSet.has(tmpl.genre);
        return {
          id: -tmpl.id, // negative to avoid collisions
          user_id: 0,
          template_id: tmpl.id,
          name: tmpl.name,
          description: tmpl.description,
          emoji: tmpl.emoji,
          image_url: tmpl.image_url,
          hp: tmpl.base_hp,
          current_hp: tmpl.base_hp,
          attack: tmpl.base_attack,
          rarity: (tmpl.rarity || 'common') as CardType['rarity'],
          genre: tmpl.genre,
          is_in_deck: false,
          is_tradeable: false,
          is_alive: true,
          is_on_cooldown: false,
          cooldown_remaining: null,
          is_companion: false,
          is_showcase: false,
          showcase_slot: null,
          rarity_color: '#9CA3AF',
          created_at: '',
          ability: null,
          ability_info: null,
          card_level: 0,
          card_xp: 0,
          _isGenreLocked: genreLocked,
          _isLocked: !wasCollected && !genreLocked,
          _isPreviouslyOwned: wasCollected && !genreLocked,
        };
      });
    return { allCollectionCards: [...cards, ...unownedCards] };
  }, [cards, templates, collectedTemplateIds, unlockedGenresSet]);

  // Filter cards by rarity and genre
  const filteredCards = useMemo(() => {
    let result = allCollectionCards;
    if (rarityFilter !== 'all') {
      result = result.filter((c) => c.rarity === rarityFilter);
    }
    if (genreFilter !== 'all') {
      result = result.filter((c) => c.genre === genreFilter);
    }
    return result;
  }, [allCollectionCards, rarityFilter, genreFilter]);

  // Group filtered cards by genre for section headers
  const groupedByGenre = useMemo(() => {
    const groups: Record<string, typeof filteredCards> = {};
    for (const card of filteredCards) {
      const genre = card.genre || 'unknown';
      if (!groups[genre]) groups[genre] = [];
      groups[genre].push(card);
    }
    // Sort genres: unlocked first (in unlock order, primary first), then locked
    const sorted = Object.entries(groups).sort(([a], [b]) => {
      return sortedGenres.indexOf(a) - sortedGenres.indexOf(b);
    });
    return sorted;
  }, [filteredCards, sortedGenres]);

  // Check if any card needs healing
  const cardsNeedHealing = cards.some((c) => c.current_hp < c.hp);

  // Cards available for merge (not in deck, not legendary, alive)
  const mergeableCards = cards.filter(
    (c) => !c.is_in_deck && c.rarity !== 'legendary' && c.current_hp > 0
  );

  // Fetch merge preview when both cards selected
  useEffect(() => {
    if (mergeCard1 && mergeCard2) {
      mergePreviewMutation.mutate({ card1Id: mergeCard1.id, card2Id: mergeCard2.id });
    } else {
      setMergePreview(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mergeCard1?.id, mergeCard2?.id]);

  const handleMergeCardSelect = (card: CardType) => {
    hapticFeedback('light');

    if (mergeCard1?.id === card.id) {
      setMergeCard1(null);
      return;
    }
    if (mergeCard2?.id === card.id) {
      setMergeCard2(null);
      return;
    }

    if (!mergeCard1) {
      setMergeCard1(card);
    } else if (!mergeCard2) {
      setMergeCard2(card);
    } else {
      // Replace first card
      setMergeCard1(card);
      setMergeCard2(null);
    }
  };

  const handleExecuteMerge = () => {
    if (mergeCard1 && mergeCard2 && mergePreview?.can_merge) {
      hapticFeedback('medium');
      mergeCardsMutation.mutate({ card1Id: mergeCard1.id, card2Id: mergeCard2.id });
    }
  };

  const clearMergeSelection = () => {
    setMergeCard1(null);
    setMergeCard2(null);
    setMergePreview(null);
  };

  // Track which cards are generating images
  const [generatingImages, setGeneratingImages] = useState<Set<number>>(new Set());
  const generatedCardsRef = useRef<Set<number>>(new Set());

  // Auto-generate images for cards without them (1 at a time, during idle)
  useEffect(() => {
    const cardsWithoutImages = cards.filter(
      (c) => !c.image_url && !generatingImages.has(c.id) && !generatedCardsRef.current.has(c.id)
    );

    if (cardsWithoutImages.length === 0) return;

    const card = cardsWithoutImages[0];

    const generateOne = () => {
      setGeneratingImages((prev) => new Set(prev).add(card.id));
      generatedCardsRef.current.add(card.id);

      cardsService.generateCardImage(card.id)
        .then((result) => {
          if (result.success && result.data?.image_url) {
            queryClient.invalidateQueries({ queryKey: ['cards'] });
            queryClient.invalidateQueries({ queryKey: ['deck'] });
          }
        })
        .catch((err) => {
          console.error('Failed to generate card image:', err);
        })
        .finally(() => {
          setGeneratingImages((prev) => {
            const next = new Set(prev);
            next.delete(card.id);
            return next;
          });
        });
    };

    if ('requestIdleCallback' in window) {
      const id = requestIdleCallback(generateOne);
      return () => cancelIdleCallback(id);
    } else {
      const id = setTimeout(generateOne, 200);
      return () => clearTimeout(id);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cards, queryClient]);

  if (!user) {
    return (
      <div className="p-4 text-center">
        <p className="text-gray-500">{t('loginToSeeDeck')}</p>
      </div>
    );
  }

  const handleCardClick = (card: CardType) => {
    setSelectedCard(selectedCard?.id === card.id ? null : card);
    hapticFeedback('light');
  };

  const handleAddToDeck = (cardId: number) => {
    addToDeckMutation.mutate(cardId);
  };

  const handleRemoveFromDeck = (cardId: number) => {
    removeFromDeckMutation.mutate(cardId);
  };

  return (
    <div className="min-h-screen p-4 pb-4">
      <ScrollBackdrop />
      {/* Header */}
      <div className="mb-4">
        <div className="flex items-center gap-3">
          <Layers className="w-8 h-8 text-purple-500" />
          <div className="flex-1">
            <h1 className="text-xl font-bold text-white">{t('deck')}</h1>
            <p className="text-sm text-gray-400">{t('deckSubtitle')}</p>
          </div>
          <span className="text-sm text-gray-400 bg-gray-800/60 px-2.5 py-1 rounded-lg border border-gray-700/50">
            {t('deckCapacity').replace('{current}', String(deck.length)).replace('{max}', String(maxDeckSize))}
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-gray-800 rounded-xl mb-4">
        <button
          onClick={() => { setActiveTab('collection'); setSelectedCard(null); }}
          className={cn(
            'flex-1 py-2 px-1 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1',
            activeTab === 'collection'
              ? 'bg-purple-500 text-white'
              : 'text-gray-400 hover:text-white'
          )}
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">{t('collection')}</span>
        </button>
        <button
          onClick={() => { setActiveTab('deck'); setSelectedCard(null); }}
          className={cn(
            'flex-1 py-2 px-1 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1',
            activeTab === 'deck'
              ? 'bg-purple-500 text-white'
              : 'text-gray-400 hover:text-white'
          )}
        >
          <Layers className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">{t('deck')}</span>
        </button>
        <button
          onClick={() => {
            setActiveTab('merge');
            setSelectedCard(null);
            clearMergeSelection();
          }}
          className={cn(
            'flex-1 py-2 px-1 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1',
            activeTab === 'merge'
              ? 'bg-gradient-to-r from-orange-500 to-pink-500 text-white'
              : 'text-gray-400 hover:text-white'
          )}
        >
          <Merge className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">{t('merge')}</span>
        </button>
      </div>

      {/* Marketplace Banner - only show in Telegram environment */}
      {isTelegramEnvironment && (
        <div className="mb-4">
          <FeatureBanner type="marketplace" />
        </div>
      )}

      {/* Collection Tab */}
      {activeTab === 'collection' && (
        <>
          {/* Rarity filter */}
          <div className="flex gap-2 mb-3 overflow-x-auto pb-1 scrollbar-hide">
            <button
              onClick={() => setRarityFilter('all')}
              className={cn(
                'px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all flex items-center gap-1',
                rarityFilter === 'all'
                  ? 'bg-purple-500 text-white'
                  : 'bg-gray-800 text-gray-400'
              )}
            >
              <Filter className="w-3 h-3" />
              {t('all')}
            </button>
            {Object.entries(RARITY_COLORS).map(([rarity, color]) => (
              <button
                key={rarity}
                onClick={() => setRarityFilter(rarity as RarityFilter)}
                className={cn(
                  'px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all',
                  rarityFilter === rarity
                    ? 'text-white'
                    : 'bg-gray-800 text-gray-400'
                )}
                style={rarityFilter === rarity ? { backgroundColor: color } : {}}
              >
                {t(RARITY_KEYS[rarity as keyof typeof RARITY_KEYS])} ({rarityCounts[rarity] || 0})
              </button>
            ))}
          </div>

          {/* Genre filter */}
          <div className="flex gap-2 mb-4 overflow-x-auto pb-1 scrollbar-hide">
            <button
              onClick={() => setGenreFilter('all')}
              className={cn(
                'px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all',
                genreFilter === 'all'
                  ? 'bg-indigo-500 text-white'
                  : 'bg-gray-800 text-gray-400'
              )}
            >
              {t('allGenres')}
            </button>
            {sortedGenres.map((genre) => {
              const isUnlocked = unlockedGenresSet.has(genre);
              return (
                <button
                  key={genre}
                  onClick={() => setGenreFilter(genre)}
                  className={cn(
                    'px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all flex items-center gap-1',
                    genreFilter === genre
                      ? 'bg-indigo-500 text-white'
                      : isUnlocked
                        ? 'bg-gray-800 text-gray-400'
                        : 'bg-gray-800/50 text-gray-600'
                  )}
                >
                  {!isUnlocked && <Lock className="w-3 h-3" />}
                  <span>{GENRE_EMOJIS[genre]}</span>
                  {t(GENRE_KEYS[genre] as any)}
                </button>
              );
            })}
          </div>

          {/* Heal all button */}
          {cardsNeedHealing && (
            <Card className="mb-4 bg-gradient-to-r from-red-900/40 to-pink-900/40 border-red-500/40">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <HeartPulse className="w-5 h-5 text-red-400" />
                    <span className="text-sm font-medium text-white">{t('healAllCards')}</span>
                  </div>
                  <Button
                    size="sm"
                    className={cn(
                      healStatus?.can_heal
                        ? 'bg-gradient-to-r from-red-500 to-pink-500 hover:from-red-600 hover:to-pink-600 text-white shadow-lg shadow-red-500/25'
                        : 'bg-gray-700 text-gray-400 cursor-not-allowed'
                    )}
                    onClick={() => healStatus?.can_heal && healAllMutation.mutate()}
                    isLoading={healAllMutation.isPending}
                    disabled={!healStatus?.can_heal}
                  >
                    <Heart className="w-4 h-4 mr-1" />
                    {t('heal')}
                  </Button>
                </div>

                {/* Healing progress */}
                {healStatus && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-400">
                        {healStatus.heals_today === 0
                          ? t('firstHealToday')
                          : healStatus.heals_today === 1
                            ? t('secondHealToday')
                            : t('freeHealing')}
                      </span>
                      {healStatus.required_tasks > 0 && (
                        <span className={cn(
                          'font-medium',
                          healStatus.can_heal ? 'text-green-400' : 'text-yellow-400'
                        )}>
                          {healStatus.completed_tasks}/{healStatus.required_tasks} {t('tasksCount')}
                        </span>
                      )}
                    </div>

                    {/* Progress bar */}
                    {healStatus.required_tasks > 0 && (
                      <div className="h-2 bg-gray-700/50 rounded-full overflow-hidden">
                        <div
                          className={cn(
                            'h-full transition-all duration-500 rounded-full',
                            healStatus.can_heal
                              ? 'bg-gradient-to-r from-green-500 to-emerald-400'
                              : 'bg-gradient-to-r from-yellow-500 to-orange-400'
                          )}
                          style={{
                            width: `${Math.min(100, (healStatus.completed_tasks / healStatus.required_tasks) * 100)}%`
                          }}
                        />
                      </div>
                    )}

                    {healStatus.required_tasks === 0 && healStatus.heals_today >= 2 && (
                      <p className="text-xs text-green-400">{t('freeHealingAvailable')}</p>
                    )}
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Cards grid */}
          {cardsLoading ? (
            <div className="grid grid-cols-2 gap-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="aspect-[3/4] bg-gray-800 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : filteredCards.length === 0 ? (
            <Card className="text-center py-8">
              <Sparkles className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400">
                {rarityFilter === 'all'
                  ? t('noCards')
                  : `${t('noCardsOfRarity')} "${t(RARITY_KEYS[rarityFilter])}"`}
              </p>
              <p className="text-sm text-gray-500 mt-1">
                {t('completeTasksToGetCards')}
              </p>
            </Card>
          ) : (
            <>
              {/* Genre-grouped cards */}
              {groupedByGenre.map(([genre, genreCards]) => (
                <div key={genre} className="mb-4">
                  {/* Genre section header (only when showing all genres) */}
                  {genreFilter === 'all' && groupedByGenre.length > 1 && (
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm">{GENRE_EMOJIS[genre] || '?'}</span>
                      <span className="text-sm font-medium text-gray-300">
                        {t(GENRE_KEYS[genre] as any) || genre}
                      </span>
                      {!unlockedGenresSet.has(genre) && (
                        <span className="flex items-center gap-1 text-xs text-gray-500">
                          <Lock className="w-3 h-3" />
                          {t('cardGenreLocked')}
                        </span>
                      )}
                      <span className="text-xs text-gray-500 ml-auto">{genreCards.length}</span>
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-3">
                    {genreCards.map((card) => {
                      const isGenreLocked = '_isGenreLocked' in card && card._isGenreLocked === true;
                      const isLocked = '_isLocked' in card && card._isLocked === true;
                      const isPreviouslyOwned = '_isPreviouslyOwned' in card && card._isPreviouslyOwned === true;
                      const isUnavailable = isGenreLocked || isLocked || isPreviouslyOwned;
                      return (
                        <DeckCard
                          key={card.id}
                          id={card.id}
                          name={card.name}
                          description={card.description}
                          emoji={card.emoji}
                          imageUrl={card.image_url}
                          hp={card.hp}
                          currentHp={card.current_hp}
                          attack={card.attack}
                          rarity={card.rarity}
                          genre={card.genre}
                          isInDeck={card.is_in_deck}
                          isGenerating={!isUnavailable && generatingImages.has(card.id)}
                          createdAt={isUnavailable ? undefined : card.created_at}
                          ability={card.ability}
                          abilityInfo={card.ability_info}
                          isLocked={isLocked}
                          isPreviouslyOwned={isPreviouslyOwned}
                          isGenreLocked={isGenreLocked}
                          onClick={isUnavailable ? undefined : () => handleCardClick(card)}
                          onInfoClick={isUnavailable ? undefined : () => setInfoCard(card)}
                        />
                      );
                    })}
                  </div>
                </div>
              ))}

              {/* Selected card actions */}
              {selectedCard && (
                <div className="fixed left-4 right-4 max-w-md mx-auto z-40" style={{ bottom: 'calc(5rem + var(--safe-area-bottom, 0px))' }}>
                  <div className="bg-gray-900/95 backdrop-blur-md border border-purple-500/30 rounded-2xl p-3 shadow-lg shadow-purple-500/10 flex items-center gap-3">
                    <span className="text-sm text-white font-medium flex-1 truncate">
                      {selectedCard.name}
                    </span>
                    {selectedCard.is_in_deck ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleRemoveFromDeck(selectedCard.id)}
                        isLoading={removeFromDeckMutation.isPending}
                      >
                        <Minus className="w-4 h-4 mr-1" />
                        {t('removeFromDeck')}
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        onClick={() => handleAddToDeck(selectedCard.id)}
                        isLoading={addToDeckMutation.isPending}
                        disabled={deck.length >= maxDeckSize}
                      >
                        <Plus className="w-4 h-4 mr-1" />
                        {t('addToDeck')}
                      </Button>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </>
      )}

      {/* Deck Tab */}
      {activeTab === 'deck' && (
        <>
          {/* Deck stats */}
          {deckStats && deck.length > 0 && (
            <Card className="mb-4">
              <h3 className="text-sm font-medium text-white mb-3">{t('deckStats')}</h3>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div>
                  <p className="text-lg font-bold text-red-400">{deckStats.total_attack}</p>
                  <p className="text-xs text-gray-500">{t('attack')}</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-green-400">{deckStats.total_hp}</p>
                  <p className="text-xs text-gray-500">{t('hp')}</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-purple-400">{deckStats.genres.length}</p>
                  <p className="text-xs text-gray-500">{t('genres')}</p>
                </div>
              </div>
            </Card>
          )}

          {/* Deck cards */}
          {deckLoading ? (
            <div className="grid grid-cols-2 gap-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="aspect-[3/4] bg-gray-800 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : deck.length === 0 ? (
            <Card className="text-center py-8">
              <Layers className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400">{t('deckEmpty')}</p>
              <p className="text-sm text-gray-500 mt-1">
                {t('addCardsForBattle')}
              </p>
              <Button
                size="sm"
                className="mt-4"
                onClick={() => setActiveTab('collection')}
              >
                {t('goToCollection')}
              </Button>
            </Card>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3">
                {deck.map((card) => (
                  <DeckCard
                    key={card.id}
                    id={card.id}
                    name={card.name}
                    description={card.description}
                    emoji={card.emoji}
                    imageUrl={card.image_url}
                    hp={card.hp}
                    currentHp={card.current_hp}
                    attack={card.attack}
                    rarity={card.rarity}
                    genre={card.genre}
                    isInDeck={card.is_in_deck}
                    isGenerating={generatingImages.has(card.id)}
                    createdAt={card.created_at}
                    ability={card.ability}
                    abilityInfo={card.ability_info}
                    onClick={() => handleCardClick(card)}
                    onInfoClick={() => setInfoCard(card)}
                  />
                ))}
              </div>

              {/* Selected card actions */}
              {selectedCard && (
                <div className="fixed left-4 right-4 max-w-md mx-auto z-40" style={{ bottom: 'calc(5rem + var(--safe-area-bottom, 0px))' }}>
                  <div className="bg-gray-900/95 backdrop-blur-md border border-purple-500/30 rounded-2xl p-3 shadow-lg shadow-purple-500/10 flex items-center gap-3">
                    <span className="text-sm text-white font-medium flex-1 truncate">
                      {selectedCard.name}
                    </span>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => handleRemoveFromDeck(selectedCard.id)}
                      isLoading={removeFromDeckMutation.isPending}
                    >
                      <Minus className="w-4 h-4 mr-1" />
                      {t('removeFromDeck')}
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </>
      )}

      {/* Merge Tab */}
      {activeTab === 'merge' && (
        <>
          {/* Merge explanation */}
          <Card className="mb-4 bg-gradient-to-r from-orange-900/30 to-pink-900/30 border-orange-500/30">
            <div className="flex items-start gap-3">
              <Merge className="w-6 h-6 text-orange-400 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-medium text-white mb-1">{t('mergeCards')}</h3>
                <p className="text-xs text-gray-400">
                  {t('mergeExplanation')}
                </p>
              </div>
            </div>
          </Card>

          {/* Selected cards for merge */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            {/* Card 1 slot */}
            <div
              className={cn(
                'aspect-[3/4] rounded-xl border-2 border-dashed flex flex-col items-center justify-center',
                mergeCard1
                  ? 'border-orange-500 bg-orange-500/10'
                  : 'border-gray-600 bg-gray-800/50'
              )}
            >
              {mergeCard1 ? (
                <div className="relative w-full h-full">
                  <DeckCard
                    id={mergeCard1.id}
                    name={mergeCard1.name}
                    description={mergeCard1.description}
                    emoji={mergeCard1.emoji}
                    imageUrl={mergeCard1.image_url}
                    hp={mergeCard1.hp}
                    currentHp={mergeCard1.current_hp}
                    attack={mergeCard1.attack}
                    rarity={mergeCard1.rarity}
                    genre={mergeCard1.genre}
                    isInDeck={false}
                    isGenerating={false}
                    createdAt={mergeCard1.created_at}
                    ability={mergeCard1.ability}
                    abilityInfo={mergeCard1.ability_info}
                    onClick={() => setMergeCard1(null)}
                  />
                  <button
                    onClick={() => setMergeCard1(null)}
                    className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center z-10"
                  >
                    <X className="w-4 h-4 text-white" />
                  </button>
                </div>
              ) : (
                <div className="text-center">
                  <Plus className="w-8 h-8 text-gray-500 mx-auto mb-2" />
                  <p className="text-xs text-gray-500">{t('card1')}</p>
                </div>
              )}
            </div>

            {/* Card 2 slot */}
            <div
              className={cn(
                'aspect-[3/4] rounded-xl border-2 border-dashed flex flex-col items-center justify-center',
                mergeCard2
                  ? 'border-pink-500 bg-pink-500/10'
                  : 'border-gray-600 bg-gray-800/50'
              )}
            >
              {mergeCard2 ? (
                <div className="relative w-full h-full">
                  <DeckCard
                    id={mergeCard2.id}
                    name={mergeCard2.name}
                    description={mergeCard2.description}
                    emoji={mergeCard2.emoji}
                    imageUrl={mergeCard2.image_url}
                    hp={mergeCard2.hp}
                    currentHp={mergeCard2.current_hp}
                    attack={mergeCard2.attack}
                    rarity={mergeCard2.rarity}
                    genre={mergeCard2.genre}
                    isInDeck={false}
                    isGenerating={false}
                    createdAt={mergeCard2.created_at}
                    ability={mergeCard2.ability}
                    abilityInfo={mergeCard2.ability_info}
                    onClick={() => setMergeCard2(null)}
                  />
                  <button
                    onClick={() => setMergeCard2(null)}
                    className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center z-10"
                  >
                    <X className="w-4 h-4 text-white" />
                  </button>
                </div>
              ) : (
                <div className="text-center">
                  <Plus className="w-8 h-8 text-gray-500 mx-auto mb-2" />
                  <p className="text-xs text-gray-500">{t('card2')}</p>
                </div>
              )}
            </div>
          </div>

          {/* Merge preview */}
          {mergePreview && (
            <Card className="mb-4">
              <h4 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-yellow-400" />
                {t('chancesToGet')}
              </h4>
              <div className="space-y-2">
                {Object.entries(mergePreview.chances)
                  .filter(([, chance]) => chance > 0)
                  .sort(([, a], [, b]) => b - a)
                  .map(([rarity, chance]) => (
                    <div key={rarity} className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: RARITY_COLORS[rarity as keyof typeof RARITY_COLORS] || '#888' }}
                      />
                      <span className="text-xs text-gray-300 flex-1">
                        {t(RARITY_KEYS[rarity as keyof typeof RARITY_KEYS] || 'rarityCommon')}
                      </span>
                      <span className="text-xs font-bold text-white">{chance}%</span>
                    </div>
                  ))}
              </div>

              {/* Bonuses */}
              {mergePreview.bonuses.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-700">
                  <p className="text-xs text-gray-400 mb-2">{t('bonuses')}</p>
                  {mergePreview.bonuses.map((bonus, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs text-green-400">
                      <Check className="w-3 h-3" />
                      <span>{bonus.value}</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}

          {/* Merge button */}
          {mergeCard1 && mergeCard2 && (
            <Button
              className="w-full mb-4 bg-gradient-to-r from-orange-500 to-pink-500 hover:from-orange-600 hover:to-pink-600"
              onClick={handleExecuteMerge}
              isLoading={mergeCardsMutation.isPending || mergePreviewMutation.isPending}
              disabled={!mergePreview?.can_merge && !mergePreviewMutation.isPending}
            >
              <Merge className="w-4 h-4 mr-2" />
              {t('mergeCardsButton')}
            </Button>
          )}

          {/* Warning */}
          <Card className="mb-4 bg-yellow-900/20 border-yellow-500/30">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-yellow-200/80">
                {t('mergeWarning')}
              </p>
            </div>
          </Card>

          {/* Available cards for merge */}
          <h4 className="text-sm font-medium text-white mb-3">
            {t('availableCards')} ({mergeableCards.length})
          </h4>

          {mergeableCards.length === 0 ? (
            <Card className="text-center py-6">
              <Merge className="w-10 h-10 text-gray-600 mx-auto mb-2" />
              <p className="text-sm text-gray-400">
                {t('noCardsForMerge')}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {t('cannotMergeLegendary')}
              </p>
            </Card>
          ) : (
            <div className="grid grid-cols-3 gap-2">
              {mergeableCards.map((card) => (
                <div
                  key={card.id}
                  onClick={() => handleMergeCardSelect(card)}
                  className={cn(
                    'cursor-pointer transition-all rounded-lg overflow-hidden',
                    (mergeCard1?.id === card.id || mergeCard2?.id === card.id)
                      ? 'ring-2 ring-orange-500 scale-95 opacity-50'
                      : 'hover:scale-105'
                  )}
                >
                  <DeckCard
                    id={card.id}
                    name={card.name}
                    description={card.description}
                    emoji={card.emoji}
                    imageUrl={card.image_url}
                    hp={card.hp}
                    currentHp={card.current_hp}
                    attack={card.attack}
                    rarity={card.rarity}
                    genre={card.genre}
                    isInDeck={false}
                    isGenerating={generatingImages.has(card.id)}
                    createdAt={card.created_at}
                    ability={card.ability}
                    abilityInfo={card.ability_info}
                    compact
                  />
                </div>
              ))}
            </div>
          )}

          {/* Merge result modal */}
          <Modal
            isOpen={showMergeResult && !!mergeResult}
            onClose={() => {
              setShowMergeResult(false);
              setMergeResult(null);
            }}
            showClose={false}
          >
            {mergeResult && (
              <div className="text-center">
                <Sparkles className="w-12 h-12 text-yellow-400 mx-auto mb-4 animate-pulse" />
                <h3 className="text-xl font-bold text-white mb-2">{t('newCard')}</h3>
                <p className="text-sm text-gray-400 mb-6">{t('congratsMerge')}</p>

                <div className="flex justify-center mb-6 max-w-[200px] mx-auto">
                  <DeckCard
                    id={mergeResult.id}
                    name={mergeResult.name}
                    description={mergeResult.description}
                    emoji={mergeResult.emoji}
                    imageUrl={mergeResult.image_url}
                    hp={mergeResult.hp}
                    currentHp={mergeResult.current_hp}
                    attack={mergeResult.attack}
                    rarity={mergeResult.rarity}
                    genre={mergeResult.genre}
                    isInDeck={false}
                    isGenerating={!mergeResult.image_url}
                    createdAt={mergeResult.created_at}
                    ability={mergeResult.ability}
                    abilityInfo={mergeResult.ability_info}
                  />
                </div>

                <Button
                  className="w-full"
                  onClick={() => {
                    setShowMergeResult(false);
                    setMergeResult(null);
                  }}
                >
                  {t('great')}
                </Button>
              </div>
            )}
          </Modal>
        </>
      )}

      {/* Card Info Sheet */}
      <CardInfoSheet
        isOpen={!!infoCard}
        onClose={() => setInfoCard(null)}
        card={infoCard ? {
          id: infoCard.id,
          name: infoCard.name,
          description: infoCard.description,
          emoji: infoCard.emoji,
          imageUrl: infoCard.image_url,
          hp: infoCard.hp,
          currentHp: infoCard.current_hp,
          attack: infoCard.attack,
          rarity: infoCard.rarity,
          genre: infoCard.genre,
          createdAt: infoCard.created_at,
          abilityInfo: infoCard.ability_info,
          isOwned: true,
          cardLevel: infoCard.card_level,
          cardXp: infoCard.card_xp,
          isCompanion: infoCard.is_companion,
        } : null}
        showSellButton={isTelegramEnvironment}
        isInDeck={infoCard?.is_in_deck}
        onAddToDeck={(id) => addToDeckMutation.mutate(id)}
        onRemoveFromDeck={(id) => removeFromDeckMutation.mutate(id)}
        onAddToShowcase={(id, slot) => setShowcaseMutation.mutate({ cardId: id, slot })}
        onSetCompanion={(id) => setCompanionMutation.mutate(id)}
        onRemoveCompanion={() => removeCompanionMutation.mutate()}
      />
    </div>
  );
}
