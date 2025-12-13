'use client';

import { cn } from '@/lib/utils';
import { Heart, Zap, Skull, Shield, Sparkles } from 'lucide-react';
import { DamageNumber } from './DamageNumber';
import type { AbilityInfo, StatusEffect } from '@/domain/types';

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
  isAttacking?: boolean;
  isBeingAttacked?: boolean;
  damageReceived?: number | null;
  isCriticalHit?: boolean;
  onClick?: () => void;
  // New ability props
  ability?: string | null;
  abilityInfo?: AbilityInfo | null;
  abilityCooldown?: number;
  hasShield?: boolean;
  statusEffects?: StatusEffect[];
  onAbilityClick?: () => void;
  canUseAbility?: boolean;
}

const rarityConfig = {
  common: {
    frame: 'from-slate-600 to-slate-700',
    border: 'border-slate-500/60',
    glow: '',
    gem: 'bg-slate-400',
    gemGlow: '',
    label: 'Обычная',
    accent: 'text-slate-300',
  },
  uncommon: {
    frame: 'from-emerald-700 to-emerald-900',
    border: 'border-emerald-500/60',
    glow: 'shadow-[0_0_20px_rgba(16,185,129,0.3)]',
    gem: 'bg-gradient-to-br from-emerald-300 to-emerald-500',
    gemGlow: 'shadow-[0_0_8px_rgba(16,185,129,0.6)]',
    label: 'Необычная',
    accent: 'text-emerald-400',
  },
  rare: {
    frame: 'from-blue-700 to-blue-900',
    border: 'border-blue-500/60',
    glow: 'shadow-[0_0_25px_rgba(59,130,246,0.4)]',
    gem: 'bg-gradient-to-br from-blue-300 to-blue-500',
    gemGlow: 'shadow-[0_0_10px_rgba(59,130,246,0.7)]',
    label: 'Редкая',
    accent: 'text-blue-400',
  },
  epic: {
    frame: 'from-purple-700 to-purple-900',
    border: 'border-purple-500/60',
    glow: 'shadow-[0_0_30px_rgba(168,85,247,0.5)]',
    gem: 'bg-gradient-to-br from-purple-300 to-purple-500',
    gemGlow: 'shadow-[0_0_12px_rgba(168,85,247,0.8)]',
    label: 'Эпическая',
    accent: 'text-purple-400',
  },
  legendary: {
    frame: 'from-amber-600 to-orange-800',
    border: 'border-amber-500/60',
    glow: 'shadow-[0_0_35px_rgba(245,158,11,0.5)]',
    gem: 'bg-gradient-to-br from-amber-200 to-amber-500',
    gemGlow: 'shadow-[0_0_15px_rgba(245,158,11,0.9)]',
    label: 'Легендарная',
    accent: 'text-amber-400',
  },
};

export function BattleCard({
  name,
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
  isAttacking = false,
  isBeingAttacked = false,
  damageReceived = null,
  isCriticalHit = false,
  onClick,
  ability,
  abilityInfo,
  abilityCooldown = 0,
  hasShield = false,
  statusEffects = [],
  onAbilityClick,
  canUseAbility = false,
}: BattleCardProps) {
  const hasPoisonEffect = statusEffects.some(e => e.type === 'poison');
  const config = rarityConfig[rarity as keyof typeof rarityConfig] || rarityConfig.common;
  const hpPercent = Math.max(0, Math.min(100, (hp / maxHp) * 100));

  const sizeClasses = {
    sm: 'w-[88px] h-[130px]',
    md: 'w-[110px] h-[160px]',
    lg: 'w-[140px] h-[200px]',
  };

  const imageSizeClasses = {
    sm: 'h-[60px]',
    md: 'h-[80px]',
    lg: 'h-[105px]',
  };

  return (
    <div
      onClick={selectable && alive ? onClick : undefined}
      className={cn(
        'relative transition-all duration-300 ease-out',
        sizeClasses[size],
        selectable && alive && 'cursor-pointer',
        selectable && alive && 'hover:scale-105 hover:-translate-y-1',
        selected && 'scale-105 -translate-y-2',
        !alive && 'grayscale brightness-50',
        !selectable && 'cursor-default',
        // Attack animation
        isAttacking && 'animate-card-attack',
        isBeingAttacked && 'animate-card-hit'
      )}
    >
      {/* Card frame */}
      <div
        className={cn(
          'absolute inset-0 rounded-xl overflow-hidden',
          'border-2',
          config.border,
          alive && config.glow,
          selected && 'ring-2 ring-white/80 ring-offset-1 ring-offset-gray-900'
        )}
      >
        {/* Outer frame gradient */}
        <div className={cn('absolute inset-0 bg-gradient-to-b', config.frame)} />

        {/* Inner card area */}
        <div className="absolute inset-[3px] rounded-lg overflow-hidden bg-gray-900/90">
          {/* Top decorative bar */}
          <div className={cn(
            'absolute top-0 left-0 right-0 h-[2px]',
            'bg-gradient-to-r from-transparent via-white/30 to-transparent'
          )} />

          {/* Gem indicator - top center */}
          <div className="absolute top-1 left-1/2 -translate-x-1/2 z-10">
            <div
              className={cn(
                'w-3 h-3 rounded-full',
                config.gem,
                config.gemGlow,
                'border border-white/20'
              )}
            />
          </div>

          {/* Attack stat - top left */}
          <div className={cn(
            'absolute top-1 left-1 z-10',
            'flex items-center gap-0.5 px-1 py-0.5 rounded',
            'bg-red-900/80 backdrop-blur-sm border border-red-500/30'
          )}>
            <Zap className={cn(
              size === 'sm' ? 'w-2 h-2' : 'w-2.5 h-2.5',
              'text-yellow-400'
            )} />
            <span className={cn(
              'font-bold text-white',
              size === 'sm' ? 'text-[8px]' : 'text-[10px]'
            )}>
              {attack}
            </span>
          </div>

          {/* HP stat - top right */}
          <div className={cn(
            'absolute top-1 right-1 z-10',
            'flex items-center gap-0.5 px-1 py-0.5 rounded',
            'bg-emerald-900/80 backdrop-blur-sm border border-emerald-500/30'
          )}>
            <Heart className={cn(
              size === 'sm' ? 'w-2 h-2' : 'w-2.5 h-2.5',
              'text-red-400 fill-red-400'
            )} />
            <span className={cn(
              'font-bold text-white',
              size === 'sm' ? 'text-[8px]' : 'text-[10px]'
            )}>
              {hp}
            </span>
          </div>

          {/* Character image */}
          <div className={cn(
            'absolute left-[4px] right-[4px] top-[18px]',
            imageSizeClasses[size],
            'rounded-md overflow-hidden',
            'border border-white/10'
          )}>
            {imageUrl ? (
              <img
                src={imageUrl}
                alt={name}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className={cn(
                'w-full h-full flex items-center justify-center',
                'bg-gradient-to-b from-gray-700/80 to-gray-800/80'
              )}>
                <span className={cn(
                  size === 'sm' ? 'text-2xl' : size === 'md' ? 'text-3xl' : 'text-4xl'
                )}>
                  {emoji || '🎴'}
                </span>
              </div>
            )}

            {/* Image overlay gradient */}
            <div className="absolute inset-0 bg-gradient-to-t from-gray-900/60 via-transparent to-transparent" />
          </div>

          {/* Name plate */}
          <div className={cn(
            'absolute left-[4px] right-[4px]',
            size === 'sm' ? 'bottom-[22px]' : size === 'md' ? 'bottom-[26px]' : 'bottom-[32px]',
            'py-0.5 px-1',
            'bg-gradient-to-r from-gray-800/90 via-gray-700/90 to-gray-800/90',
            'border-y border-white/10'
          )}>
            <h3 className={cn(
              'font-bold text-center truncate',
              config.accent,
              size === 'sm' ? 'text-[7px]' : size === 'md' ? 'text-[9px]' : 'text-[11px]'
            )}>
              {name}
            </h3>
          </div>

          {/* HP bar */}
          <div className={cn(
            'absolute left-[4px] right-[4px] bottom-[8px]',
            'space-y-0.5'
          )}>
            <div className={cn(
              'h-[6px] rounded-full overflow-hidden',
              'bg-gray-800 border border-white/10'
            )}>
              <div
                className={cn(
                  'h-full rounded-full transition-all duration-500',
                  hpPercent > 50
                    ? 'bg-gradient-to-r from-green-600 to-green-400'
                    : hpPercent > 25
                    ? 'bg-gradient-to-r from-yellow-600 to-yellow-400'
                    : 'bg-gradient-to-r from-red-600 to-red-400'
                )}
                style={{ width: `${hpPercent}%` }}
              />
            </div>
          </div>

          {/* Bottom decorative bar */}
          <div className={cn(
            'absolute bottom-0 left-0 right-0 h-[2px]',
            'bg-gradient-to-r from-transparent via-white/20 to-transparent'
          )} />
        </div>
      </div>

      {/* Selection glow effect */}
      {selected && alive && (
        <div className={cn(
          'absolute -inset-1 rounded-xl',
          'bg-gradient-to-r from-purple-500/20 via-blue-500/20 to-purple-500/20',
          'animate-pulse pointer-events-none'
        )} />
      )}

      {/* Dead overlay */}
      {!alive && (
        <div className="absolute inset-0 rounded-xl flex items-center justify-center bg-black/70">
          <Skull className={cn(
            size === 'sm' ? 'w-8 h-8' : 'w-10 h-10',
            'text-red-500 drop-shadow-[0_0_10px_rgba(239,68,68,0.8)]'
          )} />
        </div>
      )}

      {/* Attack effect overlay */}
      {isAttacking && (
        <div className={cn(
          'absolute inset-0 rounded-xl pointer-events-none',
          'bg-gradient-to-r from-orange-500/30 to-red-500/30',
          'animate-pulse'
        )} />
      )}

      {/* Hit effect overlay */}
      {isBeingAttacked && (
        <div className={cn(
          'absolute inset-0 rounded-xl pointer-events-none',
          'bg-red-500/40 animate-ping'
        )} />
      )}

      {/* Floating damage number */}
      {damageReceived !== null && damageReceived > 0 && (
        <DamageNumber damage={damageReceived} isCritical={isCriticalHit} />
      )}

      {/* Shield indicator */}
      {hasShield && alive && (
        <div className={cn(
          'absolute -top-1 -right-1 z-20',
          'w-6 h-6 rounded-full',
          'bg-gradient-to-br from-blue-400 to-blue-600',
          'border-2 border-blue-300',
          'flex items-center justify-center',
          'shadow-[0_0_10px_rgba(59,130,246,0.8)]',
          'animate-pulse'
        )}>
          <Shield className="w-3 h-3 text-white" />
        </div>
      )}

      {/* Poison indicator */}
      {hasPoisonEffect && alive && (
        <div className={cn(
          'absolute -top-1 -left-1 z-20',
          'w-6 h-6 rounded-full',
          'bg-gradient-to-br from-green-500 to-green-700',
          'border-2 border-green-400',
          'flex items-center justify-center',
          'shadow-[0_0_10px_rgba(34,197,94,0.8)]'
        )}>
          <span className="text-xs">☠️</span>
        </div>
      )}

      {/* Ability button */}
      {ability && abilityInfo && alive && onAbilityClick && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (canUseAbility && abilityCooldown === 0) {
              onAbilityClick();
            }
          }}
          disabled={!canUseAbility || abilityCooldown > 0}
          className={cn(
            'absolute -bottom-3 left-1/2 -translate-x-1/2 z-20',
            'px-2 py-1 rounded-full',
            'text-[10px] font-bold',
            'border transition-all duration-200',
            canUseAbility && abilityCooldown === 0
              ? 'bg-gradient-to-r from-purple-600 to-pink-600 border-purple-400 text-white hover:scale-110 cursor-pointer shadow-[0_0_12px_rgba(168,85,247,0.6)]'
              : 'bg-gray-700/80 border-gray-600 text-gray-400 cursor-not-allowed'
          )}
          title={`${abilityInfo.name}: ${abilityInfo.description}`}
        >
          <span className="flex items-center gap-1">
            <Sparkles className="w-3 h-3" />
            {abilityCooldown > 0 ? (
              <span>{abilityCooldown}</span>
            ) : (
              <span>{abilityInfo.emoji}</span>
            )}
          </span>
        </button>
      )}
    </div>
  );
}

export default BattleCard;
