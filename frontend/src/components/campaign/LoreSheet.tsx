'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Star, X } from 'lucide-react';
import { Button } from '@/components/ui';
import { cn } from '@/lib/utils';
import { hapticFeedback } from '@/lib/telegram';

interface Reward {
  type: string;
  value: string | number;
  emoji: string;
  label?: string;
}

interface LoreSheetProps {
  isOpen: boolean;
  onClose: () => void;
  type: 'monster_defeated' | 'chapter_complete' | 'level_complete';
  title: string;
  subtitle?: string;
  imageUrl?: string;
  emoji?: string;
  text: string;
  rewards?: Reward[];
  starsEarned?: number;
}

// Typewriter effect hook
function useTypewriter(text: string, isOpen: boolean, delay: number = 30) {
  const [displayedText, setDisplayedText] = useState('');
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      setDisplayedText('');
      setIsComplete(false);
      return;
    }

    let index = 0;
    setDisplayedText('');
    setIsComplete(false);

    const timer = setInterval(() => {
      if (index < text.length) {
        setDisplayedText(text.slice(0, index + 1));
        index++;
      } else {
        setIsComplete(true);
        clearInterval(timer);
      }
    }, delay);

    return () => clearInterval(timer);
  }, [text, isOpen, delay]);

  const skipToEnd = useCallback(() => {
    setDisplayedText(text);
    setIsComplete(true);
  }, [text]);

  return { displayedText, isComplete, skipToEnd };
}

export function LoreSheet({
  isOpen,
  onClose,
  type,
  title,
  subtitle,
  imageUrl,
  emoji,
  text,
  rewards = [],
  starsEarned = 0,
}: LoreSheetProps) {
  const { displayedText, isComplete, skipToEnd } = useTypewriter(text, isOpen);
  const [showRewards, setShowRewards] = useState(false);

  // Show rewards after text animation completes
  useEffect(() => {
    if (isComplete && rewards.length > 0) {
      const timer = setTimeout(() => {
        setShowRewards(true);
        hapticFeedback('success');
      }, 300);
      return () => clearTimeout(timer);
    }
    setShowRewards(false);
  }, [isComplete, rewards.length]);

  // Get theme colors based on type
  const getTheme = () => {
    switch (type) {
      case 'chapter_complete':
        return {
          gradient: 'from-purple-900/95 via-indigo-900/95 to-black/95',
          accent: 'text-purple-400',
          glow: 'shadow-purple-500/50',
          particle: 'bg-purple-400',
          button: 'from-purple-600 to-indigo-600',
        };
      case 'monster_defeated':
        return {
          gradient: 'from-amber-900/95 via-orange-900/95 to-black/95',
          accent: 'text-amber-400',
          glow: 'shadow-amber-500/50',
          particle: 'bg-amber-400',
          button: 'from-amber-600 to-orange-600',
        };
      default:
        return {
          gradient: 'from-blue-900/95 via-cyan-900/95 to-black/95',
          accent: 'text-blue-400',
          glow: 'shadow-blue-500/50',
          particle: 'bg-blue-400',
          button: 'from-blue-600 to-cyan-600',
        };
    }
  };

  const theme = getTheme();

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      if (!isComplete) {
        skipToEnd();
      }
    }
  };

  const handleContentClick = () => {
    if (!isComplete) {
      skipToEnd();
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-[100] flex items-end justify-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={handleBackdropClick}
        >
          {/* Backdrop with blur */}
          <motion.div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />

          {/* Main content sheet */}
          <motion.div
            className={cn(
              'relative w-full max-w-lg mx-4 mb-4 rounded-t-3xl rounded-b-2xl overflow-hidden',
              `bg-gradient-to-b ${theme.gradient}`,
              'border border-white/10'
            )}
            initial={{ y: '100%', scale: 0.95 }}
            animate={{
              y: 0,
              scale: 1,
              transition: { type: 'spring', damping: 25, stiffness: 200 },
            }}
            exit={{
              y: '100%',
              scale: 0.95,
              transition: { duration: 0.3 },
            }}
            onClick={handleContentClick}
          >
            {/* Close button */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onClose();
              }}
              className="absolute top-4 right-4 z-10 p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
            >
              <X className="w-5 h-5 text-white/70" />
            </button>

            {/* Content container */}
            <div className="p-6 pb-8 space-y-6">
              {/* Image or emoji */}
              <motion.div
                className="relative mx-auto"
                initial={{ scale: 0, opacity: 0 }}
                animate={{
                  scale: 1,
                  opacity: 1,
                  transition: { delay: 0.2, type: 'spring', stiffness: 200 },
                }}
              >
                {imageUrl ? (
                  <div className={cn(
                    'w-32 h-32 mx-auto rounded-2xl overflow-hidden',
                    'ring-4 ring-white/20',
                    `shadow-lg ${theme.glow}`
                  )}>
                    <img
                      src={imageUrl}
                      alt={title}
                      className="w-full h-full object-cover"
                    />
                  </div>
                ) : emoji ? (
                  <div className={cn(
                    'w-24 h-24 mx-auto rounded-2xl flex items-center justify-center',
                    'bg-white/10 ring-2 ring-white/20',
                    `shadow-lg ${theme.glow}`
                  )}>
                    <span className="text-5xl">{emoji}</span>
                  </div>
                ) : null}
              </motion.div>

              {/* Title */}
              <motion.div
                className="text-center"
                initial={{ y: 20, opacity: 0 }}
                animate={{
                  y: 0,
                  opacity: 1,
                  transition: { delay: 0.3 },
                }}
              >
                <h2 className={cn('text-2xl font-bold text-white mb-1', theme.accent)}>
                  {title}
                </h2>
                {subtitle && (
                  <p className="text-gray-400 text-sm">{subtitle}</p>
                )}
              </motion.div>

              {/* Stars */}
              {starsEarned > 0 && (
                <motion.div
                  className="flex justify-center gap-2"
                  initial={{ y: 20, opacity: 0 }}
                  animate={{
                    y: 0,
                    opacity: 1,
                    transition: { delay: 0.4 },
                  }}
                >
                  {[1, 2, 3].map((star) => (
                    <motion.div
                      key={star}
                      initial={{ scale: 0, rotate: -180 }}
                      animate={{
                        scale: star <= starsEarned ? 1 : 0.8,
                        rotate: 0,
                        transition: { delay: 0.4 + star * 0.15, type: 'spring' },
                      }}
                    >
                      <Star
                        className={cn(
                          'w-8 h-8',
                          star <= starsEarned
                            ? 'text-amber-400 fill-amber-400'
                            : 'text-gray-600'
                        )}
                      />
                    </motion.div>
                  ))}
                </motion.div>
              )}

              {/* Lore text with typewriter effect */}
              <motion.div
                className="bg-black/30 rounded-xl p-4 border border-white/10"
                initial={{ y: 20, opacity: 0 }}
                animate={{
                  y: 0,
                  opacity: 1,
                  transition: { delay: 0.5 },
                }}
              >
                <p className="text-gray-200 leading-relaxed whitespace-pre-wrap min-h-[60px]">
                  {displayedText}
                  {!isComplete && (
                    <motion.span
                      className="inline-block w-0.5 h-4 bg-white/50 ml-0.5"
                      animate={{ opacity: [1, 0] }}
                      transition={{ duration: 0.5, repeat: Infinity }}
                    />
                  )}
                </p>
                {!isComplete && (
                  <p className="text-xs text-gray-500 mt-2 text-center">
                    Нажмите, чтобы пропустить
                  </p>
                )}
              </motion.div>

              {/* Rewards */}
              <AnimatePresence>
                {showRewards && rewards.length > 0 && (
                  <motion.div
                    className="space-y-2"
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                  >
                    <h3 className="text-sm font-medium text-gray-400 text-center">
                      Награды
                    </h3>
                    <div className="flex flex-wrap justify-center gap-2">
                      {rewards.map((reward, index) => (
                        <motion.div
                          key={index}
                          className="flex items-center gap-2 bg-white/10 rounded-lg px-3 py-2"
                          initial={{ scale: 0, y: 20 }}
                          animate={{
                            scale: 1,
                            y: 0,
                            transition: { delay: index * 0.1, type: 'spring' },
                          }}
                        >
                          <span className="text-xl">{reward.emoji}</span>
                          <div className="text-sm">
                            <span className="text-white font-medium">
                              {typeof reward.value === 'number' ? `+${reward.value}` : reward.value}
                            </span>
                            {reward.label && (
                              <span className="text-gray-400 ml-1">{reward.label}</span>
                            )}
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Continue button */}
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{
                  y: 0,
                  opacity: isComplete ? 1 : 0.5,
                  transition: { delay: 0.6 },
                }}
              >
                <Button
                  onClick={(e) => {
                    e.stopPropagation();
                    onClose();
                  }}
                  className={cn(
                    'w-full',
                    `bg-gradient-to-r ${theme.button}`
                  )}
                >
                  Продолжить
                </Button>
              </motion.div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
