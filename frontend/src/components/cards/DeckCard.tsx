'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { Heart, Swords, Info, Layers, Calendar } from 'lucide-react';

export interface DeckCardProps {
  id: number;
  name: string;
  description?: string | null;
  emoji?: string;
  imageUrl?: string | null;
  hp: number;
  currentHp: number;
  attack: number;
  rarity: string;
  genre?: string;
  isInDeck?: boolean;
  isGenerating?: boolean;
  createdAt?: string | null;
  onClick?: () => void;
  compact?: boolean;
}

const rarityConfig = {
  common: {
    gradient: 'from-slate-600/30 to-slate-700/30',
    border: 'border-slate-500/50',
    glow: '',
    label: 'Обычная',
    labelBg: 'bg-slate-500',
    accent: 'text-slate-300',
  },
  uncommon: {
    gradient: 'from-emerald-600/30 to-emerald-700/30',
    border: 'border-emerald-500/50',
    glow: 'shadow-[0_0_15px_rgba(16,185,129,0.2)]',
    label: 'Необычная',
    labelBg: 'bg-emerald-500',
    accent: 'text-emerald-400',
  },
  rare: {
    gradient: 'from-blue-600/30 to-blue-700/30',
    border: 'border-blue-500/50',
    glow: 'shadow-[0_0_20px_rgba(59,130,246,0.3)]',
    label: 'Редкая',
    labelBg: 'bg-blue-500',
    accent: 'text-blue-400',
  },
  epic: {
    gradient: 'from-purple-600/30 to-purple-700/30',
    border: 'border-purple-500/50',
    glow: 'shadow-[0_0_25px_rgba(168,85,247,0.35)]',
    label: 'Эпическая',
    labelBg: 'bg-purple-500',
    accent: 'text-purple-400',
  },
  legendary: {
    gradient: 'from-amber-600/30 to-orange-700/30',
    border: 'border-amber-500/50',
    glow: 'shadow-[0_0_30px_rgba(245,158,11,0.4)]',
    label: 'Легендарная',
    labelBg: 'bg-gradient-to-r from-amber-500 to-orange-500',
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

export function DeckCard({
  name,
  description,
  emoji,
  imageUrl,
  hp,
  currentHp,
  attack,
  rarity,
  genre,
  isInDeck = false,
  isGenerating = false,
  createdAt,
  onClick,
  compact = false,
}: DeckCardProps) {
  const [isFlipped, setIsFlipped] = useState(false);
  const config = rarityConfig[rarity as keyof typeof rarityConfig] || rarityConfig.common;

  const handleInfoClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!compact) {
      setIsFlipped(!isFlipped);
    }
  };

  const handleCardClick = () => {
    if (isFlipped && !compact) {
      setIsFlipped(false);
    } else {
      onClick?.();
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
  };

  return (
    <div
      className="relative w-full aspect-[3/4] perspective-1000"
      onClick={handleCardClick}
    >
      <div
        className={cn(
          'relative w-full h-full transition-transform duration-500 transform-style-3d cursor-pointer',
          isFlipped && 'rotate-y-180'
        )}
      >
        {/* Front Side */}
        <div
          className={cn(
            'absolute inset-0 backface-hidden rounded-xl overflow-hidden',
            'border-2',
            config.border,
            config.glow
          )}
        >
          <div className={cn('absolute inset-0 bg-gradient-to-br', config.gradient)} />

          <div className="relative h-full flex flex-col p-2">
            {/* Rarity badge */}
            {!compact && (
              <div
                className={cn(
                  'absolute -top-0.5 left-2 px-2 py-0.5 rounded-b-md text-[10px] font-bold text-white z-10',
                  config.labelBg
                )}
              >
                {config.label}
              </div>
            )}

            {/* Info button */}
            {!compact && (
              <button
                onClick={handleInfoClick}
                className={cn(
                  'absolute top-1.5 right-1.5 z-10',
                  'w-6 h-6 rounded-full',
                  'bg-gray-800/80 backdrop-blur-sm border border-white/20',
                  'flex items-center justify-center',
                  'hover:bg-gray-700/80 transition-colors'
                )}
              >
                <Info className="w-3.5 h-3.5 text-white/80" />
              </button>
            )}

            {/* In deck indicator */}
            {isInDeck && !compact && (
              <div className="absolute top-1.5 left-1.5 z-10 w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center">
                <Layers className="w-3 h-3 text-white" />
              </div>
            )}

            {/* Image - takes most of the space */}
            <div className={cn(
              'flex-1 rounded-lg overflow-hidden border border-white/10',
              compact ? 'mt-1 mb-1' : 'mt-4 mb-2'
            )}>
              {imageUrl ? (
                <img
                  src={imageUrl}
                  alt={name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-gradient-to-b from-gray-700/50 to-gray-800/50 relative">
                  <span className="text-4xl">{emoji || '🎴'}</span>
                  {isGenerating && (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/40">
                      <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Name - below image, up to 2 lines */}
            <div className={cn('px-1', compact ? 'py-0.5' : 'py-1')}>
              <h3 className={cn(
                'font-bold text-center leading-tight line-clamp-2',
                compact ? 'text-[10px]' : 'text-sm',
                config.accent
              )}>
                {name}
              </h3>
            </div>

            {/* Stats at bottom - no health bar */}
            <div className={cn(
              'flex items-center justify-center bg-gray-900/50 rounded-lg mt-auto',
              compact ? 'gap-2 py-1' : 'gap-4 py-1.5'
            )}>
              <div className="flex items-center gap-0.5">
                <Swords className={cn(compact ? 'w-3 h-3' : 'w-4 h-4', 'text-orange-400')} />
                <span className={cn('font-bold text-white', compact ? 'text-[10px]' : 'text-sm')}>{attack}</span>
              </div>
              <div className={cn('w-px bg-gray-600', compact ? 'h-3' : 'h-4')} />
              <div className="flex items-center gap-0.5">
                <Heart className={cn(
                  compact ? 'w-3 h-3' : 'w-4 h-4',
                  currentHp < hp * 0.3 ? 'text-red-400' :
                  currentHp < hp * 0.7 ? 'text-yellow-400' : 'text-green-400'
                )} />
                <span className={cn(
                  'font-bold',
                  compact ? 'text-[10px]' : 'text-sm',
                  currentHp < hp * 0.3 ? 'text-red-400' :
                  currentHp < hp * 0.7 ? 'text-yellow-400' : 'text-green-400'
                )}>
                  {currentHp}/{hp}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Back Side - Description */}
        <div
          className={cn(
            'absolute inset-0 backface-hidden rotate-y-180 rounded-xl overflow-hidden',
            'border-2',
            config.border,
            config.glow
          )}
        >
          <div className={cn('absolute inset-0 bg-gradient-to-br', config.gradient)} />

          <div className="relative h-full flex flex-col p-3">
            {/* Header */}
            <div className="text-center mb-3">
              <span className="text-2xl">{emoji || '🎴'}</span>
              <h3 className={cn('font-bold text-sm mt-1', config.accent)}>
                {name}
              </h3>
              <span className={cn(
                'inline-block mt-1 px-2 py-0.5 rounded-full text-[10px] font-medium text-white',
                config.labelBg
              )}>
                {config.label}
              </span>
            </div>

            {/* Description */}
            <div className="flex-1 overflow-auto">
              <p className="text-xs text-gray-300 leading-relaxed">
                {description || 'Нет описания'}
              </p>
            </div>

            {/* Metadata */}
            <div className="mt-3 pt-2 border-t border-white/10 space-y-1.5">
              {genre && (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-500">Жанр</span>
                  <span className="text-gray-300">{genreLabels[genre] || genre}</span>
                </div>
              )}
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">Атака</span>
                <span className="text-yellow-400 font-medium">{attack}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">Здоровье</span>
                <span className="text-green-400 font-medium">{currentHp}/{hp}</span>
              </div>
              {createdAt && (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-500">Получена</span>
                  <span className="text-gray-300 flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {formatDate(createdAt)}
                  </span>
                </div>
              )}
            </div>

            {/* Tap hint */}
            <p className="text-center text-[10px] text-gray-500 mt-2">
              Нажми чтобы вернуться
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DeckCard;
