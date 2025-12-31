'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Swords, User, X } from 'lucide-react';
import { Button } from '@/components/ui';
import { cn } from '@/lib/utils';
import { hapticFeedback } from '@/lib/telegram';

interface DialogueLine {
  speaker: 'monster' | 'hero';
  text: string;
}

interface DialogueSheetProps {
  isOpen: boolean;
  onClose: () => void;
  onContinue: () => void;
  monsterName: string;
  monsterEmoji: string;
  monsterImageUrl?: string;
  heroName?: string;
  dialogue: DialogueLine[];
  title?: string;
  continueButtonText?: string;
}

export function DialogueSheet({
  isOpen,
  onClose,
  onContinue,
  monsterName,
  monsterEmoji,
  monsterImageUrl,
  heroName = 'Герой',
  dialogue,
  title = 'Встреча',
  continueButtonText = 'В бой!',
}: DialogueSheetProps) {
  const [currentLineIndex, setCurrentLineIndex] = useState(0);
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(true);

  const currentLine = dialogue[currentLineIndex];
  const isLastLine = currentLineIndex === dialogue.length - 1;

  // Typewriter effect
  useEffect(() => {
    if (!isOpen || !currentLine) return;

    setDisplayedText('');
    setIsTyping(true);

    let index = 0;
    const text = currentLine.text;

    const timer = setInterval(() => {
      if (index < text.length) {
        setDisplayedText(text.slice(0, index + 1));
        index++;
      } else {
        setIsTyping(false);
        clearInterval(timer);
      }
    }, 25);

    return () => clearInterval(timer);
  }, [currentLineIndex, currentLine, isOpen]);

  // Reset on open/close
  useEffect(() => {
    if (isOpen) {
      setCurrentLineIndex(0);
      setDisplayedText('');
      setIsTyping(true);
    }
  }, [isOpen]);

  const handleNextLine = useCallback(() => {
    if (isTyping) {
      // Skip to end of current line
      setDisplayedText(currentLine?.text || '');
      setIsTyping(false);
    } else if (isLastLine) {
      // Continue to battle
      hapticFeedback('medium');
      onContinue();
    } else {
      // Next line
      hapticFeedback('light');
      setCurrentLineIndex((prev) => prev + 1);
    }
  }, [isTyping, isLastLine, currentLine, onContinue]);

  const getSpeakerInfo = (speaker: 'monster' | 'hero') => {
    if (speaker === 'monster') {
      return {
        name: monsterName,
        emoji: monsterEmoji,
        imageUrl: monsterImageUrl,
        bgColor: 'bg-red-900/50',
        borderColor: 'border-red-500/30',
        align: 'items-start',
      };
    }
    return {
      name: heroName,
      emoji: '🦸',
      imageUrl: undefined,
      bgColor: 'bg-blue-900/50',
      borderColor: 'border-blue-500/30',
      align: 'items-end',
    };
  };

  if (!currentLine) return null;

  const speaker = getSpeakerInfo(currentLine.speaker);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-50 flex items-end justify-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={handleNextLine}
        >
          {/* Backdrop */}
          <motion.div
            className="absolute inset-0 bg-black/80 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />

          {/* Monster portrait at top */}
          <motion.div
            className="absolute top-20 left-1/2 -translate-x-1/2"
            initial={{ y: -50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <div className="w-28 h-28 rounded-2xl bg-gradient-to-br from-red-900/80 to-orange-900/80 border-2 border-red-500/50 flex items-center justify-center overflow-hidden shadow-lg shadow-red-500/30">
              {monsterImageUrl ? (
                <img src={monsterImageUrl} alt={monsterName} className="w-full h-full object-cover" />
              ) : (
                <span className="text-6xl">{monsterEmoji}</span>
              )}
            </div>
            <p className="text-center text-white font-bold mt-2">{monsterName}</p>
          </motion.div>

          {/* Dialogue box */}
          <motion.div
            className="relative w-full max-w-lg mx-4 mb-4"
            initial={{ y: 100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 100, opacity: 0 }}
          >
            {/* Close button */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onClose();
              }}
              className="absolute -top-12 right-0 p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors z-10"
            >
              <X className="w-5 h-5 text-white/70" />
            </button>

            {/* Dialogue bubble */}
            <div
              className={cn(
                'rounded-2xl p-5 border',
                speaker.bgColor,
                speaker.borderColor
              )}
            >
              {/* Speaker indicator */}
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
                  {currentLine.speaker === 'monster' ? (
                    <span className="text-lg">{monsterEmoji}</span>
                  ) : (
                    <User className="w-4 h-4 text-blue-400" />
                  )}
                </div>
                <span className="text-sm font-medium text-white/80">
                  {speaker.name}
                </span>
              </div>

              {/* Dialogue text */}
              <p className="text-white text-lg leading-relaxed min-h-[60px]">
                {displayedText}
                {isTyping && (
                  <motion.span
                    className="inline-block w-0.5 h-5 bg-white/50 ml-1"
                    animate={{ opacity: [1, 0] }}
                    transition={{ duration: 0.5, repeat: Infinity }}
                  />
                )}
              </p>

              {/* Progress indicator */}
              <div className="flex items-center justify-between mt-4 pt-3 border-t border-white/10">
                <div className="flex gap-1">
                  {dialogue.map((_, idx) => (
                    <div
                      key={idx}
                      className={cn(
                        'w-2 h-2 rounded-full transition-colors',
                        idx <= currentLineIndex ? 'bg-white/80' : 'bg-white/20'
                      )}
                    />
                  ))}
                </div>

                <p className="text-xs text-white/50">
                  {isTyping ? 'Нажмите, чтобы пропустить' : isLastLine ? 'Нажмите, чтобы начать бой' : 'Нажмите для продолжения'}
                </p>
              </div>
            </div>

            {/* Battle button (shows when dialogue is complete) */}
            {!isTyping && isLastLine && (
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                className="mt-4"
              >
                <Button
                  onClick={(e) => {
                    e.stopPropagation();
                    onContinue();
                  }}
                  className="w-full bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-700 hover:to-orange-700"
                >
                  <Swords className="w-5 h-5 mr-2" />
                  {continueButtonText}
                </Button>
              </motion.div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
