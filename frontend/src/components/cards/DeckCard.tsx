'use client';

import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Heart, Swords, Info, Layers, Calendar, Sparkles, Clock, Zap } from 'lucide-react';

interface SimpleAbilityInfo {
  type: string;
  name: string;
  description: string;
  emoji: string;
  cooldown: number;
  current_cooldown: number;
}

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
  onInfoClick?: () => void; // External handler - if provided, shows info in sheet instead of flip
  compact?: boolean;
  ability?: string | null;
  abilityInfo?: SimpleAbilityInfo | null;
  // Cooldown system
  isOnCooldown?: boolean;
  cooldownRemaining?: number | null; // seconds remaining
  onSkipCooldown?: () => void;
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

// Format cooldown time
function formatCooldownTime(seconds: number): string {
  if (seconds <= 0) return '0:00';
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  if (hours > 0) {
    return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

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
  onInfoClick,
  compact = false,
  ability,
  abilityInfo,
  isOnCooldown = false,
  cooldownRemaining = null,
  onSkipCooldown,
}: DeckCardProps) {
  const [isFlipped, setIsFlipped] = useState(false);
  const [displayCooldown, setDisplayCooldown] = useState(cooldownRemaining || 0);
  const config = rarityConfig[rarity as keyof typeof rarityConfig] || rarityConfig.common;

  // Update cooldown timer every second
  useEffect(() => {
    if (!isOnCooldown || !cooldownRemaining) {
      setDisplayCooldown(0);
      return;
    }

    setDisplayCooldown(cooldownRemaining);

    const interval = setInterval(() => {
      setDisplayCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);

    return () => clearInterval(interval);
  }, [isOnCooldown, cooldownRemaining]);

  const handleInfoClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!compact) {
      if (onInfoClick) {
        onInfoClick();
      } else {
        setIsFlipped(!isFlipped);
      }
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
      {/* Rarity badge - centered, outside of flip container so it doesn't rotate */}
      {!compact && (
        <div
          className={cn(
            'absolute top-1 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded-md text-[10px] font-bold text-white z-20',
            config.labelBg
          )}
        >
          {config.label}
        </div>
      )}

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
            {/* Info button - more visible */}
            {!compact && (
              <button
                onClick={handleInfoClick}
                className={cn(
                  'absolute top-1.5 right-1.5 z-10',
                  'w-7 h-7 rounded-full',
                  'bg-white/90 backdrop-blur-sm border-2 border-gray-200',
                  'flex items-center justify-center',
                  'hover:bg-white transition-colors shadow-lg',
                  'active:scale-95'
                )}
              >
                <Info className="w-4 h-4 text-gray-700" />
              </button>
            )}

            {/* In deck indicator */}
            {isInDeck && !compact && (
              <div className="absolute top-1.5 left-1.5 z-10 w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center">
                <Layers className="w-3 h-3 text-white" />
              </div>
            )}

            {/* Ability indicator */}
            {ability && abilityInfo && !compact && (
              <div
                className="absolute top-8 left-1.5 z-10 px-1.5 py-0.5 bg-gradient-to-r from-purple-600 to-pink-600 rounded-full flex items-center gap-1 shadow-lg"
                title={`${abilityInfo.name}: ${abilityInfo.description}`}
              >
                <Sparkles className="w-3 h-3 text-white" />
                <span className="text-[10px] font-medium text-white">{abilityInfo.emoji}</span>
              </div>
            )}

            {/* Image - takes most of the space */}
            <div className={cn(
              'flex-1 rounded-lg overflow-hidden border border-white/10 relative',
              compact ? 'mt-1 mb-1' : 'mt-4 mb-2',
              isOnCooldown && 'grayscale'
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

              {/* Cooldown overlay */}
              {isOnCooldown && displayCooldown > 0 && (
                <div className="absolute inset-0 bg-black/60 flex flex-col items-center justify-center">
                  <Clock className="w-8 h-8 text-blue-400 animate-pulse mb-2" />
                  <span className="text-lg font-bold text-white font-mono">
                    {formatCooldownTime(displayCooldown)}
                  </span>
                  <span className="text-xs text-gray-400 mt-1">Восстановление</span>
                  {onSkipCooldown && !compact && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSkipCooldown();
                      }}
                      className="mt-3 px-3 py-1.5 bg-gradient-to-r from-amber-500 to-orange-500 rounded-lg text-xs font-bold text-white flex items-center gap-1.5 hover:opacity-90 transition-opacity shadow-lg"
                    >
                      <Zap className="w-3.5 h-3.5" />
                      Пропустить
                    </button>
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

          <div className="relative h-full flex flex-col p-3 pb-4">
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
              {abilityInfo && (
                <div className="mt-1 pt-1 border-t border-white/10">
                  <div className="flex items-center gap-1 text-xs text-purple-400 font-medium mb-1">
                    <Sparkles className="w-3 h-3" />
                    {abilityInfo.emoji} {abilityInfo.name}
                  </div>
                  <p className="text-[10px] text-gray-400 leading-relaxed">
                    {abilityInfo.description}
                  </p>
                  {abilityInfo.cooldown > 0 && (
                    <p className="text-[10px] text-gray-500 mt-0.5">
                      Перезарядка: {abilityInfo.cooldown} ход(а)
                    </p>
                  )}
                </div>
              )}
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
