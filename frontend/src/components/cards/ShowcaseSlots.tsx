'use client';

import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { useTranslation } from '@/lib/i18n';
import { cardsService } from '@/services/cards';
import type { Card } from '@/services/cards';
import { CardInfoSheet } from './CardInfoSheet';
import { Modal } from '@/components/ui';

interface ShowcaseSlotsProps {
  userId?: number;
  readOnly?: boolean;
}

export function ShowcaseSlots({ readOnly = false }: ShowcaseSlotsProps) {
  const { t } = useTranslation();
  const [slots, setSlots] = useState<(Card | null)[]>([null, null, null]);
  const [selectedCard, setSelectedCard] = useState<Card | null>(null);

  // Card picker state
  const [pickingSlot, setPickingSlot] = useState<number | null>(null);
  const [availableCards, setAvailableCards] = useState<Card[]>([]);
  const [loadingCards, setLoadingCards] = useState(false);

  useEffect(() => {
    loadShowcase();
  }, []);

  const loadShowcase = async () => {
    try {
      const res = await cardsService.getShowcase();
      if (res.data?.slots) {
        setSlots(res.data.slots);
      }
    } catch {
      // Silently fail
    }
  };

  const handleEmptySlotClick = async (slotIndex: number) => {
    if (readOnly) return;
    setPickingSlot(slotIndex + 1); // 1-based slot number
    setLoadingCards(true);
    try {
      const res = await cardsService.getCards();
      if (res.data?.cards) {
        // Filter out cards already in showcase slots
        const showcaseCardIds = new Set(slots.filter(Boolean).map((c) => c!.id));
        setAvailableCards(res.data.cards.filter((c) => !showcaseCardIds.has(c.id)));
      }
    } catch {
      setAvailableCards([]);
    } finally {
      setLoadingCards(false);
    }
  };

  const handlePickCard = async (card: Card) => {
    if (pickingSlot === null) return;
    try {
      await cardsService.setShowcase(card.id, pickingSlot);
      await loadShowcase();
    } catch {
      // Silently fail
    }
    setPickingSlot(null);
    setAvailableCards([]);
  };

  const rarityBorders: Record<string, string> = {
    common: 'border-slate-500/50',
    uncommon: 'border-emerald-500/50',
    rare: 'border-blue-500/50',
    epic: 'border-purple-500/50',
    legendary: 'border-amber-500/50',
  };

  const rarityGlows: Record<string, string> = {
    rare: 'shadow-[0_0_10px_rgba(59,130,246,0.2)]',
    epic: 'shadow-[0_0_15px_rgba(168,85,247,0.25)]',
    legendary: 'shadow-[0_0_20px_rgba(245,158,11,0.3)]',
  };

  const rarityBgs: Record<string, string> = {
    common: 'bg-slate-500/20',
    uncommon: 'bg-emerald-500/20',
    rare: 'bg-blue-500/20',
    epic: 'bg-purple-500/20',
    legendary: 'bg-amber-500/20',
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-gray-400">{t('showcase')}</h3>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {slots.map((card, index) => (
          <button
            key={index}
            onClick={() => card ? setSelectedCard(card) : handleEmptySlotClick(index)}
            className={cn(
              'aspect-square rounded-xl border-2 border-dashed flex items-center justify-center transition-all',
              card
                ? cn(
                    'border-solid',
                    rarityBorders[card.rarity] || 'border-gray-600',
                    rarityGlows[card.rarity] || '',
                    'bg-gray-800/50'
                  )
                : cn(
                    'border-gray-700 bg-gray-800/30',
                    !readOnly && 'hover:border-purple-500/50 hover:bg-purple-500/10 active:scale-95'
                  )
            )}
          >
            {card ? (
              <div className="flex flex-col items-center gap-1 p-2">
                {card.image_url ? (
                  <img src={card.image_url} alt={card.name} className="w-12 h-12 rounded-lg object-cover" />
                ) : (
                  <span className="text-3xl">{card.emoji || '🎴'}</span>
                )}
                <span className="text-[10px] font-medium text-gray-300 line-clamp-1 text-center w-full">
                  {card.name}
                </span>
                {card.card_level > 1 && (
                  <span className="text-[9px] font-bold text-cyan-400">
                    Lv.{card.card_level}
                  </span>
                )}
              </div>
            ) : (
              <div className="text-center">
                <span className="text-gray-600 text-2xl">+</span>
                {!readOnly && (
                  <p className="text-[9px] text-gray-600 mt-1">
                    {t('showcaseSlot').replace('{slot}', String(index + 1))}
                  </p>
                )}
              </div>
            )}
          </button>
        ))}
      </div>

      {slots.every((s) => !s) && !readOnly && (
        <p className="text-xs text-gray-500 text-center mt-2">{t('showcaseEmpty')}</p>
      )}

      <CardInfoSheet
        isOpen={!!selectedCard}
        onClose={() => setSelectedCard(null)}
        card={
          selectedCard
            ? {
                id: selectedCard.id,
                name: selectedCard.name,
                description: selectedCard.description,
                emoji: selectedCard.emoji,
                imageUrl: selectedCard.image_url,
                hp: selectedCard.hp,
                currentHp: selectedCard.current_hp,
                attack: selectedCard.attack,
                rarity: selectedCard.rarity,
                genre: selectedCard.genre,
                createdAt: selectedCard.created_at,
                abilityInfo: selectedCard.ability_info,
                cardLevel: selectedCard.card_level,
                cardXp: selectedCard.card_xp,
              }
            : null
        }
      />

      {/* Card picker modal */}
      <Modal
        isOpen={pickingSlot !== null}
        onClose={() => { setPickingSlot(null); setAvailableCards([]); }}
        title={pickingSlot !== null ? t('selectCardForSlot').replace('{slot}', String(pickingSlot)) : ''}
      >
        {loadingCards ? (
          <div className="flex justify-center py-8">
            <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : availableCards.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">{t('noCards')}</p>
        ) : (
          <div className="grid grid-cols-3 gap-3 max-h-[50vh] overflow-y-auto">
            {availableCards.map((card) => (
              <button
                key={card.id}
                onClick={() => handlePickCard(card)}
                className={cn(
                  'rounded-xl border-2 p-2 flex flex-col items-center gap-1 transition-all active:scale-95',
                  rarityBorders[card.rarity] || 'border-gray-600',
                  rarityBgs[card.rarity] || 'bg-gray-800/50'
                )}
              >
                {card.image_url ? (
                  <img src={card.image_url} alt={card.name} className="w-12 h-12 rounded-lg object-cover" />
                ) : (
                  <span className="text-2xl">{card.emoji || '🎴'}</span>
                )}
                <span className="text-[10px] font-medium text-gray-300 line-clamp-1 text-center w-full">
                  {card.name}
                </span>
                <span className={cn(
                  'text-[9px] font-bold px-1.5 py-0.5 rounded-full text-white',
                  card.rarity === 'legendary' ? 'bg-amber-500' :
                  card.rarity === 'epic' ? 'bg-purple-500' :
                  card.rarity === 'rare' ? 'bg-blue-500' :
                  card.rarity === 'uncommon' ? 'bg-emerald-500' : 'bg-slate-500'
                )}>
                  {t(
                    card.rarity === 'legendary' ? 'rarityLegendary' :
                    card.rarity === 'epic' ? 'rarityEpic' :
                    card.rarity === 'rare' ? 'rarityRare' :
                    card.rarity === 'uncommon' ? 'rarityUncommon' : 'rarityCommon'
                  )}
                </span>
              </button>
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
}

export default ShowcaseSlots;
