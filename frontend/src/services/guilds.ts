/**
 * Guilds API service.
 */

import type { ApiResponse } from '@/domain/types';
import { api } from './api';

export interface Guild {
  id: number;
  name: string;
  description?: string;
  emoji: string;
  level: number;
  xp: number;
  is_public: boolean;
  max_members: number;
  members_count: number;
  leader_name?: string;
  created_at: string;
}

export interface GuildMember {
  id: number;
  user_id: number;
  username?: string;
  first_name?: string;
  photo_url?: string;
  role: 'leader' | 'officer' | 'member';
  contribution_xp: number;
  raids_participated: number;
  total_damage_dealt: number;
  joined_at: string;
}

export interface GuildRaid {
  id: number;
  guild_id: number;
  boss_name: string;
  boss_emoji: string;
  monster?: {
    id: number;
    name: string;
    emoji: string;
    image_url?: string;
  };
  total_hp: number;
  current_hp: number;
  status: 'active' | 'won' | 'expired';
  xp_reward: number;
  card_reward_rarity: string;
  started_at: string;
  expires_at: string;
  completed_at?: string;
  total_damage_dealt: number;
  participants_count: number;
}

export interface RaidContribution {
  user_id: number;
  username?: string;
  first_name?: string;
  damage_dealt: number;
  attacks_count: number;
  attacks_today: number;
}

export interface GuildQuest {
  id: number;
  guild_id: number;
  quest_type: string;
  title: string;
  emoji: string;
  target: number;
  progress: number;
  percentage: number;
  week_start: string;
  week_end: string;
  status: 'active' | 'completed' | 'expired';
  xp_reward: number;
  sparks_reward: number;
  completed_at?: string;
}

export interface GuildInvite {
  id: number;
  guild_id: number;
  guild_name: string;
  guild_emoji: string;
  invited_by_name?: string;
  created_at: string;
}

class GuildsService {
  async getGuilds(params?: {
    page?: number;
    per_page?: number;
    search?: string;
  }): Promise<ApiResponse<{
    guilds: Guild[];
    total: number;
    page: number;
    pages: number;
  }>> {
    const query = new URLSearchParams();
    if (params?.page) query.set('page', params.page.toString());
    if (params?.per_page) query.set('per_page', params.per_page.toString());
    if (params?.search) query.set('search', params.search);
    return api.get(`/guilds?${query}`);
  }

  async getMyGuild(): Promise<ApiResponse<{
    guild: Guild | null;
    membership: GuildMember | null;
  }>> {
    return api.get('/guilds/my');
  }

  async getGuildDetails(guildId: number): Promise<ApiResponse<{
    guild: Guild;
    members: GuildMember[];
    is_member: boolean;
    user_role?: string;
  }>> {
    return api.get(`/guilds/${guildId}`);
  }

  async createGuild(data: {
    name: string;
    description?: string;
    emoji?: string;
    is_public?: boolean;
  }): Promise<ApiResponse<{ guild: Guild }>> {
    return api.post('/guilds', data);
  }

  async joinGuild(guildId: number): Promise<ApiResponse<{ membership: GuildMember }>> {
    return api.post(`/guilds/${guildId}/join`);
  }

  async leaveGuild(): Promise<ApiResponse<void>> {
    return api.post('/guilds/leave');
  }

  async getGuildRaids(guildId: number): Promise<ApiResponse<{
    active_raid?: GuildRaid;
    recent_raids: GuildRaid[];
  }>> {
    return api.get(`/guilds/${guildId}/raids`);
  }

  async getRaidDetails(raidId: number): Promise<ApiResponse<{
    raid: GuildRaid;
    contributions: RaidContribution[];
    user_contribution?: RaidContribution;
    can_attack: boolean;
  }>> {
    return api.get(`/raids/${raidId}`);
  }

  async attackRaid(raidId: number): Promise<ApiResponse<{
    damage_dealt: number;
    is_critical: boolean;
    boss_defeated: boolean;
    new_hp: number;
    attacks_remaining: number;
    rewards?: {
      xp: number;
      card?: unknown;
    };
  }>> {
    return api.post(`/raids/${raidId}/attack`);
  }

  async startRaid(guildId: number, monsterId?: number): Promise<ApiResponse<{ raid: GuildRaid }>> {
    return api.post(`/guilds/${guildId}/raids`, { monster_id: monsterId });
  }

  async getInvites(): Promise<ApiResponse<{ invites: GuildInvite[] }>> {
    return api.get('/guilds/invites');
  }

  async acceptInvite(inviteId: number): Promise<ApiResponse<{ membership: GuildMember }>> {
    return api.post(`/guilds/invites/${inviteId}/accept`);
  }

  async rejectInvite(inviteId: number): Promise<ApiResponse<void>> {
    return api.post(`/guilds/invites/${inviteId}/reject`);
  }

  async getLeaderboard(params?: {
    sort_by?: 'level' | 'raids_won';
    page?: number;
    per_page?: number;
  }): Promise<ApiResponse<{
    guilds: Guild[];
    total: number;
    page: number;
    pages: number;
  }>> {
    const query = new URLSearchParams();
    if (params?.sort_by) query.set('sort_by', params.sort_by);
    if (params?.page) query.set('page', params.page.toString());
    if (params?.per_page) query.set('per_page', params.per_page.toString());
    return api.get(`/guilds/leaderboard?${query}`);
  }

  async getGuildQuests(guildId: number): Promise<ApiResponse<{ quests: GuildQuest[] }>> {
    return api.get(`/guilds/${guildId}/quests`);
  }

  async generateGuildQuests(guildId: number): Promise<ApiResponse<{ quests: GuildQuest[] }>> {
    return api.post(`/guilds/${guildId}/quests/generate`);
  }

  async getInviteLink(): Promise<ApiResponse<{
    invite_link: string;
    guild_id: number;
    guild_name: string;
  }>> {
    return api.get('/guilds/my/invite-link');
  }

  async kickMember(guildId: number, memberId: number): Promise<ApiResponse<void>> {
    return api.post(`/guilds/${guildId}/kick/${memberId}`);
  }

  async promoteMember(guildId: number, memberId: number, role: string): Promise<ApiResponse<void>> {
    return api.post(`/guilds/${guildId}/promote/${memberId}`, { role });
  }
}

export const guildsService = new GuildsService();
