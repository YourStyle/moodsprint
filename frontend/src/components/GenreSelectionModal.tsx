'use client';

import { useState, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Modal, Button } from '@/components/ui';
import { gamificationService, onboardingService } from '@/services';
import { useAppStore } from '@/lib/store';
import { hapticFeedback } from '@/lib/telegram';
import type { Genre } from '@/services/gamification';

const genreOptions: { value: Genre; label: string; emoji: string; desc: string }[] = [
  {
    value: 'magic',
    label: 'Магия',
    emoji: '🧙‍♂️',
    desc: 'Как в Гарри Поттере',
  },
  {
    value: 'fantasy',
    label: 'Фэнтези',
    emoji: '⚔️',
    desc: 'Как Властелин Колец',
  },
  {
    value: 'scifi',
    label: 'Научная фантастика',
    emoji: '🚀',
    desc: 'Космические приключения',
  },
  {
    value: 'cyberpunk',
    label: 'Киберпанк',
    emoji: '🌆',
    desc: 'Мир хакеров и технологий',
  },
  {
    value: 'anime',
    label: 'Аниме',
    emoji: '🎌',
    desc: 'Японские приключения',
  },
];

export function GenreSelectionModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedGenre, setSelectedGenre] = useState<Genre>('fantasy');
  const { user, onboardingCompleted } = useAppStore();

  // Check if user needs to select genre (onboarding completed but no genre)
  const { data: profileData, isLoading } = useQuery({
    queryKey: ['onboarding', 'profile'],
    queryFn: () => onboardingService.getProfile(),
    enabled: !!user && onboardingCompleted === true,
  });

  useEffect(() => {
    if (
      !isLoading &&
      profileData?.success &&
      profileData?.data?.profile &&
      profileData.data.profile.onboarding_completed &&
      !profileData.data.profile.favorite_genre
    ) {
      // User completed onboarding but has no genre - show modal
      setIsOpen(true);
    }
  }, [profileData, isLoading]);

  const saveMutation = useMutation({
    mutationFn: (genre: Genre) => gamificationService.setGenre(genre),
    onSuccess: () => {
      hapticFeedback('success');
      setIsOpen(false);
    },
  });

  const handleGenreSelect = (genre: Genre) => {
    setSelectedGenre(genre);
    hapticFeedback('light');
  };

  const handleSave = () => {
    saveMutation.mutate(selectedGenre);
  };

  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {}} // Don't allow closing without selection
      showClose={false}
      title="Выбери свой жанр"
    >
      <p className="text-gray-400 mb-4">
        Это определит стиль твоих квестов и приключений
      </p>

      <div className="space-y-2 mb-6">
        {genreOptions.map((opt) => (
          <button
            key={opt.value}
            onClick={() => handleGenreSelect(opt.value)}
            className={`w-full p-3 rounded-xl text-left transition-all ${
              selectedGenre === opt.value
                ? 'bg-primary-500/20 ring-2 ring-primary-500'
                : 'bg-gray-800 hover:bg-gray-700'
            }`}
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl">{opt.emoji}</span>
              <div>
                <p className="font-medium text-white">{opt.label}</p>
                <p className="text-sm text-gray-400">{opt.desc}</p>
              </div>
            </div>
          </button>
        ))}
      </div>

      <Button
        className="w-full"
        onClick={handleSave}
        isLoading={saveMutation.isPending}
      >
        Выбрать
      </Button>
    </Modal>
  );
}
