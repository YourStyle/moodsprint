'use client';

import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Shield,
  Users,
  Crown,
  Plus,
  Search,
  Trophy,
  Share2,
  UserMinus,
  Star,
} from 'lucide-react';
import { Card, Button, Progress, ScrollBackdrop } from '@/components/ui';
import { CreateGuildModal } from '@/components/guilds';
import { guildsService } from '@/services';
import { useAppStore } from '@/lib/store';
import { useLanguage } from '@/lib/i18n';
import { hapticFeedback, getTelegramWebApp, setupBackButton } from '@/lib/telegram';
import { cn } from '@/lib/utils';
import type { Guild, GuildMember } from '@/services/guilds';

type Tab = 'my-guild' | 'browse' | 'leaderboard';

export default function GuildsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { user } = useAppStore();
  const { t } = useLanguage();

  const [activeTab, setActiveTab] = useState<Tab>('my-guild');
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const inviteGuildHandled = useRef(false);

  // Setup native back button
  useEffect(() => {
    return setupBackButton(() => router.back());
  }, [router]);

  // Get invite_guild from URL params
  const inviteGuildId = searchParams.get('invite_guild');

  // Get user's guild
  const { data: myGuildData, isLoading: myGuildLoading } = useQuery({
    queryKey: ['guilds', 'my'],
    queryFn: () => guildsService.getMyGuild(),
    enabled: !!user,
  });

  // Get guild details with members if in guild
  const { data: guildDetailsData } = useQuery({
    queryKey: ['guilds', myGuildData?.data?.guild?.id, 'details'],
    queryFn: () => guildsService.getGuildDetails(myGuildData!.data!.guild!.id),
    enabled: !!myGuildData?.data?.guild,
  });

  // Get invite link
  const { data: inviteLinkData } = useQuery({
    queryKey: ['guilds', 'invite-link'],
    queryFn: () => guildsService.getInviteLink(),
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

  // Handle invite_guild URL parameter - auto-join guild
  useEffect(() => {
    if (inviteGuildId && user && !inviteGuildHandled.current && !myGuildLoading) {
      const guildId = parseInt(inviteGuildId, 10);
      if (!isNaN(guildId) && guildId > 0) {
        // Only join if user is not already in a guild
        if (!myGuildData?.data?.guild) {
          inviteGuildHandled.current = true;
          console.log('[Guild] Auto-joining guild from invite:', guildId);
          joinGuildMutation.mutate(guildId);
        } else {
          console.log('[Guild] User already in a guild, cannot join via invite');
        }
      }
    }
  }, [inviteGuildId, user, myGuildLoading, myGuildData, joinGuildMutation]);

  // Leave guild mutation
  const leaveGuildMutation = useMutation({
    mutationFn: () => guildsService.leaveGuild(),
    onSuccess: () => {
      hapticFeedback('success');
      queryClient.invalidateQueries({ queryKey: ['guilds'] });
    },
  });

  // Kick member mutation
  const kickMemberMutation = useMutation({
    mutationFn: (memberId: number) => guildsService.kickMember(myGuild!.id, memberId),
    onSuccess: () => {
      hapticFeedback('success');
      queryClient.invalidateQueries({ queryKey: ['guilds'] });
    },
  });

  const myGuild = myGuildData?.data?.guild;
  const membership = myGuildData?.data?.membership;
  const members = guildDetailsData?.data?.members || [];
  const userRole = membership?.role;
  const isLeader = userRole === 'leader';

  const handleShareInvite = () => {
    if (!inviteLinkData?.data?.invite_link || !myGuild) return;

    hapticFeedback('light');

    const webApp = getTelegramWebApp();
    const shareText = `${t('joinGuildInvitePrefix')} "${myGuild.name}"! ${myGuild.emoji}`;
    const shareUrl = inviteLinkData.data.invite_link;
    const telegramShareUrl = `https://t.me/share/url?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(shareText)}`;

    if (webApp && webApp.openTelegramLink) {
      webApp.openTelegramLink(telegramShareUrl);
    } else {
      window.open(telegramShareUrl, '_blank');
    }
  };

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'leader': return <Crown className="w-4 h-4 text-amber-400" />;
      case 'officer': return <Star className="w-4 h-4 text-purple-400" />;
      default: return null;
    }
  };

  const getRoleLabel = (role: string) => {
    switch (role) {
      case 'leader': return t('leader');
      case 'officer': return t('officer');
      default: return t('member');
    }
  };

  return (
    <div className="p-4 pb-24">
      <ScrollBackdrop />
      {/* Header */}
      <div className="mb-4">
        <div className="flex items-center gap-3">
          <Shield className="w-8 h-8 text-purple-500" />
          <div>
            <h1 className="text-xl font-bold text-white">{t('guilds')}</h1>
            <p className="text-sm text-gray-400">{t('guildsSubtitle')}</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-gray-800 rounded-xl mb-4">
        {[
          { id: 'my-guild', label: t('myGuild'), icon: Shield },
          { id: 'browse', label: t('search'), icon: Search },
          { id: 'leaderboard', label: t('top'), icon: Trophy },
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
            <div className="text-center text-gray-400 py-8">{t('loading')}</div>
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
                          <span className="text-purple-400">{t('lvl')} {myGuild.level}</span>
                        </div>
                      </div>
                    </div>
                    {isLeader && <Crown className="w-5 h-5 text-amber-400" />}
                  </div>

                  {myGuild.description && (
                    <p className="text-sm text-gray-300">{myGuild.description}</p>
                  )}

                  {/* XP Progress */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs text-gray-400">
                      <span>{t('guildXP')}</span>
                      <span>{myGuild.xp} XP</span>
                    </div>
                    <Progress value={(myGuild.xp % 1000) / 10} className="h-2" />
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handleShareInvite}
                      className="flex-1"
                    >
                      <Share2 className="w-4 h-4 mr-1" />
                      {t('invite')}
                    </Button>
                    {!isLeader && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => leaveGuildMutation.mutate()}
                        disabled={leaveGuildMutation.isPending}
                        className="text-red-400"
                      >
                        {t('leave')}
                      </Button>
                    )}
                  </div>
                </div>
              </Card>

              {/* Members List */}
              <div>
                <h3 className="font-medium text-white mb-3 flex items-center gap-2">
                  <Users className="w-4 h-4 text-purple-400" />
                  {t('members')} ({members.length})
                </h3>
                <div className="space-y-2">
                  {members.map((member) => (
                    <Card key={member.id} className="bg-gray-800/50 border-gray-700/50">
                      <div className="p-3 flex items-center gap-3">
                        {/* Avatar with crown for leader */}
                        <div className="relative">
                          {member.photo_url ? (
                            <img
                              src={member.photo_url}
                              alt=""
                              className="w-10 h-10 rounded-full object-cover"
                            />
                          ) : (
                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white font-bold">
                              {(member.first_name?.[0] || member.username?.[0] || '?').toUpperCase()}
                            </div>
                          )}
                          {member.role === 'leader' && (
                            <div className="absolute -top-1 -right-1 w-5 h-5 bg-amber-500 rounded-full flex items-center justify-center">
                              <Crown className="w-3 h-3 text-white" />
                            </div>
                          )}
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-white truncate flex items-center gap-1">
                            {member.first_name || member.username || `User #${member.user_id}`}
                            {member.role === 'officer' && (
                              <Star className="w-3 h-3 text-purple-400" />
                            )}
                          </div>
                          {member.username && (
                            <div className="text-xs text-gray-500">@{member.username}</div>
                          )}
                        </div>

                        <div className="text-right">
                          <div className="text-sm text-amber-400">+{member.contribution_xp} XP</div>
                        </div>

                        {isLeader && member.role !== 'leader' && member.user_id !== user?.id && (
                          <button
                            onClick={() => kickMemberMutation.mutate(member.user_id)}
                            className="p-2 rounded-lg hover:bg-red-600/20 text-red-400 transition-colors"
                          >
                            <UserMinus className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <Card className="bg-gray-800/50 border-gray-700/50">
              <div className="p-8 text-center space-y-4">
                <Shield className="w-16 h-16 text-gray-600 mx-auto" />
                <div>
                  <h3 className="text-lg font-medium text-white mb-1">{t('notInGuild')}</h3>
                  <p className="text-gray-400 text-sm">
                    {t('joinGuildToEarn')}
                  </p>
                </div>
                <div className="flex gap-2 justify-center">
                  <Button onClick={() => setActiveTab('browse')}>
                    <Search className="w-4 h-4 mr-1" />
                    {t('findGuild')}
                  </Button>
                  <Button variant="secondary" onClick={() => setShowCreateModal(true)}>
                    <Plus className="w-4 h-4 mr-1" />
                    {t('createGuild')}
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
              placeholder={t('searchGuilds')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-gray-800/50 border border-gray-700/50 rounded-xl py-2.5 pl-10 pr-4 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
            />
          </div>

          {/* Guild List */}
          {guildsLoading ? (
            <div className="text-center text-gray-400 py-8">{t('loading')}</div>
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
                        <span className="text-purple-400">{t('lvl')} {guild.level}</span>
                      </div>
                    </div>
                    <Button size="sm">{t('join')}</Button>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <div className="text-center text-gray-400 py-8">
              {searchQuery ? t('nothingFound') : t('noGuildsAvailable')}
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
                    {t('lvl')} {guild.level} | {guild.members_count} {t('membersCount')}
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Create Guild Modal */}
      <CreateGuildModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={() => setActiveTab('my-guild')}
      />
    </div>
  );
}
