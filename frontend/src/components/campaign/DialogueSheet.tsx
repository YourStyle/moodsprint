'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Swords, User, BookOpen } from 'lucide-react';
import { Button } from '@/components/ui';
import { cn } from '@/lib/utils';
import { hapticFeedback } from '@/lib/telegram';

interface DialogueLine {
  speaker: string;
  text: string;
  emoji?: string;
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
  showSkipButton?: boolean;
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
  continueButtonText = 'В бой!',
  showSkipButton = false,
}: DialogueSheetProps) {
  const [currentLineIndex, setCurrentLineIndex] = useState(0);
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(true);
  const [monsterText, setMonsterText] = useState('');
  const [heroText, setHeroText] = useState('');

  const currentLine = dialogue[currentLineIndex];
  const isLastLine = currentLineIndex === dialogue.length - 1;

  // Determine speaker type
  const getSpeakerType = (speaker: string): 'monster' | 'hero' | 'narrator' => {
    const lowerSpeaker = speaker.toLowerCase();
    if (lowerSpeaker === 'monster' || lowerSpeaker === monsterName.toLowerCase()) {
      return 'monster';
    }
    if (lowerSpeaker === 'hero' || lowerSpeaker === 'герой' || lowerSpeaker === heroName.toLowerCase()) {
      return 'hero';
    }
    return 'narrator';
  };

  const speakerType = currentLine ? getSpeakerType(currentLine.speaker) : 'narrator';

  // Typewriter effect
  useEffect(() => {
    if (!isOpen || !currentLine) return;

    // Clear the current speaker's text
    if (speakerType === 'monster') {
      setMonsterText('');
    } else if (speakerType === 'hero') {
      setHeroText('');
    }
    setDisplayedText('');
    setIsTyping(true);

    let index = 0;
    const text = currentLine.text;

    const timer = setInterval(() => {
      if (index < text.length) {
        const newText = text.slice(0, index + 1);
        setDisplayedText(newText);
        if (speakerType === 'monster') {
          setMonsterText(newText);
        } else if (speakerType === 'hero') {
          setHeroText(newText);
        }
        index++;
      } else {
        setIsTyping(false);
        clearInterval(timer);
      }
    }, 25);

    return () => clearInterval(timer);
  }, [currentLineIndex, currentLine, isOpen, speakerType]);

  // Reset on open/close
  useEffect(() => {
    if (isOpen) {
      setCurrentLineIndex(0);
      setDisplayedText('');
      setMonsterText('');
      setHeroText('');
      setIsTyping(true);
    }
  }, [isOpen]);

  const handleNextLine = useCallback(() => {
    if (isTyping) {
      // Skip to end of current line
      const text = currentLine?.text || '';
      setDisplayedText(text);
      if (speakerType === 'monster') {
        setMonsterText(text);
      } else if (speakerType === 'hero') {
        setHeroText(text);
      }
      setIsTyping(false);
    } else if (isLastLine) {
      hapticFeedback('medium');
      onContinue();
    } else {
      hapticFeedback('light');
      setCurrentLineIndex((prev) => prev + 1);
    }
  }, [isTyping, isLastLine, currentLine, onContinue, speakerType]);

  if (!currentLine) return null;

  const isNarrator = speakerType === 'narrator';

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-[100] flex flex-col"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={handleNextLine}
        >
          {/* Backdrop */}
          <motion.div
            className="absolute inset-0 bg-black/90"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />

          {/* Skip button - shown for repeat battles, bottom right corner */}
          {showSkipButton && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                hapticFeedback('medium');
                onContinue();
              }}
              className="absolute bottom-28 right-4 px-2.5 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-white/60 text-xs font-medium transition-colors z-10"
            >
              Пропустить »
            </button>
          )}

          {/* Content area */}
          <div className="relative flex-1 flex flex-col p-4 pt-8 pb-8">

            {/* Monster block (top) - always visible */}
            {!isNarrator && (
              <motion.div
                className="flex flex-col items-center mb-4"
                initial={{ y: -30, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.3 }}
              >
                {/* Monster avatar */}
                <div className={cn(
                  "w-20 h-20 rounded-2xl border-2 flex items-center justify-center overflow-hidden shadow-lg mb-3 transition-all duration-300",
                  speakerType === 'monster'
                    ? "bg-gradient-to-br from-red-900/80 to-orange-900/80 border-red-500/70 shadow-red-500/40 scale-105"
                    : "bg-gradient-to-br from-red-900/40 to-orange-900/40 border-red-500/30 shadow-red-500/20 opacity-60"
                )}>
                  {monsterImageUrl ? (
                    <img src={monsterImageUrl} alt={monsterName} className="w-full h-full object-cover" />
                  ) : (
                    <span className="text-4xl">{monsterEmoji}</span>
                  )}
                </div>
                <p className={cn(
                  "text-sm font-medium mb-2 transition-colors",
                  speakerType === 'monster' ? "text-red-400" : "text-red-400/50"
                )}>{monsterName}</p>

                {/* Monster dialogue bubble */}
                <div className={cn(
                  "w-full bg-red-900/40 border rounded-2xl p-4 min-h-[80px] transition-all duration-300",
                  speakerType === 'monster'
                    ? "border-red-500/50 bg-red-900/50"
                    : "border-red-500/20 bg-red-900/20 opacity-60"
                )}>
                  <p className="text-white text-base leading-relaxed">
                    {speakerType === 'monster' ? (
                      <>
                        {displayedText}
                        {isTyping && (
                          <motion.span
                            className="inline-block w-0.5 h-4 bg-red-400/50 ml-1"
                            animate={{ opacity: [1, 0] }}
                            transition={{ duration: 0.5, repeat: Infinity }}
                          />
                        )}
                      </>
                    ) : (
                      <span className="text-white/50">{monsterText || '...'}</span>
                    )}
                  </p>
                </div>
              </motion.div>
            )}

            {/* Narrator block (center) */}
            {isNarrator && (
              <motion.div
                className="flex-1 flex flex-col items-center justify-center"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.2 }}
              >
                <BookOpen className="w-10 h-10 text-purple-400 mb-4" />
                <div className="w-full bg-purple-900/30 border border-purple-500/30 rounded-2xl p-5">
                  <p className="text-white text-center text-lg leading-relaxed italic">
                    {displayedText}
                    {isTyping && (
                      <motion.span
                        className="inline-block w-0.5 h-5 bg-purple-400/50 ml-1"
                        animate={{ opacity: [1, 0] }}
                        transition={{ duration: 0.5, repeat: Infinity }}
                      />
                    )}
                  </p>
                </div>
              </motion.div>
            )}

            {/* Spacer */}
            {!isNarrator && <div className="flex-1" />}

            {/* Hero block (bottom) - always visible */}
            {!isNarrator && (
              <motion.div
                className="flex flex-col items-center mt-4"
                initial={{ y: 30, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.3 }}
              >
                {/* Hero dialogue bubble */}
                <div className={cn(
                  "w-full border rounded-2xl p-4 mb-3 min-h-[80px] transition-all duration-300",
                  speakerType === 'hero'
                    ? "bg-blue-900/50 border-blue-500/50"
                    : "bg-blue-900/20 border-blue-500/20 opacity-60"
                )}>
                  <p className="text-white text-base leading-relaxed">
                    {speakerType === 'hero' ? (
                      <>
                        {displayedText}
                        {isTyping && (
                          <motion.span
                            className="inline-block w-0.5 h-4 bg-blue-400/50 ml-1"
                            animate={{ opacity: [1, 0] }}
                            transition={{ duration: 0.5, repeat: Infinity }}
                          />
                        )}
                      </>
                    ) : (
                      <span className="text-white/50">{heroText || '...'}</span>
                    )}
                  </p>
                </div>

                {/* Hero avatar */}
                <div className={cn(
                  "w-16 h-16 rounded-2xl border-2 flex items-center justify-center shadow-lg transition-all duration-300",
                  speakerType === 'hero'
                    ? "bg-gradient-to-br from-blue-900/80 to-cyan-900/80 border-blue-500/70 shadow-blue-500/40 scale-105"
                    : "bg-gradient-to-br from-blue-900/40 to-cyan-900/40 border-blue-500/30 shadow-blue-500/20 opacity-60"
                )}>
                  <User className="w-8 h-8 text-blue-300" />
                </div>
                <p className={cn(
                  "text-sm font-medium mt-2 transition-colors",
                  speakerType === 'hero' ? "text-blue-400" : "text-blue-400/50"
                )}>{heroName}</p>
              </motion.div>
            )}

            {/* Progress and controls */}
            <div className="mt-6 space-y-4">
              {/* Progress dots */}
              <div className="flex justify-center gap-1.5">
                {dialogue.map((_, idx) => (
                  <div
                    key={idx}
                    className={cn(
                      'w-2 h-2 rounded-full transition-colors',
                      idx < currentLineIndex ? 'bg-white/60' :
                      idx === currentLineIndex ? 'bg-white' : 'bg-white/20'
                    )}
                  />
                ))}
              </div>

              {/* Hint text */}
              <p className="text-center text-xs text-white/40">
                {isTyping ? 'Нажмите, чтобы пропустить' : isLastLine ? 'Нажмите, чтобы начать бой' : 'Нажмите для продолжения'}
              </p>

              {/* Battle button */}
              {!isTyping && isLastLine && (
                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
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
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
