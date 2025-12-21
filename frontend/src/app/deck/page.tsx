'use client';

import { useState, useEffect, useRef } from 'react';
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
} from 'lucide-react';
import { Card, Button, Modal } from '@/components/ui';
import { DeckCard, CardInfoSheet } from '@/components/cards';
import { cardsService, mergeService } from '@/services';
import { useAppStore } from '@/lib/store';
import { hapticFeedback } from '@/lib/telegram';
import { cn } from '@/lib/utils';
import { useLanguage } from '@/lib/i18n';
import type { Card as CardType } from '@/services/cards';

type Tab = 'collection' | 'deck' | 'merge';
type RarityFilter = 'all' | 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary';

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
  const { user } = useAppStore();
  const { t } = useLanguage();

  const [activeTab, setActiveTab] = useState<Tab>('collection');
  const [rarityFilter, setRarityFilter] = useState<RarityFilter>('all');
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
  });

  // Fetch deck
  const { data: deckData, isLoading: deckLoading } = useQuery({
    queryKey: ['deck'],
    queryFn: () => cardsService.getDeck(),
    enabled: !!user,
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

  // Filter cards
  const filteredCards = rarityFilter === 'all'
    ? cards
    : cards.filter((c) => c.rarity === rarityFilter);

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

  // Auto-generate images for cards without them
  useEffect(() => {
    const cardsWithoutImages = cards.filter(
      (c) => !c.image_url && !generatingImages.has(c.id) && !generatedCardsRef.current.has(c.id)
    );

    if (cardsWithoutImages.length === 0) return;

    // Generate images for up to 3 cards at a time
    const cardsToGenerate = cardsWithoutImages.slice(0, 3);

    cardsToGenerate.forEach((card) => {
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
    });
  }, [cards, generatingImages, queryClient]);

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
    <div className="min-h-screen p-4 pt-safe pb-24">
      {/* Header */}
      <div className="text-center mb-4">
        <Layers className="w-10 h-10 text-purple-500 mx-auto mb-2" />
        <h1 className="text-2xl font-bold text-white">{t('deck')}</h1>
        <p className="text-sm text-gray-400">{t('deckSubtitle')}</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-gray-800 rounded-xl mb-4">
        <button
          onClick={() => setActiveTab('collection')}
          className={cn(
            'flex-1 py-2 px-2 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1',
            activeTab === 'collection'
              ? 'bg-purple-500 text-white'
              : 'text-gray-400 hover:text-white'
          )}
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">{t('collection')}</span> ({cards.length})
        </button>
        <button
          onClick={() => setActiveTab('deck')}
          className={cn(
            'flex-1 py-2 px-2 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1',
            activeTab === 'deck'
              ? 'bg-purple-500 text-white'
              : 'text-gray-400 hover:text-white'
          )}
        >
          <Layers className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">{t('deck')}</span> ({deck.length}/{maxDeckSize})
        </button>
        <button
          onClick={() => {
            setActiveTab('merge');
            clearMergeSelection();
          }}
          className={cn(
            'flex-1 py-2 px-2 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1',
            activeTab === 'merge'
              ? 'bg-gradient-to-r from-orange-500 to-pink-500 text-white'
              : 'text-gray-400 hover:text-white'
          )}
        >
          <Merge className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">{t('merge')}</span>
        </button>
      </div>

      {/* Collection Tab */}
      {activeTab === 'collection' && (
        <>
          {/* Rarity filter */}
          <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
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

          {/* Heal all button */}
          {cardsNeedHealing && (
            <Card className="mb-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <HeartPulse className="w-5 h-5 text-red-400" />
                  <span className="text-sm text-gray-300">{t('healAllCards')}</span>
                </div>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => healAllMutation.mutate()}
                  isLoading={healAllMutation.isPending}
                >
                  <Heart className="w-4 h-4 mr-1" />
                  {t('heal')}
                </Button>
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
              <div className="grid grid-cols-2 gap-3">
                {filteredCards.map((card) => (
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
                <div className="fixed bottom-20 left-4 right-4 max-w-md mx-auto z-40">
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
                <div className="fixed bottom-20 left-4 right-4 max-w-md mx-auto z-40">
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
        } : null}
      />
    </div>
  );
}
