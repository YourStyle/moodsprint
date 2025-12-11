'use client';

import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Layers,
  Swords,
  Heart,
  Plus,
  Minus,
  Sparkles,
  Filter,
  HeartPulse,
} from 'lucide-react';
import { Card, Button, Progress } from '@/components/ui';
import { cardsService } from '@/services';
import { useAppStore } from '@/lib/store';
import { hapticFeedback } from '@/lib/telegram';
import { cn } from '@/lib/utils';
import type { Card as CardType } from '@/services/cards';

type Tab = 'collection' | 'deck';
type RarityFilter = 'all' | 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary';

const RARITY_INFO = {
  common: { label: 'Обычная', color: '#9CA3AF', bgClass: 'from-gray-500/20 to-gray-600/20' },
  uncommon: { label: 'Необычная', color: '#22C55E', bgClass: 'from-green-500/20 to-emerald-600/20' },
  rare: { label: 'Редкая', color: '#3B82F6', bgClass: 'from-blue-500/20 to-cyan-600/20' },
  epic: { label: 'Эпическая', color: '#A855F7', bgClass: 'from-purple-500/20 to-violet-600/20' },
  legendary: { label: 'Легендарная', color: '#F59E0B', bgClass: 'from-yellow-500/20 to-orange-600/20' },
};

export default function DeckPage() {
  const queryClient = useQueryClient();
  const { user } = useAppStore();

  const [activeTab, setActiveTab] = useState<Tab>('collection');
  const [rarityFilter, setRarityFilter] = useState<RarityFilter>('all');
  const [selectedCard, setSelectedCard] = useState<CardType | null>(null);

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
    },
  });

  // Remove from deck mutation
  const removeFromDeckMutation = useMutation({
    mutationFn: (cardId: number) => cardsService.removeFromDeck(cardId),
    onSuccess: () => {
      hapticFeedback('light');
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      queryClient.invalidateQueries({ queryKey: ['deck'] });
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
            // Refresh cards data to get new image
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
        <p className="text-gray-500">Войдите чтобы увидеть колоду</p>
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

  const renderCard = (card: CardType, showDeckActions: boolean = true) => {
    const rarityInfo = RARITY_INFO[card.rarity];
    const isSelected = selectedCard?.id === card.id;
    const healthPercent = (card.current_hp / card.hp) * 100;
    const isGenerating = generatingImages.has(card.id);

    return (
      <div
        key={card.id}
        className={cn(
          'relative rounded-xl border transition-all cursor-pointer',
          `bg-gradient-to-br ${rarityInfo.bgClass}`,
          isSelected ? 'ring-2 ring-purple-500 scale-[1.02]' : 'hover:scale-[1.01]'
        )}
        style={{ borderColor: rarityInfo.color + '50' }}
        onClick={() => handleCardClick(card)}
      >
        {/* Rarity badge */}
        <div
          className="absolute -top-2 left-3 px-2 py-0.5 rounded-full text-xs font-medium text-white"
          style={{ backgroundColor: rarityInfo.color }}
        >
          {rarityInfo.label}
        </div>

        <div className="p-3 pt-4">
          {/* Card header */}
          <div className="flex items-start gap-3 mb-2">
            {card.image_url ? (
              <img
                src={card.image_url}
                alt={card.name}
                className="w-14 h-14 rounded-lg object-cover"
              />
            ) : (
              <div
                className="w-14 h-14 rounded-lg flex items-center justify-center text-3xl relative"
                style={{ backgroundColor: rarityInfo.color + '30' }}
              >
                {card.emoji}
                {isGenerating && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/30 rounded-lg">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  </div>
                )}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-white truncate">{card.name}</h3>
              <p className="text-xs text-gray-400 capitalize">{card.genre}</p>
            </div>
          </div>

          {/* Stats */}
          <div className="flex items-center gap-4 mb-2 text-sm">
            <div className="flex items-center gap-1">
              <Swords className="w-4 h-4 text-red-400" />
              <span className="text-white">{card.attack}</span>
            </div>
            <div className="flex items-center gap-1">
              <Heart className="w-4 h-4 text-green-400" />
              <span className="text-white">{card.hp}</span>
            </div>
          </div>

          {/* Health bar */}
          <div className="mb-2">
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-400">HP</span>
              <span className={cn(
                healthPercent < 30 ? 'text-red-400' :
                healthPercent < 70 ? 'text-yellow-400' : 'text-green-400'
              )}>
                {card.current_hp}/{card.hp}
              </span>
            </div>
            <Progress
              value={card.current_hp}
              max={card.hp}
              size="sm"
              color={healthPercent < 30 ? 'error' : healthPercent < 70 ? 'warning' : 'success'}
            />
          </div>

          {/* Description (on select) */}
          {isSelected && card.description && (
            <p className="text-xs text-gray-300 mb-3 line-clamp-2">
              {card.description}
            </p>
          )}

          {/* Actions */}
          {showDeckActions && isSelected && (
            <div className="flex gap-2">
              {card.is_in_deck ? (
                <Button
                  size="sm"
                  variant="secondary"
                  className="flex-1"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemoveFromDeck(card.id);
                  }}
                  isLoading={removeFromDeckMutation.isPending}
                >
                  <Minus className="w-4 h-4 mr-1" />
                  Убрать
                </Button>
              ) : (
                <Button
                  size="sm"
                  className="flex-1"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleAddToDeck(card.id);
                  }}
                  isLoading={addToDeckMutation.isPending}
                  disabled={deck.length >= maxDeckSize}
                >
                  <Plus className="w-4 h-4 mr-1" />
                  В колоду
                </Button>
              )}
            </div>
          )}
        </div>

        {/* In deck indicator */}
        {card.is_in_deck && (
          <div className="absolute -top-2 -right-2 w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center">
            <Layers className="w-3 h-3 text-white" />
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen p-4 pt-safe pb-24">
      {/* Header */}
      <div className="text-center mb-4">
        <Layers className="w-10 h-10 text-purple-500 mx-auto mb-2" />
        <h1 className="text-2xl font-bold text-white">Колода</h1>
        <p className="text-sm text-gray-400">Собирай карты, побеждай монстров</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 p-1 bg-gray-800 rounded-xl mb-4">
        <button
          onClick={() => setActiveTab('collection')}
          className={cn(
            'flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2',
            activeTab === 'collection'
              ? 'bg-purple-500 text-white'
              : 'text-gray-400 hover:text-white'
          )}
        >
          <Sparkles className="w-4 h-4" />
          Коллекция ({cards.length})
        </button>
        <button
          onClick={() => setActiveTab('deck')}
          className={cn(
            'flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2',
            activeTab === 'deck'
              ? 'bg-purple-500 text-white'
              : 'text-gray-400 hover:text-white'
          )}
        >
          <Layers className="w-4 h-4" />
          Колода ({deck.length}/{maxDeckSize})
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
              Все
            </button>
            {Object.entries(RARITY_INFO).map(([rarity, info]) => (
              <button
                key={rarity}
                onClick={() => setRarityFilter(rarity as RarityFilter)}
                className={cn(
                  'px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all',
                  rarityFilter === rarity
                    ? 'text-white'
                    : 'bg-gray-800 text-gray-400'
                )}
                style={rarityFilter === rarity ? { backgroundColor: info.color } : {}}
              >
                {info.label} ({rarityCounts[rarity] || 0})
              </button>
            ))}
          </div>

          {/* Heal all button */}
          {cardsNeedHealing && (
            <Card className="mb-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <HeartPulse className="w-5 h-5 text-red-400" />
                  <span className="text-sm text-gray-300">Вылечить все карты</span>
                </div>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => healAllMutation.mutate()}
                  isLoading={healAllMutation.isPending}
                >
                  <Heart className="w-4 h-4 mr-1" />
                  Лечить
                </Button>
              </div>
            </Card>
          )}

          {/* Cards grid */}
          {cardsLoading ? (
            <div className="grid grid-cols-2 gap-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-48 bg-gray-800 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : filteredCards.length === 0 ? (
            <Card className="text-center py-8">
              <Sparkles className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400">
                {rarityFilter === 'all'
                  ? 'Пока нет карт'
                  : `Нет карт редкости "${RARITY_INFO[rarityFilter].label}"`}
              </p>
              <p className="text-sm text-gray-500 mt-1">
                Выполняй задачи чтобы получать карты!
              </p>
            </Card>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {filteredCards.map((card) => renderCard(card))}
            </div>
          )}
        </>
      )}

      {/* Deck Tab */}
      {activeTab === 'deck' && (
        <>
          {/* Deck stats */}
          {deckStats && deck.length > 0 && (
            <Card className="mb-4">
              <h3 className="text-sm font-medium text-white mb-3">Статистика колоды</h3>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div>
                  <p className="text-lg font-bold text-red-400">{deckStats.total_attack}</p>
                  <p className="text-xs text-gray-500">Атака</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-green-400">{deckStats.total_hp}</p>
                  <p className="text-xs text-gray-500">HP</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-purple-400">{deckStats.genres.length}</p>
                  <p className="text-xs text-gray-500">Жанров</p>
                </div>
              </div>
            </Card>
          )}

          {/* Deck cards */}
          {deckLoading ? (
            <div className="grid grid-cols-2 gap-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-48 bg-gray-800 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : deck.length === 0 ? (
            <Card className="text-center py-8">
              <Layers className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400">Колода пуста</p>
              <p className="text-sm text-gray-500 mt-1">
                Добавь карты из коллекции для боя
              </p>
              <Button
                size="sm"
                className="mt-4"
                onClick={() => setActiveTab('collection')}
              >
                Перейти в коллекцию
              </Button>
            </Card>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {deck.map((card) => renderCard(card))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
