'use client';

import { cn } from '@/lib/utils';
import { Heart, Zap, Skull } from 'lucide-react';

export interface BattleCardProps {
  id: number | string;
  name: string;
  description?: string;
  emoji?: string;
  imageUrl?: string | null;
  hp: number;
  maxHp: number;
  attack: number;
  rarity?: string;
  genre?: string;
  alive?: boolean;
  selected?: boolean;
  selectable?: boolean;
  size?: 'sm' | 'md' | 'lg';
  onClick?: () => void;
}

const rarityStyles = {
  common: {
    border: 'border-gray-500/50',
    glow: '',
    bg: 'from-gray-700 to-gray-800',
    label: 'Обычная',
    labelBg: 'bg-gray-500',
  },
  uncommon: {
    border: 'border-green-500/50',
    glow: 'shadow-[0_0_15px_rgba(34,197,94,0.3)]',
    bg: 'from-green-900/50 to-gray-800',
    label: 'Необычная',
    labelBg: 'bg-green-600',
  },
  rare: {
    border: 'border-blue-500/50',
    glow: 'shadow-[0_0_15px_rgba(59,130,246,0.4)]',
    bg: 'from-blue-900/50 to-gray-800',
    label: 'Редкая',
    labelBg: 'bg-blue-600',
  },
  epic: {
    border: 'border-purple-500/50',
    glow: 'shadow-[0_0_20px_rgba(168,85,247,0.4)]',
    bg: 'from-purple-900/50 to-gray-800',
    label: 'Эпическая',
    labelBg: 'bg-purple-600',
  },
  legendary: {
    border: 'border-amber-500/50',
    glow: 'shadow-[0_0_25px_rgba(245,158,11,0.5)]',
    bg: 'from-amber-900/50 to-gray-800',
    label: 'Легендарная',
    labelBg: 'bg-amber-600',
  },
};

export function BattleCard({
  name,
  description,
  emoji,
  imageUrl,
  hp,
  maxHp,
  attack,
  rarity = 'common',
  alive = true,
  selected = false,
  selectable = true,
  size = 'md',
  onClick,
}: BattleCardProps) {
  const styles = rarityStyles[rarity as keyof typeof rarityStyles] || rarityStyles.common;
  const hpPercent = Math.max(0, Math.min(100, (hp / maxHp) * 100));

  const sizeClasses = {
    sm: 'w-24 h-36',
    md: 'w-32 h-48',
    lg: 'w-40 h-56',
  };

  const imageSizeClasses = {
    sm: 'h-16',
    md: 'h-24',
    lg: 'h-32',
  };

  const textSizeClasses = {
    sm: 'text-[10px]',
    md: 'text-xs',
    lg: 'text-sm',
  };

  const nameSizeClasses = {
    sm: 'text-[9px]',
    md: 'text-[11px]',
    lg: 'text-sm',
  };

  return (
    <div
      onClick={selectable && alive ? onClick : undefined}
      className={cn(
        'relative rounded-xl overflow-hidden transition-all duration-200',
        'border-2',
        sizeClasses[size],
        styles.border,
        alive && styles.glow,
        selectable && alive && 'cursor-pointer hover:scale-105 active:scale-95',
        selected && 'ring-2 ring-purple-500 ring-offset-2 ring-offset-gray-900',
        !alive && 'grayscale brightness-50',
        !selectable && 'cursor-default'
      )}
    >
      {/* Background gradient */}
      <div className={cn('absolute inset-0 bg-gradient-to-b', styles.bg)} />

      {/* Card image area */}
      <div className={cn('relative', imageSizeClasses[size], 'overflow-hidden')}>
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-b from-gray-600/50 to-transparent">
            <span className={cn(
              size === 'sm' ? 'text-3xl' : size === 'md' ? 'text-4xl' : 'text-5xl'
            )}>
              {emoji || '🎴'}
            </span>
          </div>
        )}

        {/* Rarity label */}
        {size !== 'sm' && (
          <div className={cn(
            'absolute top-1 left-1 px-1.5 py-0.5 rounded text-[8px] font-bold text-white uppercase',
            styles.labelBg
          )}>
            {styles.label}
          </div>
        )}

        {/* Attack badge - top right */}
        <div className={cn(
          'absolute top-1 right-1 flex items-center gap-0.5 px-1.5 py-0.5 rounded',
          'bg-red-600/90 backdrop-blur-sm',
          textSizeClasses[size]
        )}>
          <Zap className={cn(size === 'sm' ? 'w-2.5 h-2.5' : 'w-3 h-3', 'text-yellow-300')} />
          <span className="font-bold text-white">{attack}</span>
        </div>
      </div>

      {/* Card info */}
      <div className="relative p-1.5 flex flex-col flex-1">
        {/* Name */}
        <h3 className={cn(
          'font-bold text-white text-center truncate leading-tight',
          nameSizeClasses[size]
        )}>
          {name}
        </h3>

        {/* Description - only on lg */}
        {size === 'lg' && description && (
          <p className="text-[9px] text-gray-400 text-center line-clamp-2 mt-0.5">
            {description}
          </p>
        )}

        {/* HP bar */}
        <div className="mt-auto">
          <div className="flex items-center justify-between mb-0.5">
            <div className={cn('flex items-center gap-0.5', textSizeClasses[size])}>
              <Heart className={cn(size === 'sm' ? 'w-2.5 h-2.5' : 'w-3 h-3', 'text-red-400')} />
              <span className="text-white font-medium">{hp}</span>
              <span className="text-gray-500">/{maxHp}</span>
            </div>
          </div>

          {/* HP progress bar */}
          <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
            <div
              className={cn(
                'h-full rounded-full transition-all duration-300',
                hpPercent > 50 ? 'bg-green-500' : hpPercent > 25 ? 'bg-yellow-500' : 'bg-red-500'
              )}
              style={{ width: `${hpPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Dead overlay */}
      {!alive && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/60">
          <div className="relative">
            <Skull className="w-12 h-12 text-red-500 drop-shadow-[0_0_10px_rgba(239,68,68,0.8)]" />
          </div>
        </div>
      )}

      {/* Selection indicator */}
      {selected && alive && (
        <div className="absolute inset-0 border-2 border-purple-400 rounded-xl pointer-events-none animate-pulse" />
      )}
    </div>
  );
}

export default BattleCard;
