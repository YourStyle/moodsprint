'use client';

import { Modal } from '@/components/ui';
import type { TranslationKey } from '@/lib/i18n';

interface SharedReward {
  shared_id: number;
  task_title: string | null;
  card: {
    id: number;
    name: string;
    emoji: string;
    rarity: string;
    image_url?: string | null;
  };
}

interface SharedRewardsModalProps {
  isOpen: boolean;
  rewards: SharedReward[];
  onClose: () => void;
  t: (key: TranslationKey) => string;
}

const RARITY_COLORS: Record<string, string> = {
  common: 'border-slate-500/50',
  uncommon: 'border-emerald-500/50',
  rare: 'border-blue-500/50',
  epic: 'border-purple-500/50',
  legendary: 'border-amber-500/50',
};

const RARITY_BG: Record<string, string> = {
  common: 'bg-slate-500/10',
  uncommon: 'bg-emerald-500/10',
  rare: 'bg-blue-500/10',
  epic: 'bg-purple-500/10',
  legendary: 'bg-amber-500/10',
};

export function SharedRewardsModal({ isOpen, rewards, onClose, t }: SharedRewardsModalProps) {
  if (rewards.length === 0) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={t('sharedTaskRewards')}>
      <div className="space-y-3 max-h-[60vh] overflow-y-auto">
        {rewards.map((reward) => (
          <div
            key={reward.shared_id}
            className={`flex items-center gap-3 rounded-xl p-3 border ${RARITY_COLORS[reward.card.rarity] || 'border-gray-700'} ${RARITY_BG[reward.card.rarity] || 'bg-gray-800/50'}`}
          >
            {/* Card thumbnail */}
            <div className="w-12 h-12 rounded-lg overflow-hidden flex-shrink-0 border border-white/10">
              {reward.card.image_url ? (
                <img
                  src={reward.card.image_url}
                  alt={reward.card.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-gray-700">
                  <span className="text-xl">{reward.card.emoji || '🎴'}</span>
                </div>
              )}
            </div>

            {/* Card info */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{reward.card.name}</p>
              <p className="text-xs text-gray-400 truncate">{reward.task_title}</p>
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={onClose}
        className="w-full mt-4 py-3 rounded-xl bg-gradient-to-r from-primary-500 to-primary-600 text-white font-bold text-sm hover:opacity-90 transition-opacity"
      >
        {t('collectAll')}
      </button>
    </Modal>
  );
}
