'use client';

import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '@/lib/store';

export function XPToastQueue() {
  const { xpToastQueue, shiftXPToast } = useAppStore();
  const current = xpToastQueue[0] || null;
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auto-dismiss after 2.5s, then shift to next
  useEffect(() => {
    if (!current) return;
    timerRef.current = setTimeout(() => {
      shiftXPToast();
    }, 2500);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [current?.id, shiftXPToast]);

  return (
    <div className="fixed top-16 left-0 right-0 z-50 flex justify-center pointer-events-none">
      <AnimatePresence mode="wait">
        {current && (
          <motion.div
            key={current.id}
            initial={{ y: -40, opacity: 0, scale: 0.9 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: -20, opacity: 0, scale: 0.95 }}
            transition={{ type: 'spring', damping: 22, stiffness: 300 }}
            className="px-4 w-full max-w-xs"
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
                  {(() => {
                    const xpNow = current.type === 'companion'
                      ? (current.cardXp ?? 0)
                      : (current.currentXp ?? 0);
                    const xpMax = current.type === 'companion'
                      ? (current.cardXpForNext ?? 100)
                      : (current.xpForNext ?? 100);
                    const prevPct = Math.min(100, (xpNow / xpMax) * 100);
                    const newPct = Math.min(100, ((xpNow + current.amount) / xpMax) * 100);

                    return (
                      <div className="mt-1.5 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                        <motion.div
                          className="h-full rounded-full bg-gradient-to-r from-yellow-400 to-orange-500"
                          initial={{ width: `${prevPct}%` }}
                          animate={{ width: `${newPct}%` }}
                          transition={{ duration: 0.8, delay: 0.3, ease: 'easeOut' }}
                        />
                      </div>
                    );
                  })()}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
