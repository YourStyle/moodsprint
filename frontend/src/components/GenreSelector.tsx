'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ChevronDown, Check } from 'lucide-react';
import { gamificationService } from '@/services';
import { hapticFeedback } from '@/lib/telegram';
import { cn } from '@/lib/utils';
import type { Genre } from '@/services/gamification';

const genreOptions: { value: Genre; label: string; emoji: string }[] = [
  { value: 'magic', label: 'Магия', emoji: '🧙‍♂️' },
  { value: 'fantasy', label: 'Фэнтези', emoji: '⚔️' },
  { value: 'scifi', label: 'Sci-Fi', emoji: '🚀' },
  { value: 'cyberpunk', label: 'Киберпанк', emoji: '🌆' },
  { value: 'anime', label: 'Аниме', emoji: '🎌' },
];

interface GenreSelectorProps {
  currentGenre?: string | null;
  className?: string;
}

export function GenreSelector({ currentGenre, className }: GenreSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const queryClient = useQueryClient();

  const currentOption = genreOptions.find(g => g.value === currentGenre);

  const mutation = useMutation({
    mutationFn: (genre: Genre) => gamificationService.setGenre(genre),
    onSuccess: () => {
      hapticFeedback('success');
      setIsOpen(false);
      queryClient.invalidateQueries({ queryKey: ['onboarding', 'profile'] });
    },
  });

  const handleSelect = (genre: Genre) => {
    if (genre !== currentGenre) {
      mutation.mutate(genre);
    } else {
      setIsOpen(false);
    }
    hapticFeedback('light');
  };

  return (
    <div className={cn('relative', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-2 px-3 py-2 rounded-xl',
          'bg-gray-800/80 border border-gray-700/50',
          'text-sm text-gray-300 hover:text-white transition-colors'
        )}
      >
        <span>{currentOption?.emoji || '🎮'}</span>
        <span>{currentOption?.label || 'Выбрать жанр'}</span>
        <ChevronDown className={cn('w-4 h-4 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown */}
          <div className="absolute top-full left-0 mt-2 z-50 w-48 py-1 bg-gray-800 border border-gray-700 rounded-xl shadow-xl">
            {genreOptions.map((option) => (
              <button
                key={option.value}
                onClick={() => handleSelect(option.value)}
                disabled={mutation.isPending}
                className={cn(
                  'w-full flex items-center gap-2 px-3 py-2 text-left text-sm',
                  'hover:bg-gray-700/50 transition-colors',
                  option.value === currentGenre ? 'text-primary-400' : 'text-gray-300'
                )}
              >
                <span>{option.emoji}</span>
                <span className="flex-1">{option.label}</span>
                {option.value === currentGenre && (
                  <Check className="w-4 h-4 text-primary-400" />
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default GenreSelector;
