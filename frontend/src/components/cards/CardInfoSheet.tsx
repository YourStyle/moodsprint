'use client';

import { useState } from 'react';
import { Heart, Swords, Sparkles, Calendar, DollarSign } from 'lucide-react';
import { Modal, Button } from '@/components/ui';
import { cn } from '@/lib/utils';
import { SellCardModal } from '@/components/marketplace';

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
  } | null;
  showSellButton?: boolean;
}

const rarityConfig = {
  common: {
    gradient: 'from-slate-500 to-slate-600',
    label: 'Обычная',
    accent: 'text-slate-300',
  },
  uncommon: {
    gradient: 'from-emerald-500 to-emerald-600',
    label: 'Необычная',
    accent: 'text-emerald-400',
  },
  rare: {
    gradient: 'from-blue-500 to-blue-600',
    label: 'Редкая',
    accent: 'text-blue-400',
  },
  epic: {
    gradient: 'from-purple-500 to-purple-600',
    label: 'Эпическая',
    accent: 'text-purple-400',
  },
  legendary: {
    gradient: 'from-amber-500 to-orange-500',
    label: 'Легендарная',
    accent: 'text-amber-400',
  },
};

const genreLabels: Record<string, string> = {
  magic: 'Магия',
  fantasy: 'Фэнтези',
  scifi: 'Sci-Fi',
  cyberpunk: 'Киберпанк',
  anime: 'Аниме',
};

export function CardInfoSheet({ isOpen, onClose, card, showSellButton = false }: CardInfoSheetProps) {
  const [showSellModal, setShowSellModal] = useState(false);

  if (!card) return null;

  const config = rarityConfig[card.rarity as keyof typeof rarityConfig] || rarityConfig.common;
  const canSell = showSellButton && card.id && card.isOwned !== false;

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
            {config.label}
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
              <div className="text-orange-300/70 text-xs">Атака</div>
            </div>
          </div>
          <div className="flex items-center justify-center gap-2 bg-green-500/20 rounded-xl p-3">
            <Heart className="w-5 h-5 text-green-400" />
            <div className="text-center">
              <div className="text-green-400 font-bold text-lg">{card.currentHp}/{card.hp}</div>
              <div className="text-green-300/70 text-xs">Здоровье</div>
            </div>
          </div>
        </div>

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
                Перезарядка: {card.abilityInfo.cooldown} ход(а)
              </p>
            )}
          </div>
        )}

        {/* Meta Info */}
        <div className="w-full space-y-2 text-sm">
          {card.genre && (
            <div className="flex justify-between text-gray-400">
              <span>Жанр</span>
              <span className="text-white">{genreLabels[card.genre] || card.genre}</span>
            </div>
          )}
          {card.createdAt && (
            <div className="flex justify-between text-gray-400">
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                Получена
              </span>
              <span className="text-white">{formatDate(card.createdAt)}</span>
            </div>
          )}
        </div>

        {/* Sell Button */}
        {canSell && (
          <Button
            onClick={() => setShowSellModal(true)}
            className="w-full mt-4 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600"
          >
            <DollarSign className="w-4 h-4 mr-2" />
            Продать за Stars
          </Button>
        )}
        </div>
      </div>

      {/* Sell Card Modal */}
      {canSell && (
        <SellCardModal
          isOpen={showSellModal}
          onClose={() => setShowSellModal(false)}
          card={{
            id: card.id!,
            name: card.name,
            emoji: card.emoji,
            imageUrl: card.imageUrl ?? undefined,
            rarity: card.rarity,
            attack: card.attack,
            hp: card.hp,
          }}
          onSuccess={onClose}
        />
      )}
    </Modal>
  );
}

export default CardInfoSheet;
