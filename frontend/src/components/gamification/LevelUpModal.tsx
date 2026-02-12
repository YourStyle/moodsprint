'use client';

import { useState } from 'react';
import { Sparkles, Zap, Crown, Star, Gift } from 'lucide-react';
import { Modal, Button } from '@/components/ui';
import { useTranslation, type TranslationKey } from '@/lib/i18n';
import { cardsService } from '@/services/cards';

// Reward item from backend level_service.grant_level_rewards
export interface LevelRewardItem {
  type: 'sparks' | 'energy' | 'card' | 'genre_unlock' | 'archetype_tier' | 'xp_boost';
  amount?: number;
  rarity?: string;
  slot?: number;
  tier?: string;
  card?: {
    id: number;
    name: string;
    emoji: string;
    rarity: string;
  } | null;
  description?: string;
}

const GENRE_INFO: Record<string, { emoji: string; color: string }> = {
  magic: { emoji: '✨', color: 'from-purple-500 to-indigo-600' },
  fantasy: { emoji: '⚔️', color: 'from-emerald-500 to-teal-600' },
  scifi: { emoji: '🚀', color: 'from-blue-500 to-cyan-600' },
  cyberpunk: { emoji: '🌆', color: 'from-pink-500 to-rose-600' },
  anime: { emoji: '🌸', color: 'from-orange-500 to-red-600' },
};

const genreKeys: Record<string, TranslationKey> = {
  magic: 'genreMagic',
  fantasy: 'genreFantasy',
  scifi: 'genreScifi',
  cyberpunk: 'genreCyberpunk',
  anime: 'genreAnime',
};

const RARITY_COLORS: Record<string, string> = {
  common: 'text-gray-300',
  uncommon: 'text-green-400',
  rare: 'text-blue-400',
  epic: 'text-purple-400',
  legendary: 'text-yellow-400',
};

const RARITY_KEYS: Record<string, TranslationKey> = {
  common: 'rarityCommon',
  uncommon: 'rarityUncommon',
  rare: 'rarityRare',
  epic: 'rarityEpic',
  legendary: 'rarityLegendary',
};

const REWARD_ICONS: Record<string, typeof Sparkles> = {
  sparks: Sparkles,
  energy: Zap,
  card: Gift,
  genre_unlock: Crown,
  archetype_tier: Star,
  xp_boost: Star,
};

interface LevelUpModalProps {
  isOpen: boolean;
  onClose: () => void;
  newLevel: number;
  rewards: LevelRewardItem[];
  genreUnlockAvailable?: {
    can_unlock: boolean;
    available_genres: string[];
    suggested_genres?: string[];
  } | null;
  onGenreSelect?: (genre: string) => void;
}

export function LevelUpModal({
  isOpen,
  onClose,
  newLevel,
  rewards,
  genreUnlockAvailable,
  onGenreSelect,
}: LevelUpModalProps) {
  const { t } = useTranslation();
  const [selectedGenre, setSelectedGenre] = useState<string | null>(null);
  const [isUnlocking, setIsUnlocking] = useState(false);

  const handleGenreUnlock = async () => {
    if (!selectedGenre) return;
    setIsUnlocking(true);
    try {
      const result = await cardsService.selectGenreUnlock(selectedGenre);
      if (result.success) {
        onGenreSelect?.(selectedGenre);
      }
    } catch (e) {
      console.error('Genre unlock failed:', e);
    } finally {
      setIsUnlocking(false);
    }
  };

  const handleClose = () => {
    setSelectedGenre(null);
    onClose();
  };

  // Whether genre selection is still needed
  const hasGenreUnlock = genreUnlockAvailable?.can_unlock;
  const suggestedGenres = genreUnlockAvailable?.suggested_genres || genreUnlockAvailable?.available_genres || [];

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={t('levelUp')}>
      <div className="flex flex-col items-center">
        {/* Level number with celebration */}
        <div className="relative mb-6">
          <div className="absolute inset-0 blur-2xl bg-gradient-to-br from-yellow-500/40 to-purple-500/40 rounded-full" />
          <div className="relative w-24 h-24 rounded-full bg-gradient-to-br from-yellow-400 via-orange-500 to-purple-600 flex items-center justify-center shadow-lg shadow-yellow-500/30">
            <div className="w-20 h-20 rounded-full bg-dark-800 flex items-center justify-center">
              <span className="text-3xl font-bold bg-gradient-to-r from-yellow-400 to-purple-400 bg-clip-text text-transparent">
                {newLevel}
              </span>
            </div>
          </div>
          {/* Sparkle decorations */}
          <Sparkles className="absolute -top-2 -right-2 w-5 h-5 text-yellow-400 animate-pulse" />
          <Sparkles className="absolute -bottom-1 -left-3 w-4 h-4 text-purple-400 animate-pulse" style={{ animationDelay: '0.5s' }} />
        </div>

        {/* Rewards list */}
        {rewards.length > 0 && (
          <div className="w-full space-y-2 mb-5">
            <p className="text-sm text-gray-400 text-center mb-3">{t('levelRewards')}</p>
            {rewards.map((reward, idx) => {
              const Icon = REWARD_ICONS[reward.type] || Gift;
              return (
                <div
                  key={idx}
                  className="flex items-center gap-3 bg-dark-700/60 rounded-xl px-4 py-3 border border-gray-700/50"
                >
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-yellow-500/20 to-purple-500/20 flex items-center justify-center flex-shrink-0">
                    <Icon className="w-4 h-4 text-yellow-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    {reward.type === 'sparks' && (
                      <span className="text-sm text-white">
                        {t('sparksReward').replace('{amount}', String(reward.amount || 0))}
                      </span>
                    )}
                    {reward.type === 'energy' && (
                      <span className="text-sm text-white">
                        {t('energyReward').replace('{amount}', String(reward.amount || 0))}
                      </span>
                    )}
                    {reward.type === 'card' && (
                      <span className="text-sm text-white">
                        {t('cardReward').replace('{rarity}', t(RARITY_KEYS[reward.rarity || 'common']))}
                        {reward.card && (
                          <span className="text-gray-400 ml-1">
                            — {reward.card.emoji} {reward.card.name}
                          </span>
                        )}
                      </span>
                    )}
                    {reward.type === 'genre_unlock' && (
                      <span className="text-sm text-white">
                        {t('genreUnlockReward')}
                      </span>
                    )}
                    {reward.type === 'archetype_tier' && (
                      <span className="text-sm text-white capitalize">
                        {reward.tier} {t('xpBoostReward').replace('{amount}', String(reward.amount || ''))}
                      </span>
                    )}
                    {reward.type === 'xp_boost' && (
                      <span className="text-sm text-white">
                        {t('xpBoostReward').replace('{amount}', String(reward.amount || ''))}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Genre unlock selection */}
        {hasGenreUnlock && suggestedGenres.length > 0 && (
          <div className="w-full mb-5">
            <p className="text-sm text-gray-400 text-center mb-3">{t('selectNewGenre')}</p>
            <div className="grid grid-cols-2 gap-2">
              {suggestedGenres.slice(0, 2).map((genre) => {
                const info = GENRE_INFO[genre] || { emoji: '?', color: 'from-gray-500 to-gray-600' };
                const isSelected = selectedGenre === genre;
                return (
                  <button
                    key={genre}
                    onClick={() => setSelectedGenre(genre)}
                    className={`relative p-4 rounded-xl border-2 transition-all ${
                      isSelected
                        ? 'border-yellow-500 bg-yellow-500/10'
                        : 'border-gray-700 bg-dark-700/60 hover:border-gray-500'
                    }`}
                  >
                    <div className="text-2xl mb-1">{info.emoji}</div>
                    <div className="text-sm font-medium text-white">
                      {t(genreKeys[genre] || 'genreFantasy')}
                    </div>
                  </button>
                );
              })}
            </div>
            {selectedGenre && (
              <Button
                onClick={handleGenreUnlock}
                variant="gradient"
                className="w-full mt-3"
                disabled={isUnlocking}
              >
                {isUnlocking ? t('loading') : t('selectNewGenre')}
              </Button>
            )}
          </div>
        )}

        {/* Continue button */}
        {!hasGenreUnlock && (
          <Button onClick={handleClose} className="w-full">
            {t('great')}
          </Button>
        )}
        {hasGenreUnlock && !selectedGenre && (
          <button
            onClick={handleClose}
            className="text-sm text-gray-500 hover:text-gray-400 mt-2"
          >
            {t('close')}
          </button>
        )}
      </div>
    </Modal>
  );
}
