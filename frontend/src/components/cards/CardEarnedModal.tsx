'use client';

import { useState, useEffect } from 'react';
import { Sparkles, Heart, Swords } from 'lucide-react';
import { Button, Modal } from '@/components/ui';
import { cardsService } from '@/services';
import type { TranslationKey } from '@/lib/i18n';

// Card type for earned card modal
export interface EarnedCard {
  id: number;
  name: string;
  description: string;
  genre: string;
  rarity: string;
  hp: number;
  attack: number;
  emoji: string;
  image_url?: string | null;
}

// Rarity colors
const RARITY_COLORS: Record<string, string> = {
  common: 'from-gray-500 to-gray-600',
  uncommon: 'from-green-500 to-green-600',
  rare: 'from-blue-500 to-blue-600',
  epic: 'from-purple-500 to-purple-600',
  legendary: 'from-yellow-500 to-orange-500',
};

const RARITY_TRANSLATION_KEYS: Record<string, string> = {
  common: 'rarityCommon',
  uncommon: 'rarityUncommon',
  rare: 'rarityRare',
  epic: 'rarityEpic',
  legendary: 'rarityLegendary',
};

interface CardEarnedModalProps {
  isOpen: boolean;
  card: EarnedCard | null;
  onClose: () => void;
  t: (key: TranslationKey) => string;
}

export function CardEarnedModal({ isOpen, card, onClose, t }: CardEarnedModalProps) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  // Trigger async image generation when modal opens with a card
  useEffect(() => {
    if (isOpen && card && !card.image_url && !isGenerating) {
      setIsGenerating(true);
      setImageUrl(null);

      // Call the async image generation endpoint
      cardsService.generateCardImage(card.id)
        .then((result) => {
          if (result.success && result.data?.image_url) {
            setImageUrl(result.data.image_url);
          }
        })
        .catch((err) => {
          console.error('Failed to generate card image:', err);
        })
        .finally(() => {
          setIsGenerating(false);
        });
    } else if (card?.image_url) {
      setImageUrl(card.image_url);
    }
  }, [isOpen, card]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setImageUrl(null);
      setIsGenerating(false);
    }
  }, [isOpen]);

  if (!card) return null;

  const displayImageUrl = imageUrl || card.image_url;
  const rarityKey = (RARITY_TRANSLATION_KEYS[card.rarity] || 'rarityCommon') as TranslationKey;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={t('newCardTitle')}>
      <div className="flex flex-col items-center">
        {/* Card Preview */}
        <div className={`w-48 h-64 rounded-2xl bg-gradient-to-br ${RARITY_COLORS[card.rarity] || RARITY_COLORS.common} p-1 mb-4`}>
          <div className="w-full h-full bg-gray-900 rounded-xl flex flex-col overflow-hidden">
            {/* Card Image or Emoji */}
            <div className="flex-1 flex items-center justify-center bg-gray-800 relative">
              {displayImageUrl ? (
                <img
                  src={displayImageUrl}
                  alt={card.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <span className="text-5xl">{card.emoji}</span>
                  {isGenerating && (
                    <div className="absolute bottom-2 left-0 right-0 text-center">
                      <span className="text-xs text-gray-400 animate-pulse">
                        {t('cardImageGenerating')}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Card Info */}
            <div className="p-2 space-y-1">
              <p className="text-white font-bold text-sm truncate">{card.name}</p>
              <p className="text-gray-400 text-xs truncate">{card.description}</p>

              {/* Stats */}
              <div className="flex justify-between text-xs pt-1">
                <span className="text-red-400 flex items-center gap-1">
                  <Heart className="w-3 h-3" /> {card.hp}
                </span>
                <span className="text-orange-400 flex items-center gap-1">
                  <Swords className="w-3 h-3" /> {card.attack}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Rarity Badge */}
        <div className={`px-4 py-1 rounded-full bg-gradient-to-r ${RARITY_COLORS[card.rarity] || RARITY_COLORS.common} mb-4`}>
          <span className="text-white font-bold text-sm flex items-center gap-1">
            <Sparkles className="w-4 h-4" />
            {t(rarityKey)}
          </span>
        </div>

        <p className="text-gray-400 text-sm text-center mb-4">
          {t('cardAddedToCollection')}
        </p>

        <Button onClick={onClose} className="w-full">
          {t('great')}
        </Button>
      </div>
    </Modal>
  );
}
