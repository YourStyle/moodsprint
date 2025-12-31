'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Swords, User, X, BookOpen } from 'lucide-react';
import { Button } from '@/components/ui';
import { cn } from '@/lib/utils';
import { hapticFeedback } from '@/lib/telegram';

interface DialogueLine {
  speaker: string; // 'monster', 'hero', 'narrator', or custom name
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
}: DialogueSheetProps) {
  const [currentLineIndex, setCurrentLineIndex] = useState(0);
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(true);

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

  if (!currentLine) return null;

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

          {/* Close button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onClose();
            }}
            className="absolute top-4 right-4 p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors z-10"
          >
            <X className="w-5 h-5 text-white/70" />
          </button>

          {/* Content area */}
          <div className="relative flex-1 flex flex-col justify-between p-4 pt-16 pb-8">

            {/* Monster block (top) */}
            <AnimatePresence mode="wait">
              {speakerType === 'monster' && (
                <motion.div
                  key="monster"
                  className="flex flex-col items-center"
                  initial={{ y: -30, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  exit={{ y: -30, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  {/* Monster avatar */}
                  <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-red-900/80 to-orange-900/80 border-2 border-red-500/50 flex items-center justify-center overflow-hidden shadow-lg shadow-red-500/30 mb-3">
                    {monsterImageUrl ? (
                      <img src={monsterImageUrl} alt={monsterName} className="w-full h-full object-cover" />
                    ) : (
                      <span className="text-4xl">{monsterEmoji}</span>
                    )}
                  </div>
                  <p className="text-sm font-medium text-red-400 mb-2">{monsterName}</p>

                  {/* Monster dialogue bubble */}
                  <div className="w-full max-w-sm bg-red-900/40 border border-red-500/30 rounded-2xl p-4">
                    <p className="text-white text-base leading-relaxed">
                      {displayedText}
                      {isTyping && (
                        <motion.span
                          className="inline-block w-0.5 h-4 bg-red-400/50 ml-1"
                          animate={{ opacity: [1, 0] }}
                          transition={{ duration: 0.5, repeat: Infinity }}
                        />
                      )}
                    </p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Narrator block (center) */}
            <AnimatePresence mode="wait">
              {speakerType === 'narrator' && (
                <motion.div
                  key="narrator"
                  className="flex-1 flex flex-col items-center justify-center"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.2 }}
                >
                  <BookOpen className="w-10 h-10 text-purple-400 mb-4" />
                  <div className="w-full max-w-md bg-purple-900/30 border border-purple-500/30 rounded-2xl p-5">
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
            </AnimatePresence>

            {/* Spacer for non-narrator */}
            {speakerType !== 'narrator' && <div className="flex-1" />}

            {/* Hero block (bottom) */}
            <AnimatePresence mode="wait">
              {speakerType === 'hero' && (
                <motion.div
                  key="hero"
                  className="flex flex-col items-center"
                  initial={{ y: 30, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  exit={{ y: 30, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  {/* Hero dialogue bubble */}
                  <div className="w-full max-w-sm bg-blue-900/40 border border-blue-500/30 rounded-2xl p-4 mb-3">
                    <p className="text-white text-base leading-relaxed">
                      {displayedText}
                      {isTyping && (
                        <motion.span
                          className="inline-block w-0.5 h-4 bg-blue-400/50 ml-1"
                          animate={{ opacity: [1, 0] }}
                          transition={{ duration: 0.5, repeat: Infinity }}
                        />
                      )}
                    </p>
                  </div>

                  {/* Hero avatar */}
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-900/80 to-cyan-900/80 border-2 border-blue-500/50 flex items-center justify-center shadow-lg shadow-blue-500/30">
                    <User className="w-8 h-8 text-blue-300" />
                  </div>
                  <p className="text-sm font-medium text-blue-400 mt-2">{heroName}</p>
                </motion.div>
              )}
            </AnimatePresence>

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

              {/* Battle button (shows when dialogue is complete) */}
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
