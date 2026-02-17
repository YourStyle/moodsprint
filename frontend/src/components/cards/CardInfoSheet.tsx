'use client';

import { useState } from 'react';
import { Heart, Swords, Sparkles, Calendar, Zap, Layers, Minus, Star } from 'lucide-react';
import { Modal } from '@/components/ui';
import { cn } from '@/lib/utils';
import { useTranslation } from '@/lib/i18n';

interface AbilityInfo {
  type: string;
  name: string;
  description: string;
  emoji: string;
  cooldown: number;
  current_cooldown: number;
}

interface CardInfoSheetProps {
  isOpen: boolean;
  onClose: () => void;
  card: {
    id?: number;
    name: string;
    description?: string | null;
    emoji?: string;
    imageUrl?: string | null;
    hp: number;
    currentHp: number;
    attack: number;
    rarity: string;
    genre?: string;
    createdAt?: string | null;
    abilityInfo?: AbilityInfo | null;
    isOwned?: boolean;
    cardLevel?: number;
    cardXp?: number;
    isCompanion?: boolean;
  } | null;
  isInDeck?: boolean;
  onAddToDeck?: (id: number) => void;
  onRemoveFromDeck?: (id: number) => void;
  onAddToShowcase?: (id: number, slot: number) => void;
  showcaseSlot?: number | null;
  onRemoveFromShowcase?: (slot: number) => void;
  onSetCompanion?: (id: number) => void;
  onRemoveCompanion?: () => void;
  isDeckFull?: boolean;
  onGoToDeck?: () => void;
}

const rarityStyles = {
  common: {
    gradient: 'from-slate-500 to-slate-600',
    labelKey: 'rarityCommon' as const,
    accent: 'text-slate-300',
  },
  uncommon: {
    gradient: 'from-emerald-500 to-emerald-600',
    labelKey: 'rarityUncommon' as const,
    accent: 'text-emerald-400',
  },
  rare: {
    gradient: 'from-blue-500 to-blue-600',
    labelKey: 'rarityRare' as const,
    accent: 'text-blue-400',
  },
  epic: {
    gradient: 'from-purple-500 to-purple-600',
    labelKey: 'rarityEpic' as const,
    accent: 'text-purple-400',
  },
  legendary: {
    gradient: 'from-amber-500 to-orange-500',
    labelKey: 'rarityLegendary' as const,
    accent: 'text-amber-400',
  },
};

const genreKeys: Record<string, 'genreMagic' | 'genreFantasy' | 'genreScifi' | 'genreCyberpunk' | 'genreAnime'> = {
  magic: 'genreMagic',
  fantasy: 'genreFantasy',
  scifi: 'genreScifi',
  cyberpunk: 'genreCyberpunk',
  anime: 'genreAnime',
};

export function CardInfoSheet({ isOpen, onClose, card, isInDeck, onAddToDeck, onRemoveFromDeck, onAddToShowcase, showcaseSlot, onRemoveFromShowcase, onSetCompanion, onRemoveCompanion, isDeckFull, onGoToDeck }: CardInfoSheetProps) {
  const { t } = useTranslation();
  const [showSlotPicker, setShowSlotPicker] = useState(false);

  if (!card) return null;

  const config = rarityStyles[card.rarity as keyof typeof rarityStyles] || rarityStyles.common;

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} showClose={true}>
      <div className="flex flex-col items-center -mx-4 -mt-4">
        {/* Full-width Card Image at top */}
        <div className="w-full aspect-square overflow-hidden mb-4 relative">
          {card.imageUrl ? (
            <img
              src={card.imageUrl}
              alt={card.name}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-700 to-gray-800">
              <span className="text-6xl">{card.emoji || '🎴'}</span>
            </div>
          )}
          {/* Rarity badge on image */}
          <div className={cn(
            'absolute top-3 left-3 px-3 py-1 rounded-full text-xs font-bold text-white',
            `bg-gradient-to-r ${config.gradient}`
          )}>
            {t(config.labelKey)}
          </div>
        </div>

        {/* Content with padding */}
        <div className="px-4 w-full">
        {/* Name */}
        <h2 className={cn('text-xl font-bold mb-4 text-center', config.accent)}>
          {card.name}
        </h2>

        {/* Description */}
        {card.description && (
          <p className="text-gray-300 text-sm text-center mb-6 leading-relaxed">
            {card.description}
          </p>
        )}

        {/* Stats */}
        <div className="w-full grid grid-cols-2 gap-3 mb-4">
          <div className="flex items-center justify-center gap-2 bg-orange-500/20 rounded-xl p-3">
            <Swords className="w-5 h-5 text-orange-400" />
            <div className="text-center">
              <div className="text-orange-400 font-bold text-lg">{card.attack}</div>
              <div className="text-orange-300/70 text-xs">{t('attack')}</div>
            </div>
          </div>
          <div className="flex items-center justify-center gap-2 bg-green-500/20 rounded-xl p-3">
            <Heart className="w-5 h-5 text-green-400" />
            <div className="text-center">
              <div className="text-green-400 font-bold text-lg">{card.currentHp}/{card.hp}</div>
              <div className="text-green-300/70 text-xs">{t('health')}</div>
            </div>
          </div>
        </div>

        {/* Card Level & XP */}
        {card.cardLevel && card.cardLevel > 0 && (
          <div className="w-full bg-cyan-500/20 rounded-xl p-4 mb-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-cyan-400" />
                <span className="text-cyan-400 font-bold text-sm">
                  {t('cardLevel').replace('{level}', String(card.cardLevel))}
                </span>
              </div>
              {card.isCompanion && (
                <span className="px-2 py-0.5 bg-pink-500/30 rounded-full text-[10px] font-bold text-pink-400">
                  🐾 {t('companion')}
                </span>
              )}
            </div>
            {/* XP Progress bar */}
            {(() => {
              const maxLevelByRarity: Record<string, number> = {
                common: 3, uncommon: 5, rare: 7, epic: 10, legendary: 15,
              };
              const maxLevel = maxLevelByRarity[card.rarity] || 3;
              const xpNeeded = card.cardLevel * 100;
              const xpCurrent = card.cardXp || 0;
              const isMaxLevel = card.cardLevel >= maxLevel;
              const progress = isMaxLevel ? 100 : Math.min(100, (xpCurrent / xpNeeded) * 100);

              return (
                <div>
                  <div className="flex justify-between text-xs text-gray-400 mb-1">
                    <span>{isMaxLevel ? t('cardMaxLevel') : t('cardXp').replace('{current}', String(xpCurrent)).replace('{max}', String(xpNeeded))}</span>
                  </div>
                  <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={cn(
                        'h-full rounded-full transition-all duration-300',
                        isMaxLevel ? 'bg-gradient-to-r from-amber-400 to-yellow-500' : 'bg-gradient-to-r from-cyan-400 to-blue-500'
                      )}
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>
              );
            })()}
          </div>
        )}

        {/* Ability */}
        {card.abilityInfo && (
          <div className="w-full bg-purple-500/20 rounded-xl p-4 mb-4">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-purple-400" />
              <span className="text-purple-400 font-bold text-sm">
                {card.abilityInfo.emoji} {card.abilityInfo.name}
              </span>
            </div>
            <p className="text-gray-300 text-sm leading-relaxed">
              {card.abilityInfo.description}
            </p>
            {card.abilityInfo.cooldown > 0 && (
              <p className="text-gray-500 text-xs mt-2">
                {t('cooldownTurns')}: {card.abilityInfo.cooldown} {card.abilityInfo.cooldown === 1 ? t('turn') : t('turns')}
              </p>
            )}
          </div>
        )}

        {/* Meta Info */}
        <div className="w-full space-y-2 text-sm">
          {card.genre && (
            <div className="flex justify-between text-gray-400">
              <span>{t('genre')}</span>
              <span className="text-white">{t(genreKeys[card.genre] || 'genreFantasy')}</span>
            </div>
          )}
          {card.createdAt && (
            <div className="flex justify-between text-gray-400">
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                {t('received')}
              </span>
              <span className="text-white">{formatDate(card.createdAt)}</span>
            </div>
          )}
        </div>

        {/* Actions */}
        {card.id && card.isOwned !== false && (
          <div className="w-full mt-4 space-y-2">
            {/* Deck button */}
            {isInDeck && onRemoveFromDeck ? (
              <button
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-red-500/15 hover:bg-red-500/25 text-red-300 text-sm transition-colors"
                onClick={() => { onRemoveFromDeck(card.id!); onClose(); }}
              >
                <Minus className="w-4 h-4 text-red-400" />
                {t('removeFromDeck')}
              </button>
            ) : !isInDeck && isDeckFull && onGoToDeck ? (
              <button
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-purple-500/15 hover:bg-purple-500/25 text-purple-300 text-sm transition-colors"
                onClick={() => { onGoToDeck(); onClose(); }}
              >
                <Layers className="w-4 h-4 text-purple-400" />
                {t('goToDeck')}
              </button>
            ) : !isInDeck && onAddToDeck ? (
              <button
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-purple-500/15 hover:bg-purple-500/25 text-purple-300 text-sm transition-colors"
                onClick={() => { onAddToDeck(card.id!); onClose(); }}
              >
                <Layers className="w-4 h-4 text-purple-400" />
                {t('addToDeck')}
              </button>
            ) : null}

            {/* Companion button */}
            {card.isCompanion && onRemoveCompanion ? (
              <button
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-red-500/15 hover:bg-red-500/25 text-red-300 text-sm transition-colors"
                onClick={() => { onRemoveCompanion(); onClose(); }}
              >
                <span className="text-sm">🐾</span>
                {t('removeCompanion')}
              </button>
            ) : !card.isCompanion && onSetCompanion ? (
              <button
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-pink-500/15 hover:bg-pink-500/25 text-pink-300 text-sm transition-colors"
                onClick={() => { onSetCompanion(card.id!); onClose(); }}
              >
                <span className="text-sm">🐾</span>
                {t('setCompanion')}
              </button>
            ) : null}

            {/* Showcase button */}
            {onAddToShowcase && (
              <>
                {!showSlotPicker ? (
                  <button
                    className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 text-sm transition-colors"
                    onClick={() => setShowSlotPicker(true)}
                  >
                    <Star className="w-4 h-4 text-amber-400" />
                    {t('addToShowcase')}
                  </button>
                ) : (
                  <div className="bg-amber-500/15 rounded-xl p-3">
                    <p className="text-xs text-amber-300/70 mb-2 text-center">{t('selectSlot')}</p>
                    <div className="flex gap-2">
                      {[1, 2, 3].map((slot) => (
                        <button
                          key={slot}
                          className="flex-1 py-2 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-xs transition-colors"
                          onClick={() => {
                            onAddToShowcase(card.id!, slot);
                            setShowSlotPicker(false);
                            onClose();
                          }}
                        >
                          {t('slot')} {slot}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Remove from Showcase */}
            {showcaseSlot != null && onRemoveFromShowcase && (
              <button
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-red-500/15 hover:bg-red-500/25 text-red-300 text-sm transition-colors"
                onClick={() => { onRemoveFromShowcase(showcaseSlot); onClose(); }}
              >
                <Star className="w-4 h-4 text-red-400" />
                {t('removeFromShowcase')}
              </button>
            )}

          </div>
        )}
        </div>
      </div>

    </Modal>
  );
}

export default CardInfoSheet;
