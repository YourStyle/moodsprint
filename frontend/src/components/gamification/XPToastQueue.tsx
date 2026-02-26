'use client';

import { useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '@/lib/store';
import { useModalContext } from '@/lib/contexts/ModalContext';

const DISMISS_MS = 2500;

export function XPToastQueue() {
  const { xpToastQueue, shiftXPToast } = useAppStore();
  const { isAnyModalOpen } = useModalContext();
  const current = xpToastQueue[0] ?? null;
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auto-dismiss only when no modals are open
  useEffect(() => {
    if (!current || isAnyModalOpen) return;
    timerRef.current = setTimeout(shiftXPToast, DISMISS_MS);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [current?.id, isAnyModalOpen, shiftXPToast]);

  // Pre-compute progress bar values to avoid inline IIFE in render
  const progress = useMemo(() => {
    if (!current) return null;

    if (current.type === 'companion') {
      // Companion: card_xp is relative to current level (resets on level up)
      const xpAfter = current.cardXp ?? 0;
      const xpMax = current.cardXpForNext ?? 100;
      if (xpMax <= 0) return { from: 100, to: 100 };
      return {
        from: Math.min(100, Math.max(0, ((xpAfter - current.amount) / xpMax) * 100)),
        to: Math.min(100, (xpAfter / xpMax) * 100),
      };
    }

    // Player: xp is total, need to compute progress within current level
    const level = current.level ?? 1;
    const xpForCurrent = ((level - 1) ** 2) * 100; // XP threshold for current level
    const xpForNext = current.xpForNext ?? (level ** 2) * 100;
    const range = xpForNext - xpForCurrent;
    if (range <= 0) return { from: 100, to: 100 };

    const totalXp = current.currentXp ?? 0;
    return {
      from: Math.min(100, Math.max(0, ((totalXp - xpForCurrent) / range) * 100)),
      to: Math.min(100, ((totalXp + current.amount - xpForCurrent) / range) * 100),
    };
  }, [current?.id]);

  // Don't render while a modal is open — the toast will appear once it closes
  if (!current || isAnyModalOpen) return null;

  return (
    <div
      className="fixed left-0 right-0 z-50 pointer-events-none"
      style={{ top: 'calc(var(--safe-area-top, 0px) + 16px)' }}
    >
      <AnimatePresence mode="wait">
        <motion.div
          key={current.id}
          initial={{ y: -60, scale: 0.95 }}
          animate={{ y: 0, scale: 1 }}
          exit={{ y: -60, scale: 0.95 }}
          transition={{ type: 'spring', damping: 24, stiffness: 300 }}
          className="px-4 w-full"
        >
          <div className="bg-gray-800/95 backdrop-blur-md border border-gray-600/50 rounded-2xl px-4 py-3 shadow-2xl">
            <div className="flex items-center gap-3">
              {/* Icon */}
              <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-gradient-to-br from-yellow-400/20 to-orange-500/20 flex items-center justify-center">
                <span className="text-lg">
                  {current.type === 'companion' && current.cardEmoji
                    ? current.cardEmoji
                    : '⭐'}
                </span>
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-yellow-400">
                    +{current.amount} XP
                  </span>
                  {current.type === 'companion' && current.cardName && (
                    <span className="text-[10px] text-gray-400 truncate">
                      {current.cardName}
                    </span>
                  )}
                  {current.levelUp && (
                    <span className="text-[10px] bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded-full font-medium">
                      Level Up!
                    </span>
                  )}
                </div>

                {/* Mini progress bar */}
                {progress && (
                  <div className="mt-1.5 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full rounded-full bg-gradient-to-r from-yellow-400 to-orange-500"
                      initial={{ width: `${progress.from}%` }}
                      animate={{ width: `${progress.to}%` }}
                      transition={{ duration: 0.6, delay: 0.2, ease: 'easeOut' }}
                    />
                  </div>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
