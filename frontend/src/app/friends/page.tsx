'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import {
  Users,
  UserPlus,
  ArrowLeftRight,
  Search,
  Check,
  X,
  Send,
  Clock,
  Inbox,
  SendHorizonal,
  Heart,
  Swords,
  AlertCircle,
  Share2,
  Gift,
} from 'lucide-react';
import { Card, Button, Progress } from '@/components/ui';
import { ReferralRewardModal } from '@/components/cards';
import { cardsService } from '@/services';
import { useAppStore } from '@/lib/store';
import { hapticFeedback, showBackButton, hideBackButton, shareInviteLink } from '@/lib/telegram';
import { cn } from '@/lib/utils';
import type { Card as CardType, Friend, FriendRequest, Trade, PendingReward } from '@/services/cards';

type Tab = 'friends' | 'requests' | 'trades';

const RARITY_COLORS: Record<string, string> = {
  common: '#9CA3AF',
  uncommon: '#22C55E',
  rare: '#3B82F6',
  epic: '#A855F7',
  legendary: '#F59E0B',
};

const RARITY_LABELS: Record<string, string> = {
  common: 'Обычная',
  uncommon: 'Необычная',
  rare: 'Редкая',
  epic: 'Эпическая',
  legendary: 'Легендарная',
};

export default function FriendsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user } = useAppStore();

  const [activeTab, setActiveTab] = useState<Tab>('friends');
  const [searchUsername, setSearchUsername] = useState('');
  const [selectedFriend, setSelectedFriend] = useState<Friend | null>(null);
  const [selectedMyCards, setSelectedMyCards] = useState<CardType[]>([]);
  const [selectedFriendCards, setSelectedFriendCards] = useState<CardType[]>([]);
  const [tradeMessage, setTradeMessage] = useState('');
  const [showTradeForm, setShowTradeForm] = useState(false);
  const [showReferralModal, setShowReferralModal] = useState(false);
  const [referralRewards, setReferralRewards] = useState<Array<{
    friendName?: string;
    friendId?: number;
    isReferrer: boolean;
    cards: Array<{
      id: number;
      name: string;
      description?: string;
      genre: string;
      rarity: string;
      hp: number;
      attack: number;
      emoji: string;
      image_url?: string | null;
    }>;
  }>>([]);

  // Refetch data on mount to ensure fresh data when navigating to this page
  useEffect(() => {
    if (user) {
      queryClient.invalidateQueries({ queryKey: ['friends'] });
      queryClient.invalidateQueries({ queryKey: ['trades'] });
    }
  }, [user, queryClient]);

  // Check for pending referral rewards when page loads
  const { data: pendingRewardsData } = useQuery({
    queryKey: ['cards', 'pending-rewards'],
    queryFn: () => cardsService.getPendingRewards(),
    enabled: !!user,
    staleTime: 0, // Always refetch
  });

  // Show referral modal if there are pending rewards
  useEffect(() => {
    if (pendingRewardsData?.data?.rewards && pendingRewardsData.data.rewards.length > 0) {
      const rewards = pendingRewardsData.data.rewards;
      const rewardsToShow = rewards
        .filter((r: PendingReward) => r.card)
        .map((r: PendingReward) => ({
          isReferrer: r.is_referrer,
          friendName: r.friend_name || undefined,
          friendId: r.friend_id,
          cards: r.card ? [{
            id: r.card.id,
            name: r.card.name,
            description: r.card.description || undefined,
            genre: r.card.genre,
            rarity: r.card.rarity,
            hp: r.card.hp,
            attack: r.card.attack,
            emoji: r.card.emoji,
            image_url: r.card.image_url,
          }] : [],
        }));

      if (rewardsToShow.length > 0) {
        setReferralRewards(rewardsToShow);
        setShowReferralModal(true);
      }
    }
  }, [pendingRewardsData]);

  const handleCloseReferralModal = async () => {
    setShowReferralModal(false);
    setReferralRewards([]);
    // Mark rewards as claimed
    await cardsService.claimPendingRewards();
    // Invalidate the count query to update the badge
    queryClient.invalidateQueries({ queryKey: ['cards', 'pending-rewards-count'] });
    queryClient.invalidateQueries({ queryKey: ['cards', 'pending-rewards'] });
  };

  // Queries
  const { data: friendsData, isLoading: friendsLoading } = useQuery({
    queryKey: ['friends'],
    queryFn: () => cardsService.getFriends(),
    enabled: !!user,
    refetchOnMount: 'always',
  });

  const { data: requestsData, isLoading: requestsLoading } = useQuery({
    queryKey: ['friends', 'requests'],
    queryFn: () => cardsService.getFriendRequests(),
    enabled: !!user,
    refetchOnMount: 'always',
  });

  const { data: tradesData, isLoading: tradesLoading } = useQuery({
    queryKey: ['trades'],
    queryFn: () => cardsService.getTrades(),
    enabled: !!user,
    refetchOnMount: 'always',
  });

  const { data: myCardsData } = useQuery({
    queryKey: ['cards'],
    queryFn: () => cardsService.getCards(),
    enabled: !!user && showTradeForm,
  });

  const { data: friendCardsData, isLoading: friendCardsLoading } = useQuery({
    queryKey: ['friends', selectedFriend?.friend_id, 'cards'],
    queryFn: () => cardsService.getFriendCards(selectedFriend!.friend_id),
    enabled: !!selectedFriend,
  });

  // Mutations
  const sendRequestMutation = useMutation({
    mutationFn: (username: string) => cardsService.sendFriendRequest(undefined, username),
    onSuccess: () => {
      hapticFeedback('success');
      setSearchUsername('');
      queryClient.invalidateQueries({ queryKey: ['friends'] });
    },
    onError: () => {
      hapticFeedback('error');
    },
  });

  const acceptRequestMutation = useMutation({
    mutationFn: (requestId: number) => cardsService.acceptFriendRequest(requestId),
    onSuccess: () => {
      hapticFeedback('success');
      queryClient.invalidateQueries({ queryKey: ['friends'] });
    },
  });

  const rejectRequestMutation = useMutation({
    mutationFn: (requestId: number) => cardsService.rejectFriendRequest(requestId),
    onSuccess: () => {
      hapticFeedback('light');
      queryClient.invalidateQueries({ queryKey: ['friends'] });
    },
  });

  const createTradeMutation = useMutation({
    mutationFn: () =>
      cardsService.createTrade(
        selectedFriend!.friend_id,
        selectedMyCards.map(c => c.id),
        selectedFriendCards.length > 0 ? selectedFriendCards.map(c => c.id) : undefined,
        tradeMessage || undefined
      ),
    onSuccess: () => {
      hapticFeedback('success');
      setShowTradeForm(false);
      setSelectedFriend(null);
      setSelectedMyCards([]);
      setSelectedFriendCards([]);
      setTradeMessage('');
      queryClient.invalidateQueries({ queryKey: ['trades'] });
    },
  });

  const acceptTradeMutation = useMutation({
    mutationFn: (tradeId: number) => cardsService.acceptTrade(tradeId),
    onSuccess: () => {
      hapticFeedback('success');
      queryClient.invalidateQueries({ queryKey: ['trades'] });
      queryClient.invalidateQueries({ queryKey: ['cards'] });
    },
  });

  const rejectTradeMutation = useMutation({
    mutationFn: (tradeId: number) => cardsService.rejectTrade(tradeId),
    onSuccess: () => {
      hapticFeedback('light');
      queryClient.invalidateQueries({ queryKey: ['trades'] });
    },
  });

  const cancelTradeMutation = useMutation({
    mutationFn: (tradeId: number) => cardsService.cancelTrade(tradeId),
    onSuccess: () => {
      hapticFeedback('light');
      queryClient.invalidateQueries({ queryKey: ['trades'] });
    },
  });

  const friends = friendsData?.data?.friends || [];
  const requests = requestsData?.data?.requests || [];
  const sentTrades = tradesData?.data?.sent || [];
  const receivedTrades = tradesData?.data?.received || [];
  const myCards = myCardsData?.data?.cards?.filter((c) => c.is_tradeable) || [];
  const friendCards = friendCardsData?.data?.cards || [];

  const pendingRequestsCount = requests.length;
  const pendingTradesCount = receivedTrades.filter((t) => t.status === 'pending').length;

  // Handle Telegram back button for trade form
  // Must be before conditional return to follow React hooks rules
  useEffect(() => {
    if (showTradeForm) {
      hideBackButton();
      showBackButton(() => {
        setShowTradeForm(false);
        setSelectedFriend(null);
        setSelectedMyCards([]);
        setSelectedFriendCards([]);
        setTradeMessage('');
      });
    } else {
      hideBackButton();
    }
    return () => {
      hideBackButton();
    };
  }, [showTradeForm]);

  if (!user) {
    return (
      <div className="p-4 text-center">
        <p className="text-gray-500">Войдите чтобы увидеть друзей</p>
      </div>
    );
  }

  const handleSendRequest = () => {
    if (searchUsername.trim()) {
      // Remove @ prefix if present
      const username = searchUsername.trim().replace(/^@/, '');
      sendRequestMutation.mutate(username);
    }
  };

  const handleStartTrade = (friend: Friend) => {
    setSelectedFriend(friend);
    setShowTradeForm(true);
    hapticFeedback('light');
  };

  const handleCloseTrade = () => {
    setShowTradeForm(false);
    setSelectedFriend(null);
    setSelectedMyCards([]);
    setSelectedFriendCards([]);
    setTradeMessage('');
  };

  const toggleMyCard = (card: CardType) => {
    setSelectedMyCards(prev =>
      prev.some(c => c.id === card.id)
        ? prev.filter(c => c.id !== card.id)
        : [...prev, card]
    );
    hapticFeedback('light');
  };

  const toggleFriendCard = (card: CardType) => {
    setSelectedFriendCards(prev =>
      prev.some(c => c.id === card.id)
        ? prev.filter(c => c.id !== card.id)
        : [...prev, card]
    );
    hapticFeedback('light');
  };

  const handleShareInvite = () => {
    if (!user) return;
    hapticFeedback('light');
    shareInviteLink(user.id, 'Присоединяйся к MoodSprint!');
  };

  const renderCardMini = (card: CardType | null, onClick?: () => void, isSelected?: boolean) => {
    if (!card) {
      return (
        <div
          onClick={onClick}
          className={cn(
            'w-full h-32 rounded-xl border-2 border-dashed flex flex-col items-center justify-center cursor-pointer transition-all',
            onClick ? 'border-gray-600 hover:border-purple-500 hover:bg-purple-500/10' : 'border-gray-700'
          )}
        >
          <span className="text-2xl text-gray-600 mb-1">+</span>
          <span className="text-xs text-gray-500">Выбрать карту</span>
        </div>
      );
    }

    const rarityColor = RARITY_COLORS[card.rarity] || '#9CA3AF';

    return (
      <div
        onClick={onClick}
        className={cn(
          'relative rounded-xl p-3 border transition-all',
          onClick && 'cursor-pointer hover:scale-[1.02]',
          isSelected && 'ring-2 ring-purple-500'
        )}
        style={{
          borderColor: rarityColor + '50',
          background: `linear-gradient(135deg, ${rarityColor}20, ${rarityColor}10)`,
        }}
      >
        <div
          className="absolute -top-2 left-2 px-2 py-0.5 rounded-full text-xs font-medium text-white"
          style={{ backgroundColor: rarityColor }}
        >
          {RARITY_LABELS[card.rarity]}
        </div>
        <div className="flex items-center gap-2 mt-2">
          <span className="text-2xl">{card.emoji}</span>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-medium text-white truncate">{card.name}</h4>
            <div className="flex items-center gap-2 text-xs">
              <span className="text-red-400 flex items-center gap-0.5">
                <Swords className="w-3 h-3" />
                {card.attack}
              </span>
              <span className="text-green-400 flex items-center gap-0.5">
                <Heart className="w-3 h-3" />
                {card.hp}
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Trade creation form
  if (showTradeForm && selectedFriend) {
    const isGiftMode = selectedFriendCards.length === 0;

    return (
      <div className="p-4 pb-4">
        <div className="text-center mb-6">
          {isGiftMode ? (
            <Gift className="w-10 h-10 text-pink-500 mx-auto mb-2" />
          ) : (
            <ArrowLeftRight className="w-10 h-10 text-purple-500 mx-auto mb-2" />
          )}
          <h1 className="text-xl font-bold text-white">
            {isGiftMode ? 'Подарить карты' : 'Предложить обмен'}
          </h1>
          <p className="text-sm text-gray-400">
            {selectedFriend.first_name || selectedFriend.username}
          </p>
        </div>

        {/* My cards selection */}
        <Card className="mb-4 overflow-visible">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-white">Ваши карты</h3>
            {selectedMyCards.length > 0 && (
              <span className="text-xs text-purple-400 font-medium">
                Выбрано: {selectedMyCards.length}
              </span>
            )}
          </div>
          <div className="flex flex-col gap-2 max-h-64 overflow-y-auto overflow-x-visible px-1 pt-2 pb-2">
            {myCards.length === 0 ? (
              <p className="text-center text-gray-500 py-4">
                Нет карт для обмена
              </p>
            ) : (
              myCards.map((card) => {
                const isSelected = selectedMyCards.some(c => c.id === card.id);
                return (
                  <div key={card.id}>
                    {renderCardMini(card, () => toggleMyCard(card), isSelected)}
                  </div>
                );
              })
            )}
          </div>
        </Card>

        {/* Friend's cards selection (optional for gifts) */}
        <Card className="mb-4 overflow-visible">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-medium text-white">Карты друга</h3>
              {selectedFriendCards.length > 0 && (
                <span className="text-xs text-purple-400 font-medium">
                  ({selectedFriendCards.length})
                </span>
              )}
            </div>
            <span className="text-xs text-gray-500 flex items-center gap-1">
              <Gift className="w-3 h-3" />
              не выбирай для подарка
            </span>
          </div>
          {friendCardsLoading ? (
            <div className="h-32 bg-gray-700 rounded-xl animate-pulse" />
          ) : (
            <div className="flex flex-col gap-2 max-h-64 overflow-y-auto overflow-x-visible px-1 pt-2 pb-2">
              {friendCards.length === 0 ? (
                <p className="text-center text-gray-500 py-4">
                  У друга нет карт для обмена
                </p>
              ) : (
                friendCards.map((card) => {
                  const isSelected = selectedFriendCards.some(c => c.id === card.id);
                  return (
                    <div key={card.id}>
                      {renderCardMini(card, () => toggleFriendCard(card), isSelected)}
                    </div>
                  );
                })
              )}
            </div>
          )}
        </Card>

        {/* Message */}
        <Card className="mb-4">
          <h3 className="text-sm font-medium text-white mb-2">Сообщение</h3>
          <textarea
            value={tradeMessage}
            onChange={(e) => setTradeMessage(e.target.value)}
            placeholder="Добавьте сообщение к обмену..."
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500 text-sm resize-none"
            rows={2}
          />
        </Card>

        {/* Submit */}
        <Button
          className={cn("w-full", isGiftMode && "bg-gradient-to-r from-pink-500 to-purple-500 hover:from-pink-600 hover:to-purple-600")}
          onClick={() => createTradeMutation.mutate()}
          disabled={selectedMyCards.length === 0}
          isLoading={createTradeMutation.isPending}
        >
          {isGiftMode ? (
            <>
              <Gift className="w-4 h-4 mr-1" />
              Подарить {selectedMyCards.length > 1 ? `(${selectedMyCards.length})` : ''}
            </>
          ) : (
            <>
              <Send className="w-4 h-4 mr-2" />
              Обмен {selectedMyCards.length}:{selectedFriendCards.length}
            </>
          )}
        </Button>
      </div>
    );
  }

  return (
    <div className="p-4 pb-4">
      {/* Header */}
      <div className="text-center mb-4">
        <Users className="w-10 h-10 text-purple-500 mx-auto mb-2" />
        <h1 className="text-2xl font-bold text-white">Друзья</h1>
        <p className="text-sm text-gray-400">Добавляй друзей и обменивайся картами</p>
        <Button
          size="sm"
          variant="secondary"
          className="mt-3"
          onClick={handleShareInvite}
        >
          <Share2 className="w-4 h-4 mr-2" />
          Пригласить друга
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 p-1 bg-gray-800 rounded-xl mb-4">
        <button
          onClick={() => setActiveTab('friends')}
          className={cn(
            'flex-1 py-2.5 px-3 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-1',
            activeTab === 'friends'
              ? 'bg-purple-500 text-white'
              : 'text-gray-400 hover:text-white'
          )}
        >
          <Users className="w-4 h-4" />
          Друзья
        </button>
        <button
          onClick={() => setActiveTab('requests')}
          className={cn(
            'flex-1 py-2.5 px-3 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-1 relative',
            activeTab === 'requests'
              ? 'bg-purple-500 text-white'
              : 'text-gray-400 hover:text-white'
          )}
        >
          <UserPlus className="w-4 h-4" />
          Запросы
          {pendingRequestsCount > 0 && (
            <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full text-xs flex items-center justify-center">
              {pendingRequestsCount}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('trades')}
          className={cn(
            'flex-1 py-2.5 px-3 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-1 relative',
            activeTab === 'trades'
              ? 'bg-purple-500 text-white'
              : 'text-gray-400 hover:text-white'
          )}
        >
          <ArrowLeftRight className="w-4 h-4" />
          Обмены
          {pendingTradesCount > 0 && (
            <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full text-xs flex items-center justify-center">
              {pendingTradesCount}
            </span>
          )}
        </button>
      </div>

      {/* Friends Tab */}
      {activeTab === 'friends' && (
        <>
          {/* Search to add friend */}
          <Card className="mb-4">
            <h3 className="text-sm font-medium text-white mb-2">Добавить друга</h3>
            <div className="flex gap-2">
              <input
                type="text"
                value={searchUsername}
                onChange={(e) => setSearchUsername(e.target.value)}
                placeholder="Username друга..."
                className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500 text-sm"
              />
              <Button
                size="sm"
                onClick={handleSendRequest}
                disabled={!searchUsername.trim()}
                isLoading={sendRequestMutation.isPending}
              >
                <UserPlus className="w-4 h-4" />
              </Button>
            </div>
            {sendRequestMutation.isError && (
              <p className="text-xs text-red-400 mt-2">
                Пользователь не найден или уже в друзьях
              </p>
            )}
            {sendRequestMutation.isSuccess && (
              <p className="text-xs text-green-400 mt-2">Запрос отправлен!</p>
            )}
          </Card>

          {/* Friends list */}
          {friendsLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 bg-gray-800 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : friends.length === 0 ? (
            <Card className="text-center py-8">
              <Users className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400">Пока нет друзей</p>
              <p className="text-sm text-gray-500 mt-1">
                Добавь друга по username чтобы обмениваться картами
              </p>
            </Card>
          ) : (
            <div className="space-y-3">
              {friends.map((friend) => (
                <Card key={friend.friendship_id} className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white font-bold">
                    {(friend.first_name?.[0] || friend.username?.[0] || '?').toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-white truncate">
                      {friend.first_name || friend.username}
                    </h3>
                    {friend.username && friend.first_name && (
                      <p className="text-xs text-gray-400">@{friend.username}</p>
                    )}
                    {friend.level && (
                      <p className="text-xs text-purple-400">Уровень {friend.level}</p>
                    )}
                  </div>
                  <Button size="sm" variant="secondary" onClick={() => handleStartTrade(friend)}>
                    <ArrowLeftRight className="w-4 h-4" />
                  </Button>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {/* Requests Tab */}
      {activeTab === 'requests' && (
        <>
          {requestsLoading ? (
            <div className="space-y-3">
              {[1, 2].map((i) => (
                <div key={i} className="h-16 bg-gray-800 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : requests.length === 0 ? (
            <Card className="text-center py-8">
              <Inbox className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400">Нет входящих запросов</p>
            </Card>
          ) : (
            <div className="space-y-3">
              {requests.map((request) => (
                <Card key={request.id} className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-green-500 to-teal-500 flex items-center justify-center text-white font-bold">
                    {(request.first_name?.[0] || request.username?.[0] || '?').toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-white truncate">
                      {request.first_name || request.username}
                    </h3>
                    {request.username && (
                      <p className="text-xs text-gray-400">@{request.username}</p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={() => acceptRequestMutation.mutate(request.id)}
                      isLoading={acceptRequestMutation.isPending}
                    >
                      <Check className="w-4 h-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => rejectRequestMutation.mutate(request.id)}
                      isLoading={rejectRequestMutation.isPending}
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {/* Trades Tab */}
      {activeTab === 'trades' && (
        <>
          {tradesLoading ? (
            <div className="space-y-3">
              {[1, 2].map((i) => (
                <div key={i} className="h-24 bg-gray-800 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : receivedTrades.length === 0 && sentTrades.length === 0 ? (
            <Card className="text-center py-8">
              <ArrowLeftRight className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400">Нет активных обменов</p>
              <p className="text-sm text-gray-500 mt-1">
                Предложи обмен другу из списка друзей
              </p>
            </Card>
          ) : (
            <div className="space-y-4">
              {/* Received trades */}
              {receivedTrades.filter((t) => t.status === 'pending').length > 0 && (
                <>
                  <h3 className="text-sm font-medium text-gray-400 flex items-center gap-2">
                    <Inbox className="w-4 h-4" />
                    Входящие предложения
                  </h3>
                  <div className="space-y-3">
                    {receivedTrades
                      .filter((t) => t.status === 'pending')
                      .map((trade) => (
                        <Card key={trade.id}>
                          <div className="flex items-center gap-2 mb-3">
                            <span className="text-sm text-gray-400">От:</span>
                            <span className="text-white font-medium">{trade.sender_name}</span>
                          </div>
                          <div className="space-y-3 mb-3">
                            <div>
                              <p className="text-xs text-gray-500 mb-2">
                                Предлагает {trade.sender_cards.length > 1 && `(${trade.sender_cards.length})`}
                              </p>
                              <div className="space-y-2">
                                {trade.sender_cards.map((card) => (
                                  <div key={card.id}>{renderCardMini(card)}</div>
                                ))}
                              </div>
                            </div>
                            <div className="flex justify-center">
                              <ArrowLeftRight className="w-5 h-5 text-gray-500 rotate-90" />
                            </div>
                            <div>
                              <p className="text-xs text-gray-500 mb-2">
                                Хочет {trade.receiver_cards.length > 1 && `(${trade.receiver_cards.length})`}
                              </p>
                              {trade.receiver_cards.length > 0 ? (
                                <div className="space-y-2">
                                  {trade.receiver_cards.map((card) => (
                                    <div key={card.id}>{renderCardMini(card)}</div>
                                  ))}
                                </div>
                              ) : (
                                <div className="h-20 rounded-xl border border-dashed border-pink-500/30 bg-pink-500/5 flex items-center justify-center gap-1">
                                  <Gift className="w-4 h-4 text-pink-400" />
                                  <span className="text-xs text-pink-400">Подарок</span>
                                </div>
                              )}
                            </div>
                          </div>
                          {trade.message && (
                            <p className="text-sm text-gray-400 mb-3 italic">
                              &quot;{trade.message}&quot;
                            </p>
                          )}
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              className="flex-1"
                              onClick={() => acceptTradeMutation.mutate(trade.id)}
                              isLoading={acceptTradeMutation.isPending}
                            >
                              <Check className="w-4 h-4 mr-1" />
                              Принять
                            </Button>
                            <Button
                              size="sm"
                              variant="secondary"
                              className="flex-1"
                              onClick={() => rejectTradeMutation.mutate(trade.id)}
                              isLoading={rejectTradeMutation.isPending}
                            >
                              <X className="w-4 h-4 mr-1" />
                              Отклонить
                            </Button>
                          </div>
                        </Card>
                      ))}
                  </div>
                </>
              )}

              {/* Sent trades */}
              {sentTrades.filter((t) => t.status === 'pending').length > 0 && (
                <>
                  <h3 className="text-sm font-medium text-gray-400 flex items-center gap-2 mt-4">
                    <SendHorizonal className="w-4 h-4" />
                    Исходящие предложения
                  </h3>
                  <div className="space-y-3">
                    {sentTrades
                      .filter((t) => t.status === 'pending')
                      .map((trade) => (
                        <Card key={trade.id}>
                          <div className="flex items-center gap-2 mb-3">
                            <span className="text-sm text-gray-400">Кому:</span>
                            <span className="text-white font-medium">{trade.receiver_name}</span>
                            <Clock className="w-4 h-4 text-yellow-500 ml-auto" />
                            <span className="text-xs text-yellow-500">Ожидает</span>
                          </div>
                          <div className="space-y-3 mb-3">
                            <div>
                              <p className="text-xs text-gray-500 mb-2">
                                Ваши карты {trade.sender_cards.length > 1 && `(${trade.sender_cards.length})`}
                              </p>
                              <div className="space-y-2">
                                {trade.sender_cards.map((card) => (
                                  <div key={card.id}>{renderCardMini(card)}</div>
                                ))}
                              </div>
                            </div>
                            <div className="flex justify-center">
                              <ArrowLeftRight className="w-5 h-5 text-gray-500 rotate-90" />
                            </div>
                            <div>
                              <p className="text-xs text-gray-500 mb-2">
                                Взамен {trade.receiver_cards.length > 1 && `(${trade.receiver_cards.length})`}
                              </p>
                              {trade.receiver_cards.length > 0 ? (
                                <div className="space-y-2">
                                  {trade.receiver_cards.map((card) => (
                                    <div key={card.id}>{renderCardMini(card)}</div>
                                  ))}
                                </div>
                              ) : (
                                <div className="h-20 rounded-xl border border-dashed border-pink-500/30 bg-pink-500/5 flex items-center justify-center gap-1">
                                  <Gift className="w-4 h-4 text-pink-400" />
                                  <span className="text-xs text-pink-400">Подарок</span>
                                </div>
                              )}
                            </div>
                          </div>
                          <Button
                            size="sm"
                            variant="secondary"
                            className="w-full"
                            onClick={() => cancelTradeMutation.mutate(trade.id)}
                            isLoading={cancelTradeMutation.isPending}
                          >
                            <X className="w-4 h-4 mr-1" />
                            Отменить
                          </Button>
                        </Card>
                      ))}
                  </div>
                </>
              )}
            </div>
          )}
        </>
      )}

      {/* Referral Rewards Modal */}
      <ReferralRewardModal
        isOpen={showReferralModal}
        rewards={referralRewards}
        onClose={handleCloseReferralModal}
      />
    </div>
  );
}
