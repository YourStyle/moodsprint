'use client';

import { useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Sparkles, Star } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Card, Button } from '@/components/ui';
import { SparksBalance } from '@/components/sparks';
import { sparksService, SparksPack } from '@/services/sparks';
import { useAppStore } from '@/lib/store';
import { openInvoice, hapticFeedback, setupBackButton } from '@/lib/telegram';

export default function StorePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user } = useAppStore();

  // Setup native back button
  useEffect(() => {
    return setupBackButton(() => router.back());
  }, [router]);

  const { data: packsData, isLoading: packsLoading } = useQuery({
    queryKey: ['sparks', 'packs'],
    queryFn: () => sparksService.getPacks(),
    enabled: !!user,
  });

  const buyPackMutation = useMutation({
    mutationFn: (packId: string) => sparksService.buyPack(packId),
    onSuccess: async (result) => {
      if (result.success && result.data?.invoice_url) {
        hapticFeedback('light');
        const status = await openInvoice(result.data.invoice_url);
        if (status === 'paid') {
          hapticFeedback('success');
          // Refresh balance after purchase
          queryClient.invalidateQueries({ queryKey: ['sparks'] });
          queryClient.invalidateQueries({ queryKey: ['user'] });
        }
      }
    },
    onError: () => {
      hapticFeedback('error');
    },
  });

  const packs: SparksPack[] = packsData?.data?.packs || [];

  const handleBuyPack = (packId: string) => {
    if (buyPackMutation.isPending) return;
    buyPackMutation.mutate(packId);
  };

  return (
    <div className="p-4 space-y-4 pb-24">
      {/* Header */}
      <div className="flex flex-col items-center mb-4">
        <Sparkles className="w-8 h-8 text-amber-400 mb-1" />
        <h1 className="text-xl font-bold text-white">Магазин</h1>
      </div>

      {/* Current Balance */}
      <SparksBalance showBuyButton={false} />

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
                <div className="h-28 bg-gray-700/50 rounded-lg" />
              </Card>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {packs.map((pack) => (
              <Card
                key={pack.id}
                onClick={() => handleBuyPack(pack.id)}
                className={`
                  relative overflow-hidden cursor-pointer hover:border-amber-500/50 transition-all active:scale-[0.98]
                  ${pack.id === 'premium' ? 'border-amber-500/30 bg-gradient-to-br from-amber-500/10 to-yellow-500/10' : ''}
                  ${buyPackMutation.isPending ? 'opacity-50 pointer-events-none' : ''}
                `}
              >
                {pack.id === 'premium' && (
                  <div className="absolute top-0 right-0 bg-gradient-to-r from-amber-500 to-yellow-500 text-white text-xs px-2 py-0.5 rounded-bl-lg">
                    Популярный
                  </div>
                )}

                <div className="text-center py-3">
                  <div className="flex items-center justify-center gap-1 mb-2">
                    <Sparkles className="w-5 h-5 text-amber-400" />
                    <span className="text-2xl font-bold text-amber-400">
                      {pack.sparks.toLocaleString()}
                    </span>
                  </div>

                  <Button
                    size="sm"
                    className="w-full bg-gradient-to-r from-yellow-500 to-amber-500 hover:from-yellow-600 hover:to-amber-600 text-black font-medium"
                  >
                    <Star className="w-4 h-4 mr-1" />
                    {pack.price_stars} Stars
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Info about Sparks */}
      <Card className="bg-gray-800/50">
        <h3 className="font-medium text-white mb-2 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-amber-400" />
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
