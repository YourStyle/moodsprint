'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Store,
  Sparkles,
  Heart,
  Swords,
  TrendingUp,
  TrendingDown,
  Clock,
  Wallet,
  ShoppingCart,
  Tag,
  X,
} from 'lucide-react';
import { Card, Button } from '@/components/ui';
import { marketplaceService } from '@/services';
import { useAppStore } from '@/lib/store';
import { hapticFeedback } from '@/lib/telegram';
import { cn } from '@/lib/utils';
import { useTranslation } from '@/lib/i18n';
import type { MarketListing } from '@/services/marketplace';

type MarketTab = 'browse' | 'my-listings' | 'balance';
type SortOption = 'newest' | 'price_low' | 'price_high';

const RARITY_COLORS: Record<string, string> = {
  common: 'text-gray-400 border-gray-500',
  uncommon: 'text-green-400 border-green-500',
  rare: 'text-blue-400 border-blue-500',
  epic: 'text-purple-400 border-purple-500',
  legendary: 'text-amber-400 border-amber-500',
};

const RARITY_KEYS: Record<string, 'rarityCommon' | 'rarityUncommon' | 'rarityRare' | 'rarityEpic' | 'rarityLegendary'> = {
  common: 'rarityCommon',
  uncommon: 'rarityUncommon',
  rare: 'rarityRare',
  epic: 'rarityEpic',
  legendary: 'rarityLegendary',
};

export function MarketplaceContent() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { user } = useAppStore();

  const [activeTab, setActiveTab] = useState<MarketTab>('browse');
  const [sortBy, setSortBy] = useState<SortOption>('newest');
  const [rarityFilter, setRarityFilter] = useState<string | null>(null);
  const [selectedListing, setSelectedListing] = useState<MarketListing | null>(null);

  // Browse listings
  const { data: listingsData, isLoading } = useQuery({
    queryKey: ['marketplace', 'browse', sortBy, rarityFilter],
    queryFn: () => marketplaceService.browseListings({
      sort_by: sortBy,
      rarity: rarityFilter || undefined,
    }),
    enabled: activeTab === 'browse',
  });

  // My listings
  const { data: myListingsData } = useQuery({
    queryKey: ['marketplace', 'my-listings'],
    queryFn: () => marketplaceService.getMyListings(),
    enabled: activeTab === 'my-listings',
  });

  // Balance
  const { data: balanceData } = useQuery({
    queryKey: ['marketplace', 'balance'],
    queryFn: () => marketplaceService.getBalance(),
  });

  // Transactions
  const { data: transactionsData } = useQuery({
    queryKey: ['marketplace', 'transactions'],
    queryFn: () => marketplaceService.getTransactions(),
    enabled: activeTab === 'balance',
  });

  // Cancel listing mutation
  const cancelListingMutation = useMutation({
    mutationFn: (listingId: number) => marketplaceService.cancelListing(listingId),
    onSuccess: () => {
      hapticFeedback('success');
      queryClient.invalidateQueries({ queryKey: ['marketplace'] });
    },
  });

  const balance = balanceData?.data;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="text-center pb-2">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 mb-2">
          <Store className="w-7 h-7 text-amber-400" />
        </div>
        <h2 className="text-xl font-bold text-white">Маркетплейс</h2>
        <p className="text-sm text-gray-400">Торгуйте картами за Sparks</p>
        {balance && (
          <div className="inline-flex items-center gap-1.5 bg-amber-500/20 px-3 py-1.5 rounded-full mt-2">
            <Sparkles className="w-4 h-4 text-amber-400" />
            <span className="text-amber-400 font-medium">{balance.sparks}</span>
          </div>
        )}
      </div>

      {/* Sub-tabs */}
      <div className="flex gap-1 bg-gray-700/50 rounded-lg p-1">
        {[
          { id: 'browse', label: 'Карты', icon: ShoppingCart },
          { id: 'my-listings', label: 'Мои', icon: Tag },
          { id: 'balance', label: 'Баланс', icon: Wallet },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id as MarketTab)}
            className={cn(
              'flex-1 flex items-center justify-center gap-1.5 py-2 px-2 rounded-md text-xs font-medium transition-colors',
              activeTab === id
                ? 'bg-amber-600 text-white'
                : 'text-gray-400 hover:text-white'
            )}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Browse Tab */}
      {activeTab === 'browse' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex gap-2 overflow-x-auto pb-1">
            <button
              onClick={() => setRarityFilter(null)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors',
                !rarityFilter
                  ? 'bg-amber-600 text-white'
                  : 'bg-gray-800 text-gray-400'
              )}
            >
              {t('all')}
            </button>
            {Object.entries(RARITY_KEYS).map(([key, labelKey]) => (
              <button
                key={key}
                onClick={() => setRarityFilter(key)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors',
                  rarityFilter === key
                    ? 'bg-amber-600 text-white'
                    : 'bg-gray-800 text-gray-400'
                )}
              >
                {t(labelKey)}
              </button>
            ))}
          </div>

          {/* Sort */}
          <div className="flex gap-2">
            {[
              { id: 'newest', label: 'Новые', icon: Clock },
              { id: 'price_low', label: 'Дешевле', icon: TrendingDown },
              { id: 'price_high', label: 'Дороже', icon: TrendingUp },
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setSortBy(id as SortOption)}
                className={cn(
                  'flex items-center gap-1 px-2 py-1 rounded-lg text-xs transition-colors',
                  sortBy === id
                    ? 'bg-gray-700 text-white'
                    : 'bg-gray-800/50 text-gray-400'
                )}
              >
                <Icon className="w-3 h-3" />
                {label}
              </button>
            ))}
          </div>

          {/* Listings Grid */}
          {isLoading ? (
            <div className="text-center text-gray-400 py-8">Загрузка...</div>
          ) : listingsData?.data?.listings?.length ? (
            <div className="grid grid-cols-2 gap-3">
              {listingsData.data.listings.map((listing) => (
                <Card
                  key={listing.id}
                  className="bg-gray-800/50 border-gray-700/50 overflow-hidden cursor-pointer hover:border-amber-500/50 transition-colors"
                  onClick={() => setSelectedListing(listing)}
                >
                  <div className="aspect-[3/4] relative">
                    {listing.card.image_url ? (
                      <img
                        src={listing.card.image_url}
                        alt={listing.card.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-b from-gray-700 to-gray-800 flex items-center justify-center">
                        <span className="text-4xl">{listing.card.emoji}</span>
                      </div>
                    )}
                    <div className={cn(
                      'absolute top-2 left-2 px-2 py-0.5 rounded text-xs font-bold',
                      RARITY_COLORS[listing.card.rarity]
                    )}>
                      {t(RARITY_KEYS[listing.card.rarity] || 'rarityCommon')}
                    </div>
                  </div>
                  <div className="p-2 space-y-1">
                    <h3 className="text-sm font-medium text-white truncate">{listing.card.name}</h3>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-xs text-gray-400">
                        <span className="flex items-center gap-0.5">
                          <Swords className="w-3 h-3 text-orange-400" />
                          {listing.card.attack}
                        </span>
                        <span className="flex items-center gap-0.5">
                          <Heart className="w-3 h-3 text-green-400" />
                          {listing.card.hp}
                        </span>
                      </div>
                      <div className="flex items-center gap-1 text-amber-400 font-bold">
                        <Sparkles className="w-3.5 h-3.5" />
                        {listing.price}
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="text-center py-8">
              <Store className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400">Нет карт на продаже</p>
            </Card>
          )}
        </div>
      )}

      {/* My Listings Tab */}
      {activeTab === 'my-listings' && (
        <div className="space-y-4">
          {myListingsData?.data?.listings?.length ? (
            <div className="grid grid-cols-2 gap-3">
              {myListingsData.data.listings.map((listing) => (
                <Card
                  key={listing.id}
                  className="bg-gray-800/50 border-gray-700/50 overflow-hidden"
                >
                  <div className="aspect-[3/4] relative">
                    {listing.card.image_url ? (
                      <img
                        src={listing.card.image_url}
                        alt={listing.card.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-b from-gray-700 to-gray-800 flex items-center justify-center">
                        <span className="text-4xl">{listing.card.emoji}</span>
                      </div>
                    )}
                  </div>
                  <div className="p-2 space-y-2">
                    <h3 className="text-sm font-medium text-white truncate">{listing.card.name}</h3>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1 text-amber-400 font-bold">
                        <Sparkles className="w-3.5 h-3.5" />
                        {listing.price}
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => cancelListingMutation.mutate(listing.id)}
                        disabled={cancelListingMutation.isPending}
                        className="text-red-400 text-xs"
                      >
                        Снять
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="bg-gray-800/50 border-gray-700/50">
              <div className="p-8 text-center space-y-3">
                <Tag className="w-12 h-12 text-gray-600 mx-auto" />
                <p className="text-gray-400">У вас нет карт на продаже</p>
                <p className="text-gray-500 text-sm">
                  Выставьте карту на продажу в разделе Колода
                </p>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Balance Tab */}
      {activeTab === 'balance' && balance && (
        <div className="space-y-4">
          <Card className="bg-gradient-to-br from-amber-900/30 to-yellow-900/30 border-amber-500/30">
            <div className="p-4 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Баланс Sparks</span>
                <div className="flex items-center gap-2 text-2xl font-bold text-amber-400">
                  <Sparkles className="w-6 h-6" />
                  {balance.sparks}
                </div>
              </div>
            </div>
          </Card>

          <div className="space-y-2">
            <h3 className="text-sm font-medium text-gray-400">История операций</h3>
            {transactionsData?.data?.transactions?.length ? (
              <div className="space-y-2">
                {transactionsData.data.transactions.map((tx) => (
                  <Card
                    key={tx.id}
                    className="bg-gray-800/50 border-gray-700/50"
                  >
                    <div className="p-3 flex items-center justify-between">
                      <div>
                        <div className="text-sm text-white">{tx.description || tx.type}</div>
                        <div className="text-xs text-gray-500">
                          {new Date(tx.created_at).toLocaleDateString('ru-RU')}
                        </div>
                      </div>
                      <div className={cn(
                        'font-bold',
                        tx.amount > 0 ? 'text-green-400' : 'text-red-400'
                      )}>
                        {tx.amount > 0 ? '+' : ''}{tx.amount}
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <p className="text-center text-gray-500 py-4">Нет операций</p>
            )}
          </div>
        </div>
      )}

      {/* Selected Listing Modal */}
      {selectedListing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <Card className="bg-gray-900 border-gray-700 w-full max-w-sm">
            <div className="p-4 space-y-4">
              <div className="flex justify-between items-start">
                <h3 className="text-lg font-bold text-white">{selectedListing.card.name}</h3>
                <button onClick={() => setSelectedListing(null)}>
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              </div>

              <div className="aspect-square relative rounded-xl overflow-hidden">
                {selectedListing.card.image_url ? (
                  <img
                    src={selectedListing.card.image_url}
                    alt={selectedListing.card.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full bg-gradient-to-b from-gray-700 to-gray-800 flex items-center justify-center">
                    <span className="text-6xl">{selectedListing.card.emoji}</span>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between">
                <div className={cn('text-sm font-medium', RARITY_COLORS[selectedListing.card.rarity])}>
                  {t(RARITY_KEYS[selectedListing.card.rarity] || 'rarityCommon')}
                </div>
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1 text-orange-400">
                    <Swords className="w-4 h-4" />
                    {selectedListing.card.attack}
                  </span>
                  <span className="flex items-center gap-1 text-green-400">
                    <Heart className="w-4 h-4" />
                    {selectedListing.card.hp}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between p-3 bg-amber-500/10 rounded-xl">
                <span className="text-gray-400">Цена</span>
                <div className="flex items-center gap-2 text-xl font-bold text-amber-400">
                  <Sparkles className="w-5 h-5" />
                  {selectedListing.price}
                </div>
              </div>

              <Button
                className="w-full bg-gradient-to-r from-amber-500 to-orange-500"
                onClick={() => {
                  hapticFeedback('medium');
                  // Purchase will be handled via marketplace page
                  setSelectedListing(null);
                }}
              >
                <ShoppingCart className="w-4 h-4 mr-2" />
                Купить за {selectedListing.price} ✨
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
