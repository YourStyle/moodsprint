'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { DollarSign, Star, Loader2, AlertCircle } from 'lucide-react';
import { Modal, Button } from '@/components/ui';
import { marketplaceService } from '@/services';
import { hapticFeedback } from '@/lib/telegram';
import { cn } from '@/lib/utils';

interface CardInfo {
  id: number;
  name: string;
  emoji?: string;
  imageUrl?: string;
  rarity: string;
  attack: number;
  hp: number;
}

interface SellCardModalProps {
  isOpen: boolean;
  onClose: () => void;
  card: CardInfo | null;
  onSuccess?: () => void;
}

const rarityConfig: Record<string, { min: number; suggested: number; label: string; color: string }> = {
  common: { min: 1, suggested: 5, label: 'Обычная', color: 'text-slate-400' },
  uncommon: { min: 3, suggested: 10, label: 'Необычная', color: 'text-emerald-400' },
  rare: { min: 10, suggested: 25, label: 'Редкая', color: 'text-blue-400' },
  epic: { min: 25, suggested: 50, label: 'Эпическая', color: 'text-purple-400' },
  legendary: { min: 50, suggested: 100, label: 'Легендарная', color: 'text-amber-400' },
};

export function SellCardModal({ isOpen, onClose, card, onSuccess }: SellCardModalProps) {
  const queryClient = useQueryClient();

  const [price, setPrice] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const config = card ? rarityConfig[card.rarity] || rarityConfig.common : rarityConfig.common;

  const createListingMutation = useMutation({
    mutationFn: () => marketplaceService.createListing({
      card_id: card!.id,
      price_stars: parseInt(price, 10),
    }),
    onSuccess: (result) => {
      if (result.success) {
        hapticFeedback('success');
        queryClient.invalidateQueries({ queryKey: ['marketplace'] });
        queryClient.invalidateQueries({ queryKey: ['user-cards'] });
        queryClient.invalidateQueries({ queryKey: ['deck'] });
        resetForm();
        onClose();
        onSuccess?.();
      } else {
        setError(result.error?.message || 'Ошибка выставления карты');
        hapticFeedback('error');
      }
    },
    onError: () => {
      setError('Ошибка выставления карты');
      hapticFeedback('error');
    },
  });

  const resetForm = () => {
    setPrice('');
    setError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const priceNum = parseInt(price, 10);

    if (!price || isNaN(priceNum)) {
      setError('Введите цену');
      return;
    }

    if (priceNum < config.min) {
      setError(`Минимальная цена для ${config.label.toLowerCase()} карты: ${config.min} ⭐`);
      return;
    }

    if (priceNum > 10000) {
      setError('Максимальная цена: 10,000 ⭐');
      return;
    }

    createListingMutation.mutate();
  };

  const handleQuickPrice = (value: number) => {
    setPrice(value.toString());
    setError(null);
  };

  if (!card) return null;

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Продать карту">
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Card Preview */}
        <div className="flex items-center gap-4 bg-gray-800/50 rounded-xl p-4">
          <div className="w-16 h-16 rounded-lg overflow-hidden border border-gray-600">
            {card.imageUrl ? (
              <img
                src={card.imageUrl}
                alt={card.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-700 to-gray-800">
                <span className="text-2xl">{card.emoji || '🎴'}</span>
              </div>
            )}
          </div>
          <div className="flex-1">
            <h3 className="font-bold text-white">{card.name}</h3>
            <p className={cn('text-sm font-medium', config.color)}>{config.label}</p>
            <div className="flex items-center gap-3 text-xs text-gray-400 mt-1">
              <span>⚔️ {card.attack}</span>
              <span>❤️ {card.hp}</span>
            </div>
          </div>
        </div>

        {/* Price Input */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Цена в Telegram Stars
          </label>
          <div className="relative">
            <Star className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-amber-400" />
            <input
              type="number"
              value={price}
              onChange={(e) => {
                setPrice(e.target.value);
                setError(null);
              }}
              placeholder={`Мин. ${config.min}`}
              min={config.min}
              max={10000}
              className="w-full bg-gray-800/50 border border-gray-700/50 rounded-xl py-3 pl-11 pr-4 text-white text-lg placeholder-gray-500 focus:outline-none focus:border-amber-500 transition-colors"
            />
          </div>
        </div>

        {/* Quick Price Buttons */}
        <div>
          <label className="block text-xs text-gray-400 mb-2">Быстрый выбор</label>
          <div className="flex gap-2">
            {[config.min, config.suggested, config.suggested * 2].map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => handleQuickPrice(value)}
                className={cn(
                  'flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors',
                  price === value.toString()
                    ? 'bg-amber-500/30 text-amber-300 border border-amber-500/50'
                    : 'bg-gray-700/50 text-gray-300 hover:bg-gray-700 border border-transparent'
                )}
              >
                {value} ⭐
              </button>
            ))}
          </div>
        </div>

        {/* Commission Info */}
        <div className="bg-gray-700/30 rounded-lg p-3 text-sm">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
            <div className="text-gray-400">
              <p>Комиссия маркетплейса: <span className="text-white">10%</span></p>
              {price && !isNaN(parseInt(price, 10)) && (
                <p className="mt-1">
                  Вы получите: <span className="text-amber-400 font-medium">
                    {Math.floor(parseInt(price, 10) * 0.9)} ⭐
                  </span>
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="text-red-400 text-sm text-center bg-red-500/10 rounded-lg py-2 px-3">
            {error}
          </div>
        )}

        {/* Submit button */}
        <Button
          type="submit"
          disabled={createListingMutation.isPending || !price}
          className="w-full bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600"
        >
          {createListingMutation.isPending ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Выставление...
            </>
          ) : (
            <>
              <DollarSign className="w-4 h-4 mr-2" />
              Выставить на продажу
            </>
          )}
        </Button>
      </form>
    </Modal>
  );
}
