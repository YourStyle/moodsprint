'use client';

import { useAppStore } from '@/lib/store';

export function XPPopup() {
  const { xpAnimation } = useAppStore();

  if (!xpAnimation.show) return null;

  return (
    <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 animate-bounce">
      <div className="bg-yellow-400 text-yellow-900 font-bold px-4 py-2 rounded-full shadow-lg">
        +{xpAnimation.amount} XP
      </div>
    </div>
  );
}
