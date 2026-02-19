'use client';

import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Sparkles, Star, Palette, Lock, Check } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Card, Button, ScrollBackdrop } from '@/components/ui';
import { SparksBalance } from '@/components/sparks';
import { sparksService, SparksPack } from '@/services/sparks';
import { cosmeticsService, CosmeticItem } from '@/services/cosmetics';
import { useAppStore } from '@/lib/store';
import { useLanguage } from '@/lib/i18n';
import { openInvoice, hapticFeedback, setupBackButton } from '@/lib/telegram';

type CosmeticTab = 'card_frame' | 'profile_frame';

export default function StorePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, isTelegramEnvironment } = useAppStore();
  const { t, language } = useLanguage();
  const [cosmeticTab, setCosmeticTab] = useState<CosmeticTab>('card_frame');

  // Redirect to home if not in Telegram environment (store requires Telegram Stars)
  useEffect(() => {
    if (!isTelegramEnvironment) {
      router.replace('/');
    }
  }, [isTelegramEnvironment, router]);

  // Setup native back button
  useEffect(() => {
    return setupBackButton(() => router.back());
  }, [router]);

  const { data: packsData, isLoading: packsLoading } = useQuery({
    queryKey: ['sparks', 'packs'],
    queryFn: () => sparksService.getPacks(),
    enabled: !!user,
  });

  const { data: cosmeticsData, isLoading: cosmeticsLoading } = useQuery({
    queryKey: ['cosmetics', 'catalog', language],
    queryFn: () => cosmeticsService.getCatalog(language),
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
          // Wait for backend to process payment, then refresh balance
          await new Promise((resolve) => setTimeout(resolve, 1000));
          await queryClient.refetchQueries({ queryKey: ['sparks', 'balance'] });
          queryClient.invalidateQueries({ queryKey: ['user'] });
        }
      }
    },
    onError: () => {
      hapticFeedback('error');
    },
  });

  const buyCosmeticMutation = useMutation({
    mutationFn: (cosmeticId: string) => cosmeticsService.buy(cosmeticId),
    onSuccess: (result) => {
      if (result.success) {
        hapticFeedback('success');
        queryClient.invalidateQueries({ queryKey: ['cosmetics'] });
        queryClient.invalidateQueries({ queryKey: ['sparks', 'balance'] });
        queryClient.invalidateQueries({ queryKey: ['onboarding', 'profile'] });
      }
    },
    onError: () => hapticFeedback('error'),
  });

  const equipCosmeticMutation = useMutation({
    mutationFn: (cosmeticId: string) => cosmeticsService.equip(cosmeticId),
    onSuccess: (result) => {
      if (result.success) {
        hapticFeedback('light');
        queryClient.invalidateQueries({ queryKey: ['cosmetics'] });
        queryClient.invalidateQueries({ queryKey: ['onboarding', 'profile'] });
      }
    },
    onError: () => hapticFeedback('error'),
  });

  const unequipCosmeticMutation = useMutation({
    mutationFn: (type: 'card_frame' | 'profile_frame') => cosmeticsService.unequip(type),
    onSuccess: (result) => {
      if (result.success) {
        hapticFeedback('light');
        queryClient.invalidateQueries({ queryKey: ['cosmetics'] });
        queryClient.invalidateQueries({ queryKey: ['onboarding', 'profile'] });
      }
    },
    onError: () => hapticFeedback('error'),
  });

  const packs: SparksPack[] = packsData?.data?.packs || [];
  const allCosmetics: CosmeticItem[] = cosmeticsData?.data?.cosmetics || [];
  const filteredCosmetics = allCosmetics.filter((c) => c.type === cosmeticTab);

  const handleBuyPack = (packId: string) => {
    if (buyPackMutation.isPending) return;
    buyPackMutation.mutate(packId);
  };

  const isMutating = buyCosmeticMutation.isPending || equipCosmeticMutation.isPending || unequipCosmeticMutation.isPending;

  const renderCosmeticAction = (item: CosmeticItem) => {
    const levelTooLow = (user?.level || 0) < item.min_level;

    if (levelTooLow && !item.is_owned) {
      return (
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <Lock className="w-3 h-3" />
          {t('levelRequired').replace('{level}', String(item.min_level))}
        </div>
      );
    }

    if (item.is_equipped) {
      return (
        <Button
          size="sm"
          onClick={() => unequipCosmeticMutation.mutate(item.type)}
          disabled={isMutating}
          className="w-full bg-green-600/20 border border-green-500/30 text-green-400 text-xs"
        >
          <Check className="w-3 h-3 mr-1" />
          {t('equipped')}
        </Button>
      );
    }

    if (item.is_owned) {
      return (
        <Button
          size="sm"
          onClick={() => equipCosmeticMutation.mutate(item.id)}
          disabled={isMutating}
          className="w-full bg-purple-600 hover:bg-purple-700 text-white text-xs"
        >
          {t('equipCosmetic')}
        </Button>
      );
    }

    return (
      <Button
        size="sm"
        onClick={() => buyCosmeticMutation.mutate(item.id)}
        disabled={isMutating}
        className="w-full bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-black text-xs font-medium"
      >
        <Sparkles className="w-3 h-3 mr-1" />
        {item.price_sparks}
      </Button>
    );
  };

  return (
    <div className="p-4 space-y-4 pb-24">
      <ScrollBackdrop />
      {/* Header */}
      <div className="flex flex-col items-center mb-4">
        <Sparkles className="w-8 h-8 text-amber-400 mb-1" />
        <h1 className="text-xl font-bold text-white">{t('store')}</h1>
      </div>

      {/* Current Balance */}
      <SparksBalance showBuyButton={false} />

      {/* Sparks Packs */}
      <div>
        <h2 className="font-semibold text-white mb-3 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-amber-400" />
          {t('sparksPacks')}
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
                    {t('popular')}
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

      {/* Cosmetics Section */}
      <div>
        <h2 className="font-semibold text-white mb-3 flex items-center gap-2">
          <Palette className="w-5 h-5 text-purple-400" />
          {t('cosmetics')}
        </h2>

        {/* Tabs */}
        <div className="flex gap-2 mb-3">
          {(['card_frame', 'profile_frame'] as CosmeticTab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setCosmeticTab(tab)}
              className={`flex-1 py-2 px-3 rounded-xl text-sm font-medium transition-all ${
                cosmeticTab === tab
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-800/60 text-gray-400 hover:text-white'
              }`}
            >
              {tab === 'card_frame' ? t('cardFrames') : t('profileFrames')}
            </button>
          ))}
        </div>

        {/* Items Grid */}
        {cosmeticsLoading ? (
          <div className="grid grid-cols-2 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <Card key={i} className="animate-pulse">
                <div className="h-36 bg-gray-700/50 rounded-lg" />
              </Card>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {filteredCosmetics.map((item) => (
              <Card
                key={item.id}
                className={`relative overflow-hidden ${
                  item.is_equipped ? 'border-purple-500/50' : ''
                }`}
              >
                {/* Preview */}
                <div
                  className="w-full h-16 rounded-lg mb-2"
                  style={{ background: item.preview_gradient }}
                />

                {/* Name & description */}
                <h3 className="text-sm font-semibold text-white truncate">{item.name}</h3>
                <p className="text-xs text-gray-400 line-clamp-2 mb-2 min-h-[2rem]">
                  {item.description}
                </p>

                {/* Action */}
                {renderCosmeticAction(item)}
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Info about Sparks */}
      <Card className="bg-gray-800/50">
        <h3 className="font-medium text-white mb-2 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-amber-400" />
          {t('whatAreSparks')}
        </h3>
        <ul className="text-sm text-gray-400 space-y-1">
          <li>• {t('sparksDesc1')}</li>
          <li>• {t('sparksDesc2')}</li>
          <li>• {t('sparksDesc3')}</li>
          <li>• {t('sparksDesc4')}</li>
        </ul>
      </Card>
    </div>
  );
}
