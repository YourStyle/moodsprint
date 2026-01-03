'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

export interface BattleEventData {
  id: string;
  type: 'buff' | 'debuff' | 'heal' | 'revive' | 'damage';
  target: 'player' | 'monster';
  title: string;
  description: string;
  emoji: string;
}

export interface BattleEventProps {
  event: BattleEventData;
  onComplete: () => void;
}

export function BattleEvent({ event, onComplete }: BattleEventProps) {
  const [phase, setPhase] = useState<'enter' | 'show' | 'exit'>('enter');

  useEffect(() => {
    // Enter animation
    const enterTimer = setTimeout(() => setPhase('show'), 100);

    // Show for 2 seconds then exit
    const showTimer = setTimeout(() => setPhase('exit'), 2000);

    // Complete after exit animation
    const exitTimer = setTimeout(() => onComplete(), 2500);

    return () => {
      clearTimeout(enterTimer);
      clearTimeout(showTimer);
      clearTimeout(exitTimer);
    };
  }, [onComplete]);

  const colorConfig = {
    buff: {
      bg: 'from-blue-900/95 to-purple-900/95',
      border: 'border-blue-500/60',
      text: 'text-blue-300',
      glow: 'shadow-[0_0_30px_rgba(59,130,246,0.5)]',
    },
    debuff: {
      bg: 'from-red-900/95 to-orange-900/95',
      border: 'border-red-500/60',
      text: 'text-red-300',
      glow: 'shadow-[0_0_30px_rgba(239,68,68,0.5)]',
    },
    heal: {
      bg: 'from-green-900/95 to-emerald-900/95',
      border: 'border-green-500/60',
      text: 'text-green-300',
      glow: 'shadow-[0_0_30px_rgba(34,197,94,0.5)]',
    },
    revive: {
      bg: 'from-amber-900/95 to-yellow-900/95',
      border: 'border-amber-500/60',
      text: 'text-amber-300',
      glow: 'shadow-[0_0_30px_rgba(245,158,11,0.5)]',
    },
    damage: {
      bg: 'from-gray-900/95 to-slate-900/95',
      border: 'border-gray-500/60',
      text: 'text-gray-300',
      glow: 'shadow-[0_0_20px_rgba(100,116,139,0.4)]',
    },
  };

  const config = colorConfig[event.type];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
      {/* Backdrop */}
      <div
        className={cn(
          'absolute inset-0 bg-black/70 transition-opacity duration-300',
          phase === 'enter' ? 'opacity-0' : phase === 'exit' ? 'opacity-0' : 'opacity-100'
        )}
      />

      {/* Event Banner */}
      <div
        className={cn(
          'relative w-[90%] max-w-md p-6 rounded-xl',
          'bg-gradient-to-r',
          config.bg,
          'border-2',
          config.border,
          config.glow,
          'backdrop-blur-md',
          'transition-all duration-300 ease-out',
          phase === 'enter' ? 'opacity-0 scale-75 translate-y-8' :
          phase === 'exit' ? 'opacity-0 scale-90 translate-y-4' :
          'opacity-100 scale-100 translate-y-0'
        )}
      >
        {/* Decorative line */}
        <div className="absolute top-0 left-4 right-4 h-px bg-gradient-to-r from-transparent via-white/30 to-transparent" />

        {/* Content */}
        <div className="text-center">
          <div className="text-5xl mb-3 animate-bounce">{event.emoji}</div>
          <h3 className={cn('text-xl font-bold mb-2', config.text)}>
            {event.title}
          </h3>
          <p className="text-gray-300 text-sm">
            {event.description}
          </p>
          <div className="mt-3 text-xs text-gray-500">
            {event.target === 'player' ? 'Игрок' : 'Монстр'}
          </div>
        </div>

        {/* Decorative line */}
        <div className="absolute bottom-0 left-4 right-4 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
      </div>
    </div>
  );
}

export default BattleEvent;
