'use client';

import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export interface CompanionXPData {
  xp_earned: number;
  card_name: string | null;
  card_emoji: string | null;
  level_up: boolean;
  new_level: number | null;
}

interface CompanionXPToastProps {
  data: CompanionXPData | null;
  onDismiss: () => void;
}

export function CompanionXPToast({ data, onDismiss }: CompanionXPToastProps) {
  useEffect(() => {
    if (!data) return;
    const timer = setTimeout(onDismiss, 3000);
    return () => clearTimeout(timer);
  }, [data, onDismiss]);

  return (
    <AnimatePresence>
      {data && (
        <motion.div
          initial={{ y: 60, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 20, opacity: 0 }}
          transition={{ type: 'spring', damping: 20, stiffness: 300 }}
          className="fixed bottom-20 left-4 right-4 z-40 flex justify-center pointer-events-none"
        >
          <div className="bg-gray-800/95 backdrop-blur border border-primary-500/30 rounded-xl px-4 py-2.5 flex items-center gap-2 shadow-lg">
            <span className="text-xl">{data.card_emoji || '⭐'}</span>
            <span className="text-sm text-primary-300 font-medium">
              +{data.xp_earned} XP
            </span>
            {data.level_up && (
              <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded-full font-medium">
                Level Up!
              </span>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
