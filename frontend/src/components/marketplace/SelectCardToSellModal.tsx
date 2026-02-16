'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Package, Heart, Swords, Loader2 } from 'lucide-react';
import { Modal } from '@/components/ui';
import { cardsService, type Card } from '@/services/cards';
import { cn } from '@/lib/utils';
import { useTranslation } from '@/lib/i18n';

interface SelectCardToSellModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectCard: (card: Card) => void;
}

// Group cards by template to stack duplicates
function groupCards(cards: Card[]): (Card & { _count: number })[] {
  const groups = new Map<string, Card[]>();
  for (const card of cards) {
    const key = card.template_id ? `tmpl_${card.template_id}` : `card_${card.id}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(card);
  }
  return Array.from(groups.values()).map(group => ({
    ...group[0],
    _count: group.length,
  }));
}

const RARITY_CONFIG: Record<string, { labelKey: 'rarityCommon' | 'rarityUncommon' | 'rarityRare' | 'rarityEpic' | 'rarityLegendary'; bg: string; text: string }> = {
  common: { labelKey: 'rarityCommon', bg: 'bg-slate-600', text: 'text-slate-300' },
  uncommon: { labelKey: 'rarityUncommon', bg: 'bg-emerald-600', text: 'text-emerald-300' },
  rare: { labelKey: 'rarityRare', bg: 'bg-blue-600', text: 'text-blue-300' },
  epic: { labelKey: 'rarityEpic', bg: 'bg-purple-600', text: 'text-purple-300' },
  legendary: { labelKey: 'rarityLegendary', bg: 'bg-gradient-to-r from-amber-500 to-orange-500', text: 'text-amber-300' },
};

export function SelectCardToSellModal({ isOpen, onClose, onSelectCard }: SelectCardToSellModalProps) {
  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState('');

  const { data: cardsData, isLoading } = useQuery({
    queryKey: ['cards', 'sellable'],
    queryFn: () => cardsService.getCards(),
    enabled: isOpen,
  });

  // Filter cards that can be sold (not in deck, tradeable, alive)
  const availableCards = cardsData?.data?.cards?.filter(card =>
    !card.is_in_deck &&
    card.is_tradeable &&
    card.is_alive &&
    (searchQuery === '' || card.name.toLowerCase().includes(searchQuery.toLowerCase()))
  ) || [];

  const handleSelectCard = (card: Card) => {
    onSelectCard(card);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Выбрать карту для продажи">
      <div className="space-y-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Поиск по названию..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-gray-800/50 border border-gray-700/50 rounded-xl py-2.5 pl-10 pr-4 text-white placeholder-gray-500 focus:outline-none focus:border-amber-500 transition-colors"
          />
        </div>

        {/* Cards list */}
        <div className="max-h-[400px] overflow-y-auto -mx-4 px-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 text-amber-400 animate-spin" />
            </div>
          ) : availableCards.length > 0 ? (
            <div className="grid grid-cols-2 gap-3">
              {groupCards(availableCards).map((card) => {
                const rarityConf = RARITY_CONFIG[card.rarity] || RARITY_CONFIG.common;

                return (
                  <button
                    key={card.id}
                    onClick={() => handleSelectCard(card)}
                    className="relative bg-gray-800/50 border border-gray-700/50 rounded-xl overflow-hidden hover:border-amber-500/50 transition-colors text-left"
                  >
                    {card._count > 1 && (
                      <span className="absolute top-2 right-2 z-10 min-w-[22px] h-[22px] rounded-full bg-blue-500 border-2 border-gray-800 text-[10px] font-bold text-white flex items-center justify-center px-1">
                        x{card._count}
                      </span>
                    )}
                    {/* Card image */}
                    <div className="aspect-square relative">
                      {card.image_url ? (
                        <img
                          src={card.image_url}
                          alt={card.name}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full bg-gradient-to-b from-gray-700 to-gray-800 flex items-center justify-center">
                          <span className="text-4xl">{card.emoji}</span>
                        </div>
                      )}
                      {/* Rarity badge */}
                      <div className={cn(
                        'absolute top-2 left-2 px-2 py-0.5 rounded text-xs font-bold text-white',
                        rarityConf.bg
                      )}>
                        {t(rarityConf.labelKey)}
                      </div>
                    </div>

                    {/* Card info */}
                    <div className="p-2 space-y-1">
                      <h3 className="text-sm font-medium text-white truncate">{card.name}</h3>
                      <div className="flex items-center justify-between text-xs text-gray-400">
                        <span className="flex items-center gap-1">
                          <Swords className="w-3 h-3 text-orange-400" />
                          {card.attack}
                        </span>
                        <span className="flex items-center gap-1">
                          <Heart className="w-3 h-3 text-green-400" />
                          {card.current_hp}/{card.hp}
                        </span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-12 space-y-3">
              <Package className="w-12 h-12 text-gray-600 mx-auto" />
              <div>
                <p className="text-gray-400">
                  {searchQuery ? 'Карты не найдены' : 'Нет доступных карт для продажи'}
                </p>
                {!searchQuery && (
                  <p className="text-gray-500 text-sm mt-1">
                    Уберите карту из колоды чтобы продать
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Info */}
        {availableCards.length > 0 && (
          <p className="text-xs text-gray-500 text-center">
            Доступно карт: {availableCards.length}
          </p>
        )}
      </div>
    </Modal>
  );
}
