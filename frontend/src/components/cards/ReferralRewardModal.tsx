'use client';

import { useState } from 'react';
import { Users, Gift, Share2, Heart, Swords, Sparkles, ChevronRight } from 'lucide-react';
import { Button, Modal } from '@/components/ui';

interface Card {
  id: number;
  name: string;
  description?: string;
  genre: string;
  rarity: string;
  hp: number;
  attack: number;
  emoji: string;
  image_url?: string | null;
}

interface ReferralReward {
  friendName?: string;
  friendId?: number;
  isReferrer: boolean; // true = you invited someone, false = you were invited
  cards: Card[];
}

interface ReferralRewardModalProps {
  isOpen: boolean;
  rewards: ReferralReward[];
  onClose: () => void;
}

const RARITY_COLORS: Record<string, string> = {
  common: 'from-gray-500 to-gray-600',
  uncommon: 'from-green-500 to-green-600',
  rare: 'from-blue-500 to-blue-600',
  epic: 'from-purple-500 to-purple-600',
  legendary: 'from-yellow-500 to-orange-500',
};

const RARITY_LABELS: Record<string, string> = {
  common: 'Обычная',
  uncommon: 'Необычная',
  rare: 'Редкая',
  epic: 'Эпическая',
  legendary: 'Легендарная',
};

function MiniCard({ card }: { card: Card }) {
  return (
    <div className={`w-24 rounded-xl bg-gradient-to-br ${RARITY_COLORS[card.rarity] || RARITY_COLORS.common} p-0.5`}>
      <div className="w-full bg-gray-900 rounded-xl flex flex-col overflow-hidden">
        <div className="h-20 flex items-center justify-center bg-gray-800">
          {card.image_url ? (
            <img src={card.image_url} alt={card.name} className="w-full h-full object-cover" />
          ) : (
            <span className="text-2xl">{card.emoji}</span>
          )}
        </div>
        <div className="px-1.5 py-1.5 space-y-0.5">
          <p className="text-white font-bold text-[10px] truncate">{card.name}</p>
          <div className="flex justify-between text-[9px]">
            <span className="text-red-400 flex items-center gap-0.5">
              <Heart className="w-2 h-2" /> {card.hp}
            </span>
            <span className="text-orange-400 flex items-center gap-0.5">
              <Swords className="w-2 h-2" /> {card.attack}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function ReferralRewardModal({ isOpen, rewards, onClose }: ReferralRewardModalProps) {
  const [activeTab, setActiveTab] = useState(0);

  if (!isOpen || rewards.length === 0) return null;

  // Group rewards by type
  const invitedByRewards = rewards.filter(r => !r.isReferrer);
  const invitedOthersRewards = rewards.filter(r => r.isReferrer);

  // Determine what to show
  const showInvitedByTab = invitedByRewards.length > 0;
  const showInvitedOthersTab = invitedOthersRewards.length > 0;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="">
      <div className="flex flex-col items-center -mt-4">
        {/* Header Icon */}
        <div className="w-16 h-16 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center mb-4">
          <Users className="w-8 h-8 text-white" />
        </div>

        {/* Tabs if both types exist */}
        {showInvitedByTab && showInvitedOthersTab && (
          <div className="flex gap-2 mb-4 w-full">
            <button
              onClick={() => setActiveTab(0)}
              className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 0
                  ? 'bg-purple-500 text-white'
                  : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              Новая дружба
            </button>
            <button
              onClick={() => setActiveTab(1)}
              className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 1
                  ? 'bg-purple-500 text-white'
                  : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              Подарки
            </button>
          </div>
        )}

        {/* Content based on active tab */}
        {((activeTab === 0 && showInvitedByTab) || (!showInvitedOthersTab && showInvitedByTab)) && (
          <div className="w-full space-y-4">
            {invitedByRewards.map((reward, idx) => (
              <div key={idx} className="space-y-3">
                <h3 className="text-lg font-bold text-white text-center">
                  Вы подружились с {reward.friendName || 'новым другом'}! 🎉
                </h3>
                <p className="text-gray-400 text-sm text-center">
                  Теперь вы можете обмениваться карточками и дарить их друг другу.
                </p>
              </div>
            ))}

            {/* Cards received */}
            {invitedByRewards.some(r => r.cards.length > 0) && (
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-center gap-2 text-pink-400">
                  <Gift className="w-5 h-5" />
                  <span className="font-medium">Вот ваши подарочные карточки:</span>
                </div>
                <div className="flex flex-wrap justify-center gap-2">
                  {invitedByRewards.flatMap(r => r.cards).map((card) => (
                    <MiniCard key={card.id} card={card} />
                  ))}
                </div>
              </div>
            )}

            {/* Invite tip */}
            <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-3 mt-4">
              <div className="flex items-start gap-2">
                <Share2 className="w-5 h-5 text-purple-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="text-purple-300 font-medium">Приглашайте друзей!</p>
                  <p className="text-gray-400 text-xs mt-1">
                    Тот, кого вы пригласите, получит стартовую колоду, а вы — крутую карточку.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {((activeTab === 1 && showInvitedOthersTab) || (!showInvitedByTab && showInvitedOthersTab)) && (
          <div className="w-full space-y-4">
            {/* Friends who joined */}
            <h3 className="text-lg font-bold text-white text-center">
              {invitedOthersRewards.length === 1
                ? `${invitedOthersRewards[0].friendName || 'Друг'} присоединился!`
                : `${invitedOthersRewards.length} друзей присоединились!`}
            </h3>

            {invitedOthersRewards.length > 1 && (
              <div className="space-y-2">
                {invitedOthersRewards.map((reward, idx) => (
                  <div key={idx} className="flex items-center gap-2 bg-gray-800/50 rounded-lg p-2">
                    <div className="w-8 h-8 rounded-full bg-purple-500/30 flex items-center justify-center">
                      <Users className="w-4 h-4 text-purple-400" />
                    </div>
                    <span className="text-white text-sm font-medium">
                      {reward.friendName || 'Новый друг'}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Cards received */}
            {invitedOthersRewards.some(r => r.cards.length > 0) && (
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-center gap-2 text-yellow-400">
                  <Sparkles className="w-5 h-5" />
                  <span className="font-medium">Ваши награды:</span>
                </div>
                <div className="flex flex-wrap justify-center gap-2">
                  {invitedOthersRewards.flatMap(r => r.cards).map((card) => (
                    <MiniCard key={card.id} card={card} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <Button onClick={onClose} className="w-full mt-6">
          Отлично!
        </Button>
      </div>
    </Modal>
  );
}
