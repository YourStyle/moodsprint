'use client';

import { useQuery } from '@tanstack/react-query';
import { Sparkles, Wallet, Star, ChevronLeft, Info, Copy, Check } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Card, Button } from '@/components/ui';
import { TonConnectButton } from '@/components/ui/TonConnectButton';
import { SparksBalance } from '@/components/sparks';
import { sparksService } from '@/services/sparks';
import { useAppStore } from '@/lib/store';

export default function StorePage() {
  const router = useRouter();
  const { user } = useAppStore();
  const [copiedMemo, setCopiedMemo] = useState(false);

  const { data: packsData, isLoading: packsLoading } = useQuery({
    queryKey: ['sparks', 'packs'],
    queryFn: () => sparksService.getPacks(),
    enabled: !!user,
  });

  const { data: depositData } = useQuery({
    queryKey: ['sparks', 'deposit-info'],
    queryFn: () => sparksService.getDepositInfo(),
    enabled: !!user,
  });

  const packs = packsData?.data?.packs || [];
  const depositInfo = depositData?.data;

  const handleCopyMemo = () => {
    if (depositInfo?.memo) {
      navigator.clipboard.writeText(depositInfo.memo);
      setCopiedMemo(true);
      setTimeout(() => setCopiedMemo(false), 2000);
    }
  };

  const formatTON = (amount: number) => {
    return amount.toFixed(2);
  };

  return (
    <div className="p-4 space-y-4 pb-24">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <button
          onClick={() => router.back()}
          className="p-2 rounded-xl bg-gray-800/80 border border-gray-700/50 text-gray-400 hover:text-white transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        <h1 className="text-xl font-bold text-white">Магазин Sparks</h1>
      </div>

      {/* Current Balance */}
      <SparksBalance showBuyButton={false} />

      {/* Wallet Connection */}
      <Card>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Wallet className="w-5 h-5 text-cyan-500" />
            <h2 className="font-semibold text-white">TON Кошелёк</h2>
          </div>
          <TonConnectButton />
        </div>
        <p className="text-sm text-gray-400">
          Подключите TON кошелёк для покупки Sparks за криптовалюту
        </p>
      </Card>

      {/* Deposit Info */}
      {depositInfo && (
        <Card className="bg-gradient-to-br from-cyan-500/10 to-blue-500/10 border-cyan-500/20">
          <div className="flex items-start gap-2 mb-3">
            <Info className="w-5 h-5 text-cyan-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-medium text-white mb-1">Как пополнить</h3>
              <p className="text-sm text-gray-400">{depositInfo.instructions}</p>
            </div>
          </div>

          <div className="space-y-2 p-3 bg-gray-800/50 rounded-xl">
            <div>
              <p className="text-xs text-gray-500 mb-1">Адрес для пополнения:</p>
              <p className="text-sm font-mono text-cyan-400 break-all">
                {depositInfo.deposit_address}
              </p>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500 mb-1">Ваш ID (укажите в комментарии):</p>
                <p className="text-sm font-mono text-white">{depositInfo.memo}</p>
              </div>
              <button
                onClick={handleCopyMemo}
                className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 transition-colors"
              >
                {copiedMemo ? (
                  <Check className="w-4 h-4 text-green-400" />
                ) : (
                  <Copy className="w-4 h-4 text-gray-400" />
                )}
              </button>
            </div>
          </div>
        </Card>
      )}

      {/* Sparks Packs */}
      <div>
        <h2 className="font-semibold text-white mb-3 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-amber-400" />
          Наборы Sparks
        </h2>

        {packsLoading ? (
          <div className="grid grid-cols-2 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <Card key={i} className="animate-pulse">
                <div className="h-20 bg-gray-700/50 rounded-lg" />
              </Card>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {packs.map((pack) => (
              <Card
                key={pack.id}
                className={`
                  relative overflow-hidden cursor-pointer hover:border-amber-500/50 transition-colors
                  ${pack.id === 'premium' ? 'border-amber-500/30 bg-gradient-to-br from-amber-500/10 to-yellow-500/10' : ''}
                `}
              >
                {pack.id === 'premium' && (
                  <div className="absolute top-0 right-0 bg-gradient-to-r from-amber-500 to-yellow-500 text-white text-xs px-2 py-0.5 rounded-bl-lg">
                    Популярный
                  </div>
                )}

                <div className="text-center py-2">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <Sparkles className="w-5 h-5 text-amber-400" />
                    <span className="text-2xl font-bold text-amber-400">
                      {pack.sparks.toLocaleString()}
                    </span>
                  </div>

                  <div className="space-y-1 mt-3">
                    <div className="flex items-center justify-center gap-1 text-sm">
                      <Star className="w-4 h-4 text-yellow-400" />
                      <span className="text-gray-300">{pack.price_stars} Stars</span>
                    </div>
                    <div className="text-xs text-gray-500">
                      или {formatTON(pack.price_ton)} TON
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Info about Sparks */}
      <Card className="bg-gray-800/50">
        <h3 className="font-medium text-white mb-2 flex items-center gap-2">
          <Info className="w-4 h-4 text-gray-400" />
          Что такое Sparks?
        </h3>
        <ul className="text-sm text-gray-400 space-y-1">
          <li>• Внутренняя валюта MoodSprint</li>
          <li>• Покупайте карточки на маркетплейсе</li>
          <li>• Получайте за продажу карточек</li>
          <li>• Зарабатывайте за прохождение кампании</li>
        </ul>
      </Card>
    </div>
  );
}
