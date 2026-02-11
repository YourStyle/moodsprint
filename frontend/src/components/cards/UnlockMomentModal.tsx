'use client';

import { useState } from 'react';
import { Modal, Button } from '@/components/ui';
import { cn } from '@/lib/utils';
import { useTranslation } from '@/lib/i18n';
import { cardsService } from '@/services/cards';
import type { GenreUnlockInfo } from '@/services/cards';

const GENRE_INFO: Record<string, { emoji: string; color: string }> = {
  magic: { emoji: '✨', color: 'from-purple-500 to-indigo-600' },
  fantasy: { emoji: '⚔️', color: 'from-emerald-500 to-teal-600' },
  scifi: { emoji: '🚀', color: 'from-blue-500 to-cyan-600' },
  cyberpunk: { emoji: '🌆', color: 'from-pink-500 to-rose-600' },
  anime: { emoji: '🌸', color: 'from-orange-500 to-red-600' },
};

const genreKeys: Record<string, 'genreMagic' | 'genreFantasy' | 'genreScifi' | 'genreCyberpunk' | 'genreAnime'> = {
  magic: 'genreMagic',
  fantasy: 'genreFantasy',
  scifi: 'genreScifi',
  cyberpunk: 'genreCyberpunk',
  anime: 'genreAnime',
};

interface UnlockMomentModalProps {
  isOpen: boolean;
  onClose: () => void;
  unlockInfo: GenreUnlockInfo;
  onUnlocked?: (genre: string) => void;
}

export function UnlockMomentModal({ isOpen, onClose, unlockInfo, onUnlocked }: UnlockMomentModalProps) {
  const { t } = useTranslation();
  const [selectedGenre, setSelectedGenre] = useState<string | null>(null);
  const [isUnlocking, setIsUnlocking] = useState(false);

  const handleUnlock = async () => {
    if (!selectedGenre) return;
    setIsUnlocking(true);
    try {
      const res = await cardsService.selectGenreUnlock(selectedGenre);
      if (res.data?.success) {
        onUnlocked?.(selectedGenre);
        onClose();
      }
    } finally {
      setIsUnlocking(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} showClose>
      <div className="text-center pb-2">
        <div className="text-4xl mb-3 animate-bounce">🎉</div>
        <h2 className="text-xl font-bold text-white mb-2">{t('genreUnlockTitle')}</h2>
        <p className="text-gray-400 text-sm mb-6">{t('genreUnlockDesc')}</p>

        <div className="space-y-3 mb-6">
          {unlockInfo.available_genres.map((genre) => {
            const info = GENRE_INFO[genre] || GENRE_INFO.fantasy;
            const isSelected = selectedGenre === genre;

            return (
              <button
                key={genre}
                onClick={() => setSelectedGenre(genre)}
                className={cn(
                  'w-full p-4 rounded-xl border-2 transition-all flex items-center gap-4',
                  isSelected
                    ? 'border-white bg-white/10 scale-[1.02]'
                    : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
                )}
              >
                <div className={cn(
                  'w-12 h-12 rounded-xl bg-gradient-to-br flex items-center justify-center text-2xl',
                  info.color
                )}>
                  {info.emoji}
                </div>
                <div className="text-left">
                  <div className="font-bold text-white">{t(genreKeys[genre] || 'genreFantasy')}</div>
                  <div className="text-xs text-gray-400">{genre}</div>
                </div>
                {isSelected && (
                  <div className="ml-auto w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                    <span className="text-white text-sm">✓</span>
                  </div>
                )}
              </button>
            );
          })}
        </div>

        <Button
          onClick={handleUnlock}
          disabled={!selectedGenre || isUnlocking}
          className="w-full bg-gradient-to-r from-purple-500 to-pink-500 disabled:opacity-50"
        >
          {isUnlocking ? '...' : t('unlockGenre')}
        </Button>
      </div>
    </Modal>
  );
}

export default UnlockMomentModal;
