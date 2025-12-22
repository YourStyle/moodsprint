'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Gift, Sparkles, X, Flame } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { gamificationService } from '@/services';
import { useAppStore } from '@/lib/store';
import { hapticFeedback } from '@/lib/telegram';

export function DailyBonus() {
  const [isOpen, setIsOpen] = useState(false);
  const [claimed, setClaimed] = useState(false);
  const queryClient = useQueryClient();
  const { showXPAnimation } = useAppStore();

  // Check if this is user's first visit - skip daily bonus on first login
  const isFirstVisit = typeof window !== 'undefined' && !localStorage.getItem('first_visit_completed');

  const { data: bonusStatus, isLoading } = useQuery({
    queryKey: ['daily-bonus-status'],
    queryFn: () => gamificationService.getDailyBonusStatus(),
    enabled: !isFirstVisit, // Don't fetch on first visit
  });

  const claimMutation = useMutation({
    mutationFn: () => gamificationService.claimDailyBonus(),
    onSuccess: (result) => {
      if (result.success && result.data?.claimed) {
        setClaimed(true);
        hapticFeedback('success');
        if (result.data.xp_earned) {
          showXPAnimation(result.data.xp_earned);
        }
        queryClient.invalidateQueries({ queryKey: ['user', 'stats'] });
        queryClient.invalidateQueries({ queryKey: ['daily-bonus-status'] });

        // Auto close after animation
        setTimeout(() => {
          setIsOpen(false);
          setClaimed(false);
        }, 2500);
      }
    },
  });

  // Show modal when bonus is available
  useEffect(() => {
    if (bonusStatus?.data?.can_claim && !isLoading) {
      // Small delay to let page load
      const timer = setTimeout(() => setIsOpen(true), 1000);
      return () => clearTimeout(timer);
    }
  }, [bonusStatus?.data?.can_claim, isLoading]);

  const status = bonusStatus?.data;

  // Skip on first visit or if no bonus available
  if (isFirstVisit || !status?.can_claim || isLoading) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {/* Backdrop */}
          <motion.div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => !claimMutation.isPending && setIsOpen(false)}
          />

          {/* Modal */}
          <motion.div
            className="relative bg-gradient-to-br from-purple-900/90 to-indigo-900/90 rounded-3xl p-6 max-w-sm w-full border border-purple-500/30 shadow-2xl overflow-hidden"
            initial={{ scale: 0.8, y: 50, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.8, y: 50, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          >
            {/* Close button */}
            <button
              onClick={() => setIsOpen(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
              disabled={claimMutation.isPending}
            >
              <X className="w-5 h-5" />
            </button>

            {/* Sparkles background */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
              {[...Array(12)].map((_, i) => (
                <motion.div
                  key={i}
                  className="absolute w-1 h-1 bg-yellow-400 rounded-full"
                  style={{
                    left: `${Math.random() * 100}%`,
                    top: `${Math.random() * 100}%`,
                  }}
                  animate={{
                    scale: [0, 1, 0],
                    opacity: [0, 1, 0],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    delay: Math.random() * 2,
                  }}
                />
              ))}
            </div>

            {/* Content */}
            <div className="relative text-center">
              {!claimed ? (
                <>
                  {/* Gift icon */}
                  <motion.div
                    className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-2xl flex items-center justify-center shadow-lg"
                    animate={{
                      scale: [1, 1.1, 1],
                      rotate: [0, -5, 5, 0],
                    }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      ease: 'easeInOut',
                    }}
                  >
                    <Gift className="w-10 h-10 text-white" />
                  </motion.div>

                  <h2 className="text-2xl font-bold text-white mb-2">
                    Ежедневный бонус!
                  </h2>

                  <p className="text-gray-300 mb-4">
                    Заходи каждый день и получай награды
                  </p>

                  {/* Streak info */}
                  {status.streak_days > 0 && (
                    <div className="flex items-center justify-center gap-2 mb-4 text-orange-400">
                      <Flame className="w-5 h-5" />
                      <span className="font-medium">
                        Серия {status.streak_days} {status.streak_days === 1 ? 'день' : status.streak_days < 5 ? 'дня' : 'дней'}
                      </span>
                    </div>
                  )}

                  {/* XP reward */}
                  <div className="bg-white/10 rounded-2xl p-4 mb-6">
                    <div className="flex items-center justify-center gap-2">
                      <Sparkles className="w-6 h-6 text-yellow-400" />
                      <span className="text-3xl font-bold text-white">
                        +{status.potential_xp} XP
                      </span>
                    </div>
                    {status.streak_multiplier > 0 && (
                      <p className="text-sm text-purple-300 mt-1">
                        Включая бонус за серию +{status.streak_multiplier * 5} XP
                      </p>
                    )}
                  </div>

                  {/* Claim button */}
                  <motion.button
                    onClick={() => claimMutation.mutate()}
                    disabled={claimMutation.isPending}
                    className="w-full py-4 bg-gradient-to-r from-yellow-400 to-orange-500 text-white font-bold rounded-2xl shadow-lg disabled:opacity-50"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    {claimMutation.isPending ? 'Получаем...' : 'Забрать награду'}
                  </motion.button>
                </>
              ) : (
                <>
                  {/* Success state */}
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                  >
                    <motion.div
                      className="w-24 h-24 mx-auto mb-4 bg-gradient-to-br from-green-400 to-emerald-500 rounded-full flex items-center justify-center"
                      animate={{
                        boxShadow: [
                          '0 0 0 0 rgba(52, 211, 153, 0.4)',
                          '0 0 0 20px rgba(52, 211, 153, 0)',
                        ],
                      }}
                      transition={{
                        duration: 1,
                        repeat: Infinity,
                      }}
                    >
                      <Sparkles className="w-12 h-12 text-white" />
                    </motion.div>

                    <h2 className="text-2xl font-bold text-white mb-2">
                      Получено!
                    </h2>

                    <motion.p
                      className="text-4xl font-bold text-yellow-400"
                      initial={{ scale: 0 }}
                      animate={{ scale: [0, 1.2, 1] }}
                      transition={{ delay: 0.2 }}
                    >
                      +{status.potential_xp} XP
                    </motion.p>
                  </motion.div>
                </>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
