'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import {
  Shield,
  Users,
  Swords,
  Crown,
  Plus,
  Search,
  ChevronRight,
  Zap,
  Trophy,
  Clock,
  Heart,
} from 'lucide-react';
import { Card, Button, Progress } from '@/components/ui';
import { guildsService } from '@/services';
import { useAppStore } from '@/lib/store';
import { hapticFeedback, showBackButton, hideBackButton } from '@/lib/telegram';
import { cn } from '@/lib/utils';
import type { Guild, GuildRaid, RaidContribution } from '@/services/guilds';

type Tab = 'my-guild' | 'browse' | 'leaderboard';

export default function GuildsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user } = useAppStore();

  const [activeTab, setActiveTab] = useState<Tab>('my-guild');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    showBackButton(() => router.back());
    return () => hideBackButton();
  }, [router]);

  // Get user's guild
  const { data: myGuildData, isLoading: myGuildLoading } = useQuery({
    queryKey: ['guilds', 'my'],
    queryFn: () => guildsService.getMyGuild(),
    enabled: !!user,
  });

  // Get guild raids if in guild
  const { data: raidsData } = useQuery({
    queryKey: ['guilds', myGuildData?.data?.guild?.id, 'raids'],
    queryFn: () => guildsService.getGuildRaids(myGuildData!.data!.guild!.id),
    enabled: !!myGuildData?.data?.guild,
  });

  // Browse guilds
  const { data: guildsData, isLoading: guildsLoading } = useQuery({
    queryKey: ['guilds', 'browse', searchQuery],
    queryFn: () => guildsService.getGuilds({ search: searchQuery || undefined }),
    enabled: activeTab === 'browse',
  });

  // Leaderboard
  const { data: leaderboardData } = useQuery({
    queryKey: ['guilds', 'leaderboard'],
    queryFn: () => guildsService.getLeaderboard(),
    enabled: activeTab === 'leaderboard',
  });

  // Join guild mutation
  const joinGuildMutation = useMutation({
    mutationFn: (guildId: number) => guildsService.joinGuild(guildId),
    onSuccess: () => {
      hapticFeedback('success');
      queryClient.invalidateQueries({ queryKey: ['guilds'] });
      setActiveTab('my-guild');
    },
  });

  // Leave guild mutation
  const leaveGuildMutation = useMutation({
    mutationFn: () => guildsService.leaveGuild(),
    onSuccess: () => {
      hapticFeedback('success');
      queryClient.invalidateQueries({ queryKey: ['guilds'] });
    },
  });

  // Attack raid mutation
  const attackRaidMutation = useMutation({
    mutationFn: (raidId: number) => guildsService.attackRaid(raidId),
    onSuccess: (result) => {
      if (result.success) {
        hapticFeedback('success');
        queryClient.invalidateQueries({ queryKey: ['guilds'] });
      }
    },
  });

  const myGuild = myGuildData?.data?.guild;
  const membership = myGuildData?.data?.membership;
  const activeRaid = raidsData?.data?.active_raid;

  const formatTimeRemaining = (expiresAt: string) => {
    const remaining = new Date(expiresAt).getTime() - Date.now();
    if (remaining <= 0) return 'Истекло';
    const hours = Math.floor(remaining / (1000 * 60 * 60));
    const mins = Math.floor((remaining % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}ч ${mins}м`;
  };

  return (
    <div className="p-4 pb-4">
      {/* Header */}
      <div className="text-center mb-4">
        <Shield className="w-10 h-10 text-purple-500 mx-auto mb-2" />
        <h1 className="text-2xl font-bold text-white">Гильдии</h1>
        <p className="text-sm text-gray-400">Объединяйтесь и сражайтесь вместе</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-gray-800 rounded-xl mb-4">
          {[
            { id: 'my-guild', label: 'Моя гильдия', icon: Shield },
            { id: 'browse', label: 'Поиск', icon: Search },
            { id: 'leaderboard', label: 'Топ', icon: Trophy },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id as Tab)}
              className={cn(
                'flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg text-sm font-medium transition-colors',
                activeTab === id
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:text-white'
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
      </div>

      {/* My Guild Tab */}
      {activeTab === 'my-guild' && (
          <div className="space-y-4">
            {myGuildLoading ? (
              <div className="text-center text-gray-400 py-8">Загрузка...</div>
            ) : myGuild ? (
              <>
                {/* Guild Card */}
                <Card className="bg-gradient-to-br from-purple-900/30 to-blue-900/30 border-purple-500/30">
                  <div className="p-4 space-y-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-14 h-14 bg-purple-600/30 rounded-xl flex items-center justify-center text-2xl">
                          {myGuild.emoji}
                        </div>
                        <div>
                          <h2 className="text-lg font-bold text-white">{myGuild.name}</h2>
                          <div className="flex items-center gap-2 text-sm text-gray-400">
                            <Users className="w-4 h-4" />
                            <span>{myGuild.members_count}/{myGuild.max_members}</span>
                            <span className="text-purple-400">Ур. {myGuild.level}</span>
                          </div>
                        </div>
                      </div>
                      {membership?.role === 'leader' && (
                        <Crown className="w-5 h-5 text-amber-400" />
                      )}
                    </div>

                    {myGuild.description && (
                      <p className="text-sm text-gray-300">{myGuild.description}</p>
                    )}

                    <div className="flex gap-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => router.push(`/guilds/${myGuild.id}`)}
                        className="flex-1"
                      >
                        Подробнее
                      </Button>
                      {membership?.role !== 'leader' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => leaveGuildMutation.mutate()}
                          disabled={leaveGuildMutation.isPending}
                          className="text-red-400"
                        >
                          Выйти
                        </Button>
                      )}
                    </div>
                  </div>
                </Card>

                {/* Active Raid */}
                {activeRaid && (
                  <Card className="bg-gradient-to-br from-red-900/30 to-orange-900/30 border-red-500/30">
                    <div className="p-4 space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-12 h-12 bg-red-600/30 rounded-xl flex items-center justify-center text-xl">
                            {activeRaid.boss_emoji}
                          </div>
                          <div>
                            <h3 className="font-bold text-white">Рейд: {activeRaid.boss_name}</h3>
                            <div className="flex items-center gap-2 text-sm text-gray-400">
                              <Clock className="w-3.5 h-3.5" />
                              <span>{formatTimeRemaining(activeRaid.expires_at)}</span>
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-xs text-gray-400">Награда</div>
                          <div className="text-sm text-amber-400 font-medium">
                            +{activeRaid.xp_reward} XP
                          </div>
                        </div>
                      </div>

                      {/* Boss HP */}
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-400">HP Босса</span>
                          <span className="text-red-400 font-medium">
                            {activeRaid.current_hp.toLocaleString()} / {activeRaid.total_hp.toLocaleString()}
                          </span>
                        </div>
                        <Progress
                          value={(activeRaid.current_hp / activeRaid.total_hp) * 100}
                          className="h-3 bg-gray-700"
                        />
                      </div>

                      {/* Attack Button */}
                      <Button
                        onClick={() => attackRaidMutation.mutate(activeRaid.id)}
                        disabled={attackRaidMutation.isPending}
                        className="w-full bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-700 hover:to-orange-700"
                      >
                        <Swords className="w-4 h-4 mr-2" />
                        Атаковать!
                      </Button>

                      {/* Participants */}
                      <div className="flex items-center justify-between text-sm text-gray-400">
                        <span>Участников: {activeRaid.participants_count}</span>
                        <span>Урон: {activeRaid.total_damage_dealt.toLocaleString()}</span>
                      </div>
                    </div>
                  </Card>
                )}

                {!activeRaid && membership?.role !== 'member' && (
                  <Card className="bg-gray-800/50 border-gray-700/50">
                    <div className="p-4 text-center space-y-3">
                      <Swords className="w-10 h-10 text-gray-500 mx-auto" />
                      <p className="text-gray-400">Нет активного рейда</p>
                      <Button variant="secondary" size="sm">
                        <Plus className="w-4 h-4 mr-1" />
                        Начать рейд
                      </Button>
                    </div>
                  </Card>
                )}
              </>
            ) : (
              <Card className="bg-gray-800/50 border-gray-700/50">
                <div className="p-8 text-center space-y-4">
                  <Shield className="w-16 h-16 text-gray-600 mx-auto" />
                  <div>
                    <h3 className="text-lg font-medium text-white mb-1">Вы не в гильдии</h3>
                    <p className="text-gray-400 text-sm">
                      Присоединитесь к гильдии чтобы участвовать в рейдах и получать награды
                    </p>
                  </div>
                  <div className="flex gap-2 justify-center">
                    <Button onClick={() => setActiveTab('browse')}>
                      <Search className="w-4 h-4 mr-1" />
                      Найти гильдию
                    </Button>
                    <Button variant="secondary">
                      <Plus className="w-4 h-4 mr-1" />
                      Создать
                    </Button>
                  </div>
                </div>
              </Card>
            )}
          </div>
        )}

      {/* Browse Tab */}
      {activeTab === 'browse' && (
          <div className="space-y-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Поиск гильдий..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-gray-800/50 border border-gray-700/50 rounded-xl py-2.5 pl-10 pr-4 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
              />
            </div>

            {/* Guild List */}
            {guildsLoading ? (
              <div className="text-center text-gray-400 py-8">Загрузка...</div>
            ) : guildsData?.data?.guilds?.length ? (
              <div className="space-y-3">
                {guildsData.data.guilds.map((guild) => (
                  <Card
                    key={guild.id}
                    className="bg-gray-800/50 border-gray-700/50 hover:border-purple-500/50 transition-colors cursor-pointer"
                    onClick={() => joinGuildMutation.mutate(guild.id)}
                  >
                    <div className="p-4 flex items-center gap-3">
                      <div className="w-12 h-12 bg-purple-600/20 rounded-xl flex items-center justify-center text-xl">
                        {guild.emoji}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium text-white truncate">{guild.name}</h3>
                        <div className="flex items-center gap-2 text-sm text-gray-400">
                          <Users className="w-3.5 h-3.5" />
                          <span>{guild.members_count}/{guild.max_members}</span>
                          <span className="text-purple-400">Ур. {guild.level}</span>
                        </div>
                      </div>
                      <ChevronRight className="w-5 h-5 text-gray-500" />
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center text-gray-400 py-8">
                {searchQuery ? 'Ничего не найдено' : 'Нет доступных гильдий'}
              </div>
            )}
          </div>
        )}

      {/* Leaderboard Tab */}
      {activeTab === 'leaderboard' && (
          <div className="space-y-3">
            {leaderboardData?.data?.guilds?.map((guild, index) => (
              <Card
                key={guild.id}
                className={cn(
                  'border-gray-700/50',
                  index === 0 && 'bg-gradient-to-r from-amber-900/30 to-yellow-900/30 border-amber-500/30',
                  index === 1 && 'bg-gradient-to-r from-gray-600/30 to-gray-700/30 border-gray-400/30',
                  index === 2 && 'bg-gradient-to-r from-orange-900/30 to-amber-900/30 border-orange-500/30',
                  index > 2 && 'bg-gray-800/50'
                )}
              >
                <div className="p-4 flex items-center gap-3">
                  <div className={cn(
                    'w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm',
                    index === 0 && 'bg-amber-500 text-black',
                    index === 1 && 'bg-gray-400 text-black',
                    index === 2 && 'bg-orange-600 text-white',
                    index > 2 && 'bg-gray-700 text-gray-300'
                  )}>
                    {index + 1}
                  </div>
                  <div className="w-10 h-10 bg-purple-600/20 rounded-lg flex items-center justify-center text-lg">
                    {guild.emoji}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-white truncate">{guild.name}</h3>
                    <div className="text-sm text-gray-400">
                      Ур. {guild.level} | {guild.members_count} участников
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
    </div>
  );
}
