'use client';

import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ChevronDown, Check, Lock } from 'lucide-react';
import { gamificationService } from '@/services';
import { cardsService } from '@/services/cards';
import { hapticFeedback } from '@/lib/telegram';
import { cn } from '@/lib/utils';
import { useTranslation } from '@/lib/i18n';
import type { Genre } from '@/services/gamification';

// Genre unlock level thresholds (matches backend GENRE_UNLOCK_LEVELS)
const GENRE_UNLOCK_LEVELS: Record<number, number> = { 1: 1, 4: 2, 7: 3, 10: 4, 15: 5 };

function getNextUnlockLevel(currentGenreCount: number): number | null {
  for (const [level, count] of Object.entries(GENRE_UNLOCK_LEVELS).sort(([a], [b]) => Number(a) - Number(b))) {
    if (count > currentGenreCount) return Number(level);
  }
  return null;
}

const genreOptions: { value: Genre; labelKey: 'genreMagic' | 'genreFantasy' | 'genreScifi' | 'genreCyberpunk' | 'genreAnime'; emoji: string }[] = [
  { value: 'magic', labelKey: 'genreMagic', emoji: '🧙‍♂️' },
  { value: 'fantasy', labelKey: 'genreFantasy', emoji: '⚔️' },
  { value: 'scifi', labelKey: 'genreScifi', emoji: '🚀' },
  { value: 'cyberpunk', labelKey: 'genreCyberpunk', emoji: '🌆' },
  { value: 'anime', labelKey: 'genreAnime', emoji: '🎌' },
];

interface GenreSelectorProps {
  currentGenre?: string | null;
  className?: string;
  /** Called before switching genre. Return false to cancel the switch. */
  onBeforeSwitch?: (genre: string) => boolean;
}

export function GenreSelector({ currentGenre, className, onBeforeSwitch }: GenreSelectorProps) {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const [unlockedGenres, setUnlockedGenres] = useState<string[]>([]);
  const queryClient = useQueryClient();

  const currentOption = genreOptions.find(g => g.value === currentGenre);

  useEffect(() => {
    cardsService.getUnlockedGenres().then((res) => {
      if (res.data?.unlocked_genres) {
        setUnlockedGenres(res.data.unlocked_genres);
      }
    }).catch(() => {
      // Fallback: all genres unlocked
      setUnlockedGenres(genreOptions.map(g => g.value));
    });
  }, []);

  const mutation = useMutation({
    mutationFn: (genre: Genre) => gamificationService.setGenre(genre),
    onSuccess: () => {
      hapticFeedback('success');
      setIsOpen(false);
      queryClient.invalidateQueries({ queryKey: ['onboarding', 'profile'] });
      queryClient.invalidateQueries({ queryKey: ['campaign'] });
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      queryClient.invalidateQueries({ queryKey: ['card-templates'] });
    },
  });

  const handleSelect = (genre: Genre) => {
    if (!unlockedGenres.includes(genre)) {
      hapticFeedback('error');
      return;
    }
    if (genre !== currentGenre) {
      if (onBeforeSwitch && !onBeforeSwitch(genre)) {
        return;
      }
      mutation.mutate(genre);
    } else {
      setIsOpen(false);
    }
    hapticFeedback('light');
  };

  const nextUnlockLevel = getNextUnlockLevel(unlockedGenres.length);

  return (
    <div className={cn('relative', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-2 px-3 py-2 rounded-xl w-full',
          'bg-gray-800/80 border border-gray-700/50',
          'text-sm text-gray-300 hover:text-white transition-colors'
        )}
      >
        <span>{currentOption?.emoji || '🎮'}</span>
        <span>{currentOption ? t(currentOption.labelKey) : t('selectGenre')}</span>
        <ChevronDown className={cn('w-4 h-4 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-[100]"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown */}
          <div className="absolute top-full left-0 mt-2 z-[101] w-56 py-1 bg-gray-800 border border-gray-700 rounded-xl shadow-xl">
            {genreOptions.map((option) => {
              const isLocked = unlockedGenres.length > 0 && !unlockedGenres.includes(option.value);

              return (
                <button
                  key={option.value}
                  onClick={() => handleSelect(option.value)}
                  disabled={mutation.isPending || isLocked}
                  className={cn(
                    'w-full flex items-center gap-2 px-3 py-2 text-left text-sm',
                    'transition-colors',
                    isLocked
                      ? 'text-gray-600 cursor-not-allowed'
                      : 'hover:bg-gray-700/50',
                    option.value === currentGenre ? 'text-primary-400' : isLocked ? '' : 'text-gray-300'
                  )}
                >
                  <span className={isLocked ? 'grayscale opacity-50' : ''}>{option.emoji}</span>
                  <span className="flex-1">{t(option.labelKey)}</span>
                  {isLocked ? (
                    <div className="flex items-center gap-1 text-gray-600">
                      <Lock className="w-3 h-3" />
                      <span className="text-[10px]">
                        {t('genreLocked').replace('{level}', String(nextUnlockLevel || '?'))}
                      </span>
                    </div>
                  ) : option.value === currentGenre ? (
                    <Check className="w-4 h-4 text-primary-400" />
                  ) : null}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

export default GenreSelector;
