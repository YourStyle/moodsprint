'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import {
  Store,
  Sparkles,
  Filter,
  Search,
  Heart,
  Swords,
  TrendingUp,
  TrendingDown,
  Clock,
  Wallet,
  ShoppingCart,
  Tag,
  X,
  Loader2,
  HelpCircle,
  Plus,
} from 'lucide-react';
import { Card, Button } from '@/components/ui';
import { DeckCard } from '@/components/cards';
import { SelectCardToSellModal, SellCardModal } from '@/components/marketplace';
import { marketplaceService } from '@/services';
import type { Card as CardType } from '@/services/cards';
import { useAppStore } from '@/lib/store';
import { hapticFeedback, showBackButton, hideBackButton, showTelegramAlert } from '@/lib/telegram';
import { cn } from '@/lib/utils';
import type { MarketListing } from '@/services/marketplace';

type Tab = 'browse' | 'my-listings' | 'balance';
type SortOption = 'newest' | 'price_low' | 'price_high';

const RARITY_COLORS: Record<string, string> = {
  common: 'bg-slate-600 text-white',
  uncommon: 'bg-emerald-600 text-white',
  rare: 'bg-blue-600 text-white',
  epic: 'bg-purple-600 text-white',
  legendary: 'bg-gradient-to-r from-amber-500 to-orange-500 text-white',
};

const RARITY_LABELS: Record<string, string> = {
  common: 'Обычная',
  uncommon: 'Необычная',
  rare: 'Редкая',
  epic: 'Эпическая',
  legendary: 'Легендарная',
};

// Helper to get price from listing (supports both price and price_stars)
const getListingPrice = (listing: MarketListing): number => {
  return listing.price || listing.price_stars || 0;
};

export default function MarketplacePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user } = useAppStore();

  const [activeTab, setActiveTab] = useState<Tab>('browse');
  const [sortBy, setSortBy] = useState<SortOption>('newest');
  const [rarityFilter, setRarityFilter] = useState<string | null>(null);
  const [selectedListing, setSelectedListing] = useState<MarketListing | null>(null);
  const [showSelectCardModal, setShowSelectCardModal] = useState(false);
  const [cardToSell, setCardToSell] = useState<CardType | null>(null);

  useEffect(() => {
    showBackButton(() => router.back());
    return () => hideBackButton();
  }, [router]);

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

  // Purchase mutation
  const purchaseMutation = useMutation({
    mutationFn: (listingId: number) => marketplaceService.purchaseWithSparks(listingId),
    onSuccess: (result) => {
      if (result.success) {
        hapticFeedback('success');
        showTelegramAlert(`Покупка завершена! Карта "${result.data?.card?.name}" добавлена в коллекцию.`);
        setSelectedListing(null);
        queryClient.invalidateQueries({ queryKey: ['marketplace'] });
        queryClient.invalidateQueries({ queryKey: ['cards'] });
        queryClient.invalidateQueries({ queryKey: ['sparks'] });
        queryClient.invalidateQueries({ queryKey: ['user'] });
      } else {
        hapticFeedback('error');
        showTelegramAlert(result.error?.message || 'Ошибка при покупке');
      }
    },
    onError: () => {
      hapticFeedback('error');
      showTelegramAlert('Произошла ошибка');
    },
  });

  const sparks = balanceData?.data?.sparks ?? user?.sparks ?? 0;

  const handlePurchase = (listing: MarketListing) => {
    const price = getListingPrice(listing);
    if (sparks < price) {
      showTelegramAlert(`Недостаточно Sparks. Нужно: ${price}, у вас: ${sparks}`);
      return;
    }
    purchaseMutation.mutate(listing.id);
  };

  return (
    <div className="p-4 pb-4">
      {/* Header */}
      <div className="text-center mb-4">
        <Store className="w-10 h-10 text-amber-500 mx-auto mb-2" />
        <h1 className="text-2xl font-bold text-white">Маркетплейс</h1>
        <p className="text-sm text-gray-400">Покупай и продавай карты за Sparks</p>
        <div className="flex items-center justify-center gap-1.5 bg-amber-500/20 px-3 py-1.5 rounded-full mt-3 w-fit mx-auto">
          <Sparkles className="w-4 h-4 text-amber-400" />
          <span className="text-amber-400 font-medium">{sparks.toLocaleString()}</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-gray-800 rounded-xl mb-4">
        {[
          { id: 'browse', label: 'Карты', icon: ShoppingCart },
          { id: 'my-listings', label: 'Мои', icon: Tag },
          { id: 'balance', label: 'История', icon: Wallet },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id as Tab)}
            className={cn(
              'flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg text-sm font-medium transition-colors',
              activeTab === id
                ? 'bg-amber-600 text-white'
                : 'text-gray-400 hover:text-white'
            )}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Browse Tab */}
      {activeTab === 'browse' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex gap-2">
            <div className="flex-1 flex gap-2 overflow-x-auto pb-1">
              <button
                onClick={() => setRarityFilter(null)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors',
                  !rarityFilter
                    ? 'bg-amber-600 text-white'
                    : 'bg-gray-800 text-gray-400'
                )}
              >
                Все
              </button>
              {Object.entries(RARITY_LABELS).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setRarityFilter(key)}
                  className={cn(
                    'px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors',
                    rarityFilter === key
                      ? 'bg-amber-600 text-white'
                      : 'bg-gray-800 text-gray-400'
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
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
                  'flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition-colors',
                  sortBy === id
                    ? 'bg-gray-700 text-white'
                    : 'bg-gray-800/50 text-gray-400'
                )}
              >
                <Icon className="w-3.5 h-3.5" />
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
                      'absolute top-2 left-2 px-2 py-0.5 rounded text-xs font-bold shadow-md',
                      RARITY_COLORS[listing.card.rarity]
                    )}>
                      {RARITY_LABELS[listing.card.rarity]}
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
                        {getListingPrice(listing)}
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <div className="text-center text-gray-400 py-8">
              Нет карт на продаже
            </div>
          )}
        </div>
      )}

      {/* My Listings Tab */}
      {activeTab === 'my-listings' && (
        <div className="space-y-4">
          {/* Sell Card Button */}
          <Button
            onClick={() => setShowSelectCardModal(true)}
            className="w-full bg-gradient-to-r from-amber-500 to-orange-500"
          >
            <Tag className="w-4 h-4 mr-2" />
            Продать карту
          </Button>

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
                        {getListingPrice(listing)}
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
      {activeTab === 'balance' && (
        <div className="space-y-4">
          {/* Balance Card */}
          <Card className="bg-gradient-to-br from-amber-900/30 to-yellow-900/30 border-amber-500/30">
            <div className="p-4 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Баланс Sparks</span>
                <div className="flex items-center gap-2 text-2xl font-bold text-amber-400">
                  <Sparkles className="w-6 h-6" />
                  {sparks.toLocaleString()}
                </div>
              </div>
              <Button
                variant="secondary"
                size="sm"
                className="w-full"
                onClick={() => router.push('/store')}
              >
                <Plus className="w-4 h-4 mr-1" />
                Купить Sparks
              </Button>
            </div>
          </Card>

          {/* How to get Sparks */}
          <Card className="bg-gray-800/50 border-gray-700/50">
            <div className="p-4 space-y-3">
              <div className="flex items-center gap-2">
                <HelpCircle className="w-5 h-5 text-amber-400" />
                <h3 className="font-medium text-white">Как получить Sparks?</h3>
              </div>
              <ul className="space-y-2 text-sm text-gray-400">
                <li className="flex items-start gap-2">
                  <span className="text-amber-400">1.</span>
                  <span>Продавайте карты другим игрокам на маркетплейсе</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-400">2.</span>
                  <span>Покупайте Sparks за Telegram Stars в магазине</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-400">3.</span>
                  <span>Проходите кампанию и побеждайте монстров</span>
                </li>
              </ul>
            </div>
          </Card>

          {/* Transactions */}
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
                        'font-bold flex items-center gap-1',
                        tx.amount > 0 ? 'text-green-400' : 'text-red-400'
                      )}>
                        {tx.amount > 0 ? '+' : ''}{tx.amount}
                        <Sparkles className="w-3.5 h-3.5" />
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
                <div className={cn('px-2 py-0.5 rounded text-sm font-medium', RARITY_COLORS[selectedListing.card.rarity])}>
                  {RARITY_LABELS[selectedListing.card.rarity]}
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
                  {getListingPrice(selectedListing)}
                </div>
              </div>

              {sparks < getListingPrice(selectedListing) && (
                <div className="text-center text-red-400 text-sm">
                  Недостаточно Sparks (у вас: {sparks})
                </div>
              )}

              <Button
                className="w-full bg-gradient-to-r from-amber-500 to-orange-500"
                onClick={() => handlePurchase(selectedListing)}
                disabled={purchaseMutation.isPending || sparks < getListingPrice(selectedListing)}
              >
                {purchaseMutation.isPending ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <ShoppingCart className="w-4 h-4 mr-2" />
                )}
                {purchaseMutation.isPending ? 'Покупка...' : 'Купить'}
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* Select Card to Sell Modal */}
      <SelectCardToSellModal
        isOpen={showSelectCardModal}
        onClose={() => setShowSelectCardModal(false)}
        onSelectCard={(card) => {
          setCardToSell(card);
        }}
      />

      {/* Sell Card Modal */}
      <SellCardModal
        isOpen={!!cardToSell}
        onClose={() => setCardToSell(null)}
        card={cardToSell ? {
          id: cardToSell.id,
          name: cardToSell.name,
          emoji: cardToSell.emoji,
          imageUrl: cardToSell.image_url || undefined,
          rarity: cardToSell.rarity,
          attack: cardToSell.attack,
          hp: cardToSell.hp,
        } : null}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['marketplace'] });
        }}
      />
    </div>
  );
}
