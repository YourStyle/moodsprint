'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

export interface DamageNumberProps {
  damage: number;
  isCritical?: boolean;
  onComplete?: () => void;
}

export function DamageNumber({ damage, isCritical = false, onComplete }: DamageNumberProps) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
      onComplete?.();
    }, 1000);

    return () => clearTimeout(timer);
  }, [onComplete]);

  if (!visible) return null;

  return (
    <div
      className={cn(
        'absolute left-1/2 -translate-x-1/2 -top-2 z-50',
        'animate-damage-float pointer-events-none',
        'font-bold text-xl',
        isCritical
          ? 'text-yellow-400 drop-shadow-[0_0_10px_rgba(250,204,21,0.8)] text-2xl'
          : 'text-red-500 drop-shadow-[0_0_6px_rgba(239,68,68,0.6)]'
      )}
    >
      -{damage}
      {isCritical && <span className="ml-1">💥</span>}
    </div>
  );
}

export default DamageNumber;
