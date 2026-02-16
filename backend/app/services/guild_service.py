"""Guild and raid management service."""

import logging
import random
from datetime import date, datetime, timedelta
from typing import Any

from app import db
from app.models import Monster
from app.models.card import UserCard
from app.models.guild import (
    Guild,
    GuildInvite,
    GuildMember,
    GuildQuest,
    GuildRaid,
    GuildRaidContribution,
)

logger = logging.getLogger(__name__)

# Raid configuration
MAX_ATTACKS_PER_DAY = 3
RAID_DURATION_HOURS = 48
BASE_RAID_HP = 10000

# Guild level XP requirements
GUILD_LEVEL_XP = [0, 1000, 3000, 6000, 10000, 15000, 21000, 28000, 36000, 45000]


class GuildService:
    """Service for managing guilds and raids."""

    def create_guild(
        self,
        leader_id: int,
        name: str,
        description: str | None = None,
        emoji: str = "⚔️",
        is_public: bool = True,
    ) -> dict[str, Any]:
        """Create a new guild."""
        # Check if user is already in a guild
        existing_membership = GuildMember.query.filter_by(user_id=leader_id).first()
        if existing_membership:
            return {"error": "already_in_guild"}

        # Check name uniqueness
        if Guild.query.filter_by(name=name).first():
            return {"error": "name_taken"}

        # Check name length
        if len(name) < 3 or len(name) > 50:
            return {"error": "invalid_name_length"}

        guild = Guild(
            name=name,
            description=description,
            emoji=emoji,
            leader_id=leader_id,
            is_public=is_public,
        )
        db.session.add(guild)
        db.session.flush()

        # Add creator as leader
        member = GuildMember(
            guild_id=guild.id,
            user_id=leader_id,
            role="leader",
        )
        db.session.add(member)
        db.session.commit()

        logger.info(f"Guild created: {name} by user {leader_id}")
        return {"success": True, "guild": guild.to_dict()}

    def get_guild(self, guild_id: int) -> Guild | None:
        """Get guild by ID."""
        return Guild.query.get(guild_id)

    def get_user_guild(self, user_id: int) -> Guild | None:
        """Get guild that user belongs to."""
        membership = GuildMember.query.filter_by(user_id=user_id).first()
        if membership:
            return membership.guild
        return None

    def list_guilds(
        self,
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
    ) -> dict[str, Any]:
        """List public guilds."""
        query = Guild.query.filter_by(is_public=True)

        if search:
            query = query.filter(Guild.name.ilike(f"%{search}%"))

        query = query.order_by(Guild.level.desc(), Guild.xp.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            "guilds": [g.to_dict() for g in pagination.items],
            "total": pagination.total,
            "page": page,
            "pages": pagination.pages,
        }

    def join_guild(self, user_id: int, guild_id: int) -> dict[str, Any]:
        """Join a public guild."""
        guild = Guild.query.get(guild_id)
        if not guild:
            return {"error": "guild_not_found"}

        if not guild.is_public:
            return {"error": "guild_not_public"}

        # Check if already in a guild
        if GuildMember.query.filter_by(user_id=user_id).first():
            return {"error": "already_in_guild"}

        # Check member limit
        if guild.member_count >= guild.max_members:
            return {"error": "guild_full"}

        member = GuildMember(
            guild_id=guild_id,
            user_id=user_id,
            role="member",
        )
        db.session.add(member)
        db.session.commit()

        logger.info(f"User {user_id} joined guild {guild_id}")
        return {"success": True, "guild": guild.to_dict()}

    def leave_guild(self, user_id: int) -> dict[str, Any]:
        """Leave current guild."""
        membership = GuildMember.query.filter_by(user_id=user_id).first()
        if not membership:
            return {"error": "not_in_guild"}

        guild = membership.guild

        # Can't leave if you're the leader and there are other members
        if membership.role == "leader" and guild.member_count > 1:
            return {"error": "transfer_leadership_first"}

        # Delete guild if last member
        if guild.member_count == 1:
            db.session.delete(guild)
        else:
            db.session.delete(membership)

        db.session.commit()

        logger.info(f"User {user_id} left guild {guild.id}")
        return {"success": True}

    def get_members(self, guild_id: int) -> list[dict]:
        """Get guild members sorted by contribution."""
        members = (
            GuildMember.query.filter_by(guild_id=guild_id)
            .order_by(GuildMember.contribution_xp.desc())
            .all()
        )
        result = []
        for m in members:
            user = m.user
            result.append(
                {
                    "id": m.id,
                    "user_id": m.user_id,
                    "username": user.username if user else None,
                    "first_name": user.first_name if user else None,
                    "photo_url": user.photo_url if user else None,
                    "role": m.role,
                    "contribution_xp": m.contribution_xp,
                    "raids_participated": m.raids_participated,
                    "total_damage_dealt": m.total_damage_dealt,
                    "joined_at": m.joined_at.isoformat() if m.joined_at else None,
                }
            )
        return result

    def transfer_leadership(self, user_id: int, new_leader_id: int) -> dict[str, Any]:
        """Transfer guild leadership to another member."""
        membership = GuildMember.query.filter_by(user_id=user_id).first()
        if not membership or membership.role != "leader":
            return {"error": "not_leader"}

        new_leader = GuildMember.query.filter_by(
            guild_id=membership.guild_id, user_id=new_leader_id
        ).first()
        if not new_leader:
            return {"error": "member_not_found"}

        # Transfer
        membership.role = "member"
        new_leader.role = "leader"
        membership.guild.leader_id = new_leader_id
        db.session.commit()

        return {"success": True}

    def promote_member(
        self, user_id: int, member_id: int, new_role: str
    ) -> dict[str, Any]:
        """Promote/demote a member (leader only)."""
        if new_role not in ["officer", "member"]:
            return {"error": "invalid_role"}

        leader_membership = GuildMember.query.filter_by(user_id=user_id).first()
        if not leader_membership or leader_membership.role != "leader":
            return {"error": "not_leader"}

        target = GuildMember.query.filter_by(
            guild_id=leader_membership.guild_id, user_id=member_id
        ).first()
        if not target:
            return {"error": "member_not_found"}

        target.role = new_role
        db.session.commit()

        return {"success": True}

    # ============ RAIDS ============

    def start_raid(self, user_id: int, monster_id: int | None = None) -> dict[str, Any]:
        """Start a new guild raid (leader/officer only)."""
        membership = GuildMember.query.filter_by(user_id=user_id).first()
        if not membership:
            return {"error": "not_in_guild"}

        if membership.role not in ["leader", "officer"]:
            return {"error": "not_authorized"}

        guild = membership.guild

        # Check for active raid
        active_raid = GuildRaid.query.filter_by(
            guild_id=guild.id, status="active"
        ).first()
        if active_raid:
            return {"error": "raid_in_progress"}

        # Get or create boss
        if monster_id:
            monster = Monster.query.get(monster_id)
            boss_name = monster.name if monster else "Рейд-Босс"
            boss_emoji = monster.emoji if monster else "👹"
        else:
            boss_name = "Рейд-Босс"
            boss_emoji = "👹"
            monster = None

        # Scale HP based on guild size
        member_count = guild.member_count
        raid_hp = BASE_RAID_HP + (member_count * 2000)

        raid = GuildRaid(
            guild_id=guild.id,
            monster_id=monster.id if monster else None,
            boss_name=boss_name,
            boss_emoji=boss_emoji,
            total_hp=raid_hp,
            current_hp=raid_hp,
            expires_at=datetime.utcnow() + timedelta(hours=RAID_DURATION_HOURS),
        )
        db.session.add(raid)
        db.session.commit()

        logger.info(f"Raid started for guild {guild.id} with HP {raid_hp}")
        return {"success": True, "raid": raid.to_dict()}

    def get_active_raid(self, guild_id: int) -> GuildRaid | None:
        """Get active raid for guild."""
        return GuildRaid.query.filter_by(guild_id=guild_id, status="active").first()

    def attack_raid(self, user_id: int, card_ids: list[int]) -> dict[str, Any]:
        """Attack raid boss with cards."""
        membership = GuildMember.query.filter_by(user_id=user_id).first()
        if not membership:
            return {"error": "not_in_guild"}

        raid = self.get_active_raid(membership.guild_id)
        if not raid:
            return {"error": "no_active_raid"}

        # Check if raid expired
        if datetime.utcnow() > raid.expires_at:
            raid.status = "expired"
            db.session.commit()
            return {"error": "raid_expired"}

        # Get or create contribution
        contribution = GuildRaidContribution.query.filter_by(
            raid_id=raid.id, user_id=user_id
        ).first()

        if not contribution:
            contribution = GuildRaidContribution(
                raid_id=raid.id,
                user_id=user_id,
            )
            db.session.add(contribution)

        # Check daily limit
        today = date.today()
        if contribution.attacks_reset_date != today:
            contribution.attacks_today = 0
            contribution.attacks_reset_date = today

        if contribution.attacks_today >= MAX_ATTACKS_PER_DAY:
            return {"error": "daily_limit_reached", "max_attacks": MAX_ATTACKS_PER_DAY}

        # Calculate damage from cards
        cards = UserCard.query.filter(
            UserCard.id.in_(card_ids),
            UserCard.user_id == user_id,
            UserCard.is_destroyed.is_(False),
        ).all()

        if not cards:
            return {"error": "no_valid_cards"}

        # Check cards not on cooldown
        cooldown_cards = [c for c in cards if c.is_on_cooldown()]
        if cooldown_cards:
            return {"error": "cards_on_cooldown"}

        # Calculate damage (sum of attack with random variance)
        base_damage = sum(c.attack for c in cards)
        variance = random.uniform(0.9, 1.3)
        crit_chance = 0.15
        is_crit = random.random() < crit_chance

        damage = int(base_damage * variance)
        if is_crit:
            damage = int(damage * 1.5)

        # Apply damage to boss
        actual_damage = min(damage, raid.current_hp)
        raid.current_hp -= actual_damage
        raid.total_damage_dealt += actual_damage

        # Update contribution
        contribution.damage_dealt += actual_damage
        contribution.attacks_count += 1
        contribution.attacks_today += 1
        contribution.last_attack_at = datetime.utcnow()

        # Update member stats
        membership.total_damage_dealt += actual_damage
        membership.raids_participated = GuildRaidContribution.query.filter_by(
            user_id=user_id
        ).count()

        # Check if boss defeated
        raid_won = False
        rewards = None
        if raid.current_hp <= 0:
            raid.status = "won"
            raid.completed_at = datetime.utcnow()
            raid.current_hp = 0
            raid_won = True
            rewards = self._distribute_raid_rewards(raid)

        # Update participant count
        raid.participants_count = GuildRaidContribution.query.filter_by(
            raid_id=raid.id
        ).count()

        db.session.commit()

        logger.info(
            f"User {user_id} dealt {actual_damage} damage to raid {raid.id} "
            f"(crit={is_crit})"
        )

        return {
            "success": True,
            "damage": actual_damage,
            "is_critical": is_crit,
            "raid": raid.to_dict(),
            "raid_won": raid_won,
            "rewards": rewards,
        }

    def _distribute_raid_rewards(self, raid: GuildRaid) -> list[dict]:
        """Distribute rewards to raid participants."""
        from app.services.card_service import CardService

        contributions = raid.contributions.order_by(
            GuildRaidContribution.damage_dealt.desc()
        ).all()

        if not contributions:
            return []

        card_service = CardService()
        rewards = []

        for i, contrib in enumerate(contributions):
            # Calculate share of XP based on damage
            if raid.total_damage_dealt > 0:
                share = contrib.damage_dealt / raid.total_damage_dealt
            else:
                share = 1.0 / len(contributions)

            xp_reward = int(raid.xp_reward * share)

            # Top 3 get guaranteed card
            card_reward = None
            if i < 3:
                from app.models.card import CardRarity

                rarity_map = {
                    0: CardRarity.EPIC,  # 1st place
                    1: CardRarity.RARE,  # 2nd place
                    2: CardRarity.RARE,  # 3rd place
                }
                card = card_service.generate_card_for_task(
                    user_id=contrib.user_id,
                    task_id=None,
                    task_title=f"Награда за рейд: {raid.boss_name}",
                    forced_rarity=rarity_map.get(i, CardRarity.RARE),
                )
                if card:
                    card_reward = card.to_dict()

            # Add XP to user
            from app.models import User

            user = User.query.get(contrib.user_id)
            if user:
                user.add_xp(xp_reward)

            # Add XP to guild
            guild = raid.guild
            guild.xp += int(xp_reward * 0.1)  # 10% of user XP goes to guild

            # Update member contribution XP
            membership = GuildMember.query.filter_by(
                guild_id=raid.guild_id, user_id=contrib.user_id
            ).first()
            if membership:
                membership.contribution_xp += xp_reward

            rewards.append(
                {
                    "user_id": contrib.user_id,
                    "rank": i + 1,
                    "damage_dealt": contrib.damage_dealt,
                    "xp_earned": xp_reward,
                    "card": card_reward,
                }
            )

        # Check guild level up
        self._check_guild_level_up(raid.guild)

        return rewards

    def _check_guild_level_up(self, guild: Guild) -> bool:
        """Check if guild should level up."""
        if guild.level >= len(GUILD_LEVEL_XP):
            return False

        next_level_xp = GUILD_LEVEL_XP[guild.level]
        if guild.xp >= next_level_xp:
            guild.level += 1
            guild.max_members += 5  # Increase capacity
            logger.info(f"Guild {guild.id} leveled up to {guild.level}")
            return True
        return False

    def get_raid_leaderboard(self, raid_id: int) -> list[dict]:
        """Get leaderboard for a raid."""
        contributions = (
            GuildRaidContribution.query.filter_by(raid_id=raid_id)
            .order_by(GuildRaidContribution.damage_dealt.desc())
            .all()
        )
        return [c.to_dict() for c in contributions]

    # ============ INVITES ============

    def invite_user(self, inviter_id: int, user_id: int) -> dict[str, Any]:
        """Invite a user to guild."""
        membership = GuildMember.query.filter_by(user_id=inviter_id).first()
        if not membership:
            return {"error": "not_in_guild"}

        if membership.role not in ["leader", "officer"]:
            return {"error": "not_authorized"}

        # Check if user already in a guild
        if GuildMember.query.filter_by(user_id=user_id).first():
            return {"error": "user_in_guild"}

        # Check for existing invite
        existing = GuildInvite.query.filter_by(
            guild_id=membership.guild_id, user_id=user_id, status="pending"
        ).first()
        if existing:
            return {"error": "invite_exists"}

        invite = GuildInvite(
            guild_id=membership.guild_id,
            user_id=user_id,
            invited_by_id=inviter_id,
        )
        db.session.add(invite)
        db.session.commit()

        return {"success": True, "invite": invite.to_dict()}

    def respond_to_invite(
        self, user_id: int, invite_id: int, accept: bool
    ) -> dict[str, Any]:
        """Accept or reject a guild invite."""
        invite = GuildInvite.query.filter_by(
            id=invite_id, user_id=user_id, status="pending"
        ).first()
        if not invite:
            return {"error": "invite_not_found"}

        if accept:
            # Check if user already in a guild
            if GuildMember.query.filter_by(user_id=user_id).first():
                invite.status = "rejected"
                db.session.commit()
                return {"error": "already_in_guild"}

            # Check guild capacity
            if invite.guild.member_count >= invite.guild.max_members:
                invite.status = "rejected"
                db.session.commit()
                return {"error": "guild_full"}

            # Join guild
            member = GuildMember(
                guild_id=invite.guild_id,
                user_id=user_id,
            )
            db.session.add(member)
            invite.status = "accepted"
        else:
            invite.status = "rejected"

        invite.responded_at = datetime.utcnow()
        db.session.commit()

        return {"success": True, "joined": accept}

    def get_pending_invites(self, user_id: int) -> list[dict]:
        """Get pending invites for user."""
        invites = GuildInvite.query.filter_by(user_id=user_id, status="pending").all()
        return [i.to_dict() for i in invites]

    def update_guild(self, guild_id: int, user_id: int, data: dict) -> dict[str, Any]:
        """Update guild settings (leader/officer only)."""
        membership = GuildMember.query.filter_by(user_id=user_id).first()
        if not membership or membership.guild_id != guild_id:
            return {"error": "not_authorized"}

        if membership.role not in ["leader", "officer"]:
            return {"error": "not_authorized"}

        guild = Guild.query.get(guild_id)
        if not guild:
            return {"error": "guild_not_found"}

        # Update fields
        if "name" in data and data["name"]:
            # Check name uniqueness
            existing = Guild.query.filter(
                Guild.name == data["name"], Guild.id != guild_id
            ).first()
            if existing:
                return {"error": "name_taken"}
            guild.name = data["name"]

        if "description" in data:
            guild.description = data["description"]

        if "emoji" in data:
            guild.emoji = data["emoji"]

        if "is_public" in data:
            guild.is_public = data["is_public"]

        db.session.commit()
        return {"success": True, "guild": guild.to_dict()}

    def kick_member(
        self, guild_id: int, user_id: int, member_id: int
    ) -> dict[str, Any]:
        """Kick a member from guild (leader/officer only)."""
        membership = GuildMember.query.filter_by(user_id=user_id).first()
        if not membership or membership.guild_id != guild_id:
            return {"error": "not_authorized"}

        if membership.role not in ["leader", "officer"]:
            return {"error": "not_authorized"}

        if user_id == member_id:
            return {"error": "cannot_kick_self"}

        target = GuildMember.query.filter_by(
            guild_id=guild_id, user_id=member_id
        ).first()
        if not target:
            return {"error": "member_not_found"}

        if target.role == "leader":
            return {"error": "cannot_kick_leader"}

        db.session.delete(target)
        db.session.commit()

        logger.info(f"User {member_id} kicked from guild {guild_id} by {user_id}")
        return {"success": True}

    def invite_to_guild(
        self, guild_id: int, inviter_id: int, user_id: int
    ) -> dict[str, Any]:
        """Invite a user to guild (wrapper for invite_user)."""
        membership = GuildMember.query.filter_by(user_id=inviter_id).first()
        if not membership or membership.guild_id != guild_id:
            return {"error": "not_authorized"}

        return self.invite_user(inviter_id, user_id)

    def get_guild_raids(self, guild_id: int, user_id: int) -> dict[str, Any]:
        """Get guild's raids (active and recent completed)."""
        membership = GuildMember.query.filter_by(user_id=user_id).first()
        if not membership or membership.guild_id != guild_id:
            return {"error": "not_member"}

        active_raid = self.get_active_raid(guild_id)
        recent_raids = (
            GuildRaid.query.filter_by(guild_id=guild_id)
            .filter(GuildRaid.status != "active")
            .order_by(GuildRaid.started_at.desc())
            .limit(10)
            .all()
        )

        return {
            "active_raid": active_raid.to_dict() if active_raid else None,
            "recent_raids": [r.to_dict() for r in recent_raids],
        }

    def get_raid_details(self, raid_id: int, user_id: int) -> dict[str, Any]:
        """Get raid details with leaderboard."""
        raid = GuildRaid.query.get(raid_id)
        if not raid:
            return {"error": "raid_not_found"}

        leaderboard = self.get_raid_leaderboard(raid_id)

        return {
            "raid": raid.to_dict(),
            "leaderboard": leaderboard,
        }

    def get_invite_link(self, user_id: int) -> dict[str, Any]:
        """Get shareable invite link for the guild."""
        import os

        membership = GuildMember.query.filter_by(user_id=user_id).first()
        if not membership:
            return {"error": "not_in_guild"}

        guild = membership.guild
        bot_username = os.environ.get("BOT_USERNAME", "moodsprint_bot")

        # Create Telegram bot deep link with startapp parameter
        invite_link = f"https://t.me/{bot_username}?startapp=guild_{guild.id}"

        return {
            "success": True,
            "invite_link": invite_link,
            "guild_name": guild.name,
            "guild_id": guild.id,
        }

    # ── Weekly Quests ──

    QUEST_TEMPLATES = [
        {
            "quest_type": "tasks_completed",
            "title": "Complete {target} tasks",
            "emoji": "✅",
            "base_target": 20,
            "xp_reward": 300,
            "sparks_reward": 10,
        },
        {
            "quest_type": "focus_minutes",
            "title": "Focus for {target} minutes",
            "emoji": "🎯",
            "base_target": 120,
            "xp_reward": 250,
            "sparks_reward": 5,
        },
        {
            "quest_type": "battles_won",
            "title": "Win {target} battles",
            "emoji": "⚔️",
            "base_target": 10,
            "xp_reward": 350,
            "sparks_reward": 15,
        },
        {
            "quest_type": "cards_earned",
            "title": "Earn {target} cards",
            "emoji": "🃏",
            "base_target": 5,
            "xp_reward": 200,
            "sparks_reward": 5,
        },
        {
            "quest_type": "streaks_maintained",
            "title": "Maintain {target} member streaks",
            "emoji": "🔥",
            "base_target": 3,
            "xp_reward": 400,
            "sparks_reward": 20,
        },
    ]

    def generate_weekly_quests(self, guild_id: int) -> list[dict]:
        """Generate 2-3 weekly quests for a guild."""
        guild = Guild.query.get(guild_id)
        if not guild:
            return []

        today = date.today()
        # Week runs Monday-Sunday
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        # Check if quests already exist for this week
        existing = GuildQuest.query.filter_by(
            guild_id=guild_id, week_start=week_start
        ).first()
        if existing:
            return []

        # Pick 2-3 random quest templates
        member_count = guild.member_count
        count = 3 if member_count >= 5 else 2
        templates = random.sample(
            self.QUEST_TEMPLATES, min(count, len(self.QUEST_TEMPLATES))
        )

        quests = []
        for tmpl in templates:
            # Scale target by member count (more members = higher target)
            scale = max(1, member_count // 3)
            target = tmpl["base_target"] * scale

            quest = GuildQuest(
                guild_id=guild_id,
                quest_type=tmpl["quest_type"],
                title=tmpl["title"].replace("{target}", str(target)),
                emoji=tmpl["emoji"],
                target=target,
                week_start=week_start,
                week_end=week_end,
                xp_reward=tmpl["xp_reward"],
                sparks_reward=tmpl["sparks_reward"],
            )
            db.session.add(quest)
            quests.append(quest)

        db.session.commit()
        return [q.to_dict() for q in quests]

    def generate_quests_for_all_guilds(self) -> int:
        """Generate weekly quests for all guilds. Called by scheduler."""
        guilds = Guild.query.all()
        generated = 0
        for guild in guilds:
            try:
                result = self.generate_weekly_quests(guild.id)
                if result:
                    generated += 1
            except Exception as e:
                logger.error(f"Failed to generate quests for guild {guild.id}: {e}")
        return generated

    def get_active_quests(self, guild_id: int) -> list[dict]:
        """Get active weekly quests for a guild."""
        today = date.today()
        quests = (
            GuildQuest.query.filter(
                GuildQuest.guild_id == guild_id,
                GuildQuest.week_start <= today,
                GuildQuest.week_end >= today,
            )
            .order_by(GuildQuest.id)
            .all()
        )
        return [q.to_dict() for q in quests]

    def increment_quest_progress(
        self, guild_id: int, quest_type: str, amount: int = 1
    ) -> dict | None:
        """Increment progress on a guild's active quest of given type."""
        today = date.today()
        quest = GuildQuest.query.filter(
            GuildQuest.guild_id == guild_id,
            GuildQuest.quest_type == quest_type,
            GuildQuest.status == "active",
            GuildQuest.week_start <= today,
            GuildQuest.week_end >= today,
        ).first()

        if not quest:
            return None

        quest.progress += amount

        if quest.progress >= quest.target:
            quest.status = "completed"
            quest.completed_at = datetime.utcnow()

            # Award guild XP
            guild = Guild.query.get(guild_id)
            if guild:
                guild.xp += quest.xp_reward
                self._check_guild_level_up(guild)

        db.session.commit()
        return quest.to_dict()

    def expire_old_quests(self) -> int:
        """Expire quests past their week_end. Called by scheduler."""
        today = date.today()
        expired = GuildQuest.query.filter(
            GuildQuest.status == "active",
            GuildQuest.week_end < today,
        ).all()
        for q in expired:
            q.status = "expired"
        db.session.commit()
        return len(expired)
