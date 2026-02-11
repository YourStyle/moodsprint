'use client';

import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { useTranslation } from '@/lib/i18n';
import { cardsService } from '@/services/cards';
import type { Card } from '@/services/cards';
import { CardInfoSheet } from './CardInfoSheet';

interface ShowcaseSlotsProps {
  userId?: number;
  readOnly?: boolean;
}

export function ShowcaseSlots({ readOnly = false }: ShowcaseSlotsProps) {
  const { t } = useTranslation();
  const [slots, setSlots] = useState<(Card | null)[]>([null, null, null]);
  const [selectedCard, setSelectedCard] = useState<Card | null>(null);

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

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-gray-400">{t('showcase')}</h3>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {slots.map((card, index) => (
          <button
            key={index}
            onClick={() => card && setSelectedCard(card)}
            className={cn(
              'aspect-square rounded-xl border-2 border-dashed flex items-center justify-center transition-all',
              card
                ? cn(
                    'border-solid',
                    rarityBorders[card.rarity] || 'border-gray-600',
                    rarityGlows[card.rarity] || '',
                    'bg-gray-800/50'
                  )
                : 'border-gray-700 bg-gray-800/30'
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
    </div>
  );
}

export default ShowcaseSlots;
