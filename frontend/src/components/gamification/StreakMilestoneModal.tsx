'use client';

import { useCallback } from 'react';
import { Flame, Sparkles, Gift, Share2 } from 'lucide-react';
import { Modal, Button } from '@/components/ui';
import { useTranslation } from '@/lib/i18n';
import { getTelegramWebApp } from '@/lib/telegram';
import { useAppStore } from '@/lib/store';

interface StreakMilestoneData {
  milestone_days: number;
  xp_bonus: number;
  card_earned?: {
    id: number;
    name: string;
    emoji: string;
    rarity: string;
  };
}

interface StreakMilestoneModalProps {
  isOpen: boolean;
  onClose: () => void;
  milestone: StreakMilestoneData | null;
}

const RARITY_COLORS: Record<string, string> = {
  common: 'text-gray-300',
  uncommon: 'text-green-400',
  rare: 'text-blue-400',
  epic: 'text-purple-400',
  legendary: 'text-yellow-400',
};

export function StreakMilestoneModal({ isOpen, onClose, milestone }: StreakMilestoneModalProps) {
  const { t } = useTranslation();
  const { user } = useAppStore();

  const handleShare = useCallback(() => {
    if (!milestone) return;
    const webApp = getTelegramWebApp();
    const inviteParam = user?.id ? `invite_${user.id}` : '';
    const appUrl = `https://t.me/moodsprint_bot${inviteParam ? `?startapp=${inviteParam}` : ''}`;
    const shareText = t('shareStreakText').replace('{days}', String(milestone.milestone_days));
    const telegramShareUrl = `https://t.me/share/url?url=${encodeURIComponent(appUrl)}&text=${encodeURIComponent(shareText)}`;

    if (webApp && webApp.openTelegramLink) {
      webApp.openTelegramLink(telegramShareUrl);
    } else {
      window.open(telegramShareUrl, '_blank');
    }
  }, [milestone, t, user?.id]);

  if (!milestone) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={t('streakMilestone')}>
      <div className="flex flex-col items-center">
        {/* Fire circle with milestone number */}
        <div className="relative mb-6">
          <div className="absolute inset-0 blur-2xl bg-gradient-to-br from-orange-500/40 to-red-500/40 rounded-full" />
          <div className="relative w-24 h-24 rounded-full bg-gradient-to-br from-orange-400 via-red-500 to-orange-600 flex items-center justify-center shadow-lg shadow-orange-500/30">
            <div className="w-20 h-20 rounded-full bg-dark-800 flex items-center justify-center">
              <div className="text-center">
                <Flame className="w-6 h-6 text-orange-400 mx-auto animate-pulse" />
                <span className="text-xl font-bold text-orange-400">
                  {milestone.milestone_days}
                </span>
              </div>
            </div>
          </div>
          <Sparkles className="absolute -top-2 -right-2 w-5 h-5 text-orange-400 animate-pulse" />
        </div>

        {/* Description */}
        <p className="text-gray-400 text-sm text-center mb-5">
          {t('streakMilestoneDesc').replace('{days}', String(milestone.milestone_days))}
        </p>

        {/* Rewards */}
        <div className="w-full space-y-2 mb-5">
          {/* XP reward */}
          <div className="flex items-center gap-3 bg-dark-700/60 rounded-xl px-4 py-3 border border-gray-700/50">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-orange-500/20 to-red-500/20 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-4 h-4 text-orange-400" />
            </div>
            <span className="text-sm text-white">
              {t('streakMilestoneXp').replace('{xp}', String(milestone.xp_bonus))}
            </span>
          </div>

          {/* Card reward */}
          {milestone.card_earned && (
            <div className="flex items-center gap-3 bg-dark-700/60 rounded-xl px-4 py-3 border border-gray-700/50">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-orange-500/20 to-red-500/20 flex items-center justify-center flex-shrink-0">
                <Gift className="w-4 h-4 text-orange-400" />
              </div>
              <div className="flex-1">
                <span className="text-sm text-white">{t('streakMilestoneCard')}</span>
                <span className={`text-sm ml-1 ${RARITY_COLORS[milestone.card_earned.rarity] || 'text-gray-300'}`}>
                  {milestone.card_earned.emoji} {milestone.card_earned.name}
                </span>
              </div>
            </div>
          )}
        </div>

        <div className="w-full flex gap-2">
          <Button
            onClick={handleShare}
            variant="secondary"
            className="flex-1 flex items-center justify-center gap-2"
          >
            <Share2 className="w-4 h-4" />
            {t('shareStreak')}
          </Button>
          <Button onClick={onClose} className="flex-1">
            {t('great')}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
