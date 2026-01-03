'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

export interface HealNumberProps {
  heal: number;
  onComplete?: () => void;
}

export function HealNumber({ heal, onComplete }: HealNumberProps) {
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
        'text-green-400 drop-shadow-[0_0_10px_rgba(34,197,94,0.8)]'
      )}
    >
      +{heal} 💚
    </div>
  );
}

export default HealNumber;
