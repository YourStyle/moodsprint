"""Tests for quest system — existing + new card/campaign quests."""

from datetime import date

from app import db
from app.models import DailyQuest
from app.models.quest import QUEST_NAME_PROMPTS, QUEST_TEMPLATES
from app.services.quest_service import QuestService

# ============ Model / Template Tests ============


class TestQuestTemplates:
    """Verify quest template and prompt integrity."""

    def test_all_templates_have_required_fields(self):
        """Every template must have description, target_count, xp_reward, stat_points_reward."""
        for name, tmpl in QUEST_TEMPLATES.items():
            assert "description" in tmpl, f"{name} missing description"
            assert "target_count" in tmpl, f"{name} missing target_count"
            assert "xp_reward" in tmpl, f"{name} missing xp_reward"
            assert "stat_points_reward" in tmpl, f"{name} missing stat_points_reward"
            assert tmpl["target_count"] > 0, f"{name} target_count must be > 0"
            assert tmpl["xp_reward"] > 0, f"{name} xp_reward must be > 0"

    def test_new_quest_types_exist(self):
        """Verify the 5 new card/campaign quest types are registered."""
        new_types = [
            "arena_battles",
            "merge_cards",
            "collect_rarity",
            "campaign_stars",
            "use_abilities",
        ]
        for qt in new_types:
            assert qt in QUEST_TEMPLATES, f"Missing quest template: {qt}"

    def test_all_genres_have_all_quest_prompts(self):
        """Every genre must have prompts for every quest type."""
        expected_genres = {"magic", "fantasy", "scifi", "cyberpunk", "anime"}
        for genre in expected_genres:
            assert genre in QUEST_NAME_PROMPTS, f"Missing genre: {genre}"
            for quest_type in QUEST_TEMPLATES:
                assert (
                    quest_type in QUEST_NAME_PROMPTS[genre]
                ), f"Genre '{genre}' missing prompt for '{quest_type}'"

    def test_quest_prompts_are_non_empty_strings(self):
        """All prompts must be non-empty strings."""
        for genre, prompts in QUEST_NAME_PROMPTS.items():
            for quest_type, prompt_text in prompts.items():
                assert isinstance(
                    prompt_text, str
                ), f"{genre}/{quest_type} prompt is not a string"
                assert (
                    len(prompt_text.strip()) > 0
                ), f"{genre}/{quest_type} prompt is empty"


# ============ Quest Model Tests ============


class TestDailyQuestModel:
    """Test DailyQuest ORM model."""

    def test_create_quest(self, app, test_user):
        """Can create and read back a quest."""
        with app.app_context():
            quest = DailyQuest(
                user_id=test_user["id"],
                quest_type="arena_battles",
                title="Arena Champion",
                description="Win 2 arena battles",
                target_count=2,
                xp_reward=60,
                stat_points_reward=2,
                date=date.today(),
            )
            db.session.add(quest)
            db.session.commit()

            fetched = DailyQuest.query.filter_by(
                user_id=test_user["id"], quest_type="arena_battles"
            ).first()
            assert fetched is not None
            assert fetched.target_count == 2
            assert fetched.current_count == 0
            assert fetched.completed is False

    def test_increment_progress(self, app, test_user):
        """Incrementing progress should complete when target reached."""
        with app.app_context():
            quest = DailyQuest(
                user_id=test_user["id"],
                quest_type="merge_cards",
                title="Card Fusion",
                description="Merge a card",
                target_count=1,
                xp_reward=50,
                stat_points_reward=1,
                date=date.today(),
            )
            db.session.add(quest)
            db.session.commit()

            just_completed = quest.increment_progress()
            assert just_completed is True
            assert quest.completed is True
            assert quest.completed_at is not None

    def test_increment_does_not_overcomplete(self, app, test_user):
        """Incrementing an already-completed quest returns False."""
        with app.app_context():
            quest = DailyQuest(
                user_id=test_user["id"],
                quest_type="collect_rarity",
                title="Rare Find",
                description="Get a rare card",
                target_count=1,
                xp_reward=70,
                stat_points_reward=2,
                date=date.today(),
            )
            db.session.add(quest)
            db.session.commit()

            quest.increment_progress()
            assert quest.completed is True
            # Second call should return False
            assert quest.increment_progress() is False

    def test_claim_reward(self, app, test_user):
        """Claiming reward on completed quest returns xp + stat_points."""
        with app.app_context():
            quest = DailyQuest(
                user_id=test_user["id"],
                quest_type="campaign_stars",
                title="Star Collector",
                description="Earn 3 stars",
                target_count=3,
                xp_reward=80,
                stat_points_reward=2,
                date=date.today(),
            )
            db.session.add(quest)
            db.session.commit()

            quest.increment_progress(3)
            reward = quest.claim_reward()
            assert reward is not None
            assert reward["xp"] == 80
            assert reward["stat_points"] == 2

            # Second claim returns None
            assert quest.claim_reward() is None

    def test_to_dict(self, app, test_user):
        """to_dict should return all expected fields."""
        with app.app_context():
            quest = DailyQuest(
                user_id=test_user["id"],
                quest_type="use_abilities",
                title="Ability Master",
                description="Use 3 abilities",
                target_count=3,
                xp_reward=50,
                stat_points_reward=1,
                date=date.today(),
            )
            db.session.add(quest)
            db.session.commit()

            d = quest.to_dict()
            assert d["quest_type"] == "use_abilities"
            assert d["target_count"] == 3
            assert d["current_count"] == 0
            assert d["completed"] is False
            assert d["progress_percent"] == 0


# ============ QuestService Tests ============


class TestQuestServiceNewMethods:
    """Test the new quest check methods."""

    def _seed_quest(self, app, user_id, quest_type, target_count=1):
        """Helper to create a quest for testing."""
        with app.app_context():
            tmpl = QUEST_TEMPLATES[quest_type]
            quest = DailyQuest(
                user_id=user_id,
                quest_type=quest_type,
                title=f"Test {quest_type}",
                description=tmpl["description"],
                target_count=target_count,
                xp_reward=tmpl["xp_reward"],
                stat_points_reward=tmpl["stat_points_reward"],
                date=date.today(),
            )
            db.session.add(quest)
            db.session.commit()
            return quest.id

    def test_check_battle_win_quests(self, app, test_user):
        """Battle win should increment arena_battles quest."""
        self._seed_quest(app, test_user["id"], "arena_battles", target_count=2)
        with app.app_context():
            service = QuestService()
            updated = service.check_battle_win_quests(test_user["id"])
            assert len(updated) == 1
            assert updated[0].current_count == 1
            assert updated[0].completed is False

            # Second win completes it
            updated2 = service.check_battle_win_quests(test_user["id"])
            assert len(updated2) == 1
            assert updated2[0].completed is True

    def test_check_merge_quests(self, app, test_user):
        """Merge should increment merge_cards quest."""
        self._seed_quest(app, test_user["id"], "merge_cards")
        with app.app_context():
            service = QuestService()
            updated = service.check_merge_quests(test_user["id"])
            assert len(updated) == 1
            assert updated[0].completed is True

    def test_check_card_received_rare(self, app, test_user):
        """Receiving a rare card should increment collect_rarity quest."""
        self._seed_quest(app, test_user["id"], "collect_rarity")
        with app.app_context():
            service = QuestService()
            # Common card — should NOT trigger
            updated = service.check_card_received_quests(test_user["id"], "common")
            assert len(updated) == 0

            # Rare card — should trigger
            updated = service.check_card_received_quests(test_user["id"], "rare")
            assert len(updated) == 1
            assert updated[0].completed is True

    def test_check_card_received_epic(self, app, test_user):
        """Epic card should also trigger collect_rarity."""
        self._seed_quest(app, test_user["id"], "collect_rarity")
        with app.app_context():
            service = QuestService()
            updated = service.check_card_received_quests(test_user["id"], "epic")
            assert len(updated) == 1

    def test_check_card_received_legendary(self, app, test_user):
        """Legendary card should also trigger collect_rarity."""
        self._seed_quest(app, test_user["id"], "collect_rarity")
        with app.app_context():
            service = QuestService()
            updated = service.check_card_received_quests(test_user["id"], "legendary")
            assert len(updated) == 1

    def test_check_campaign_stars(self, app, test_user):
        """Campaign stars should increment campaign_stars quest."""
        self._seed_quest(app, test_user["id"], "campaign_stars", target_count=3)
        with app.app_context():
            service = QuestService()
            # Earn 2 stars
            updated = service.check_campaign_stars_quests(test_user["id"], 2)
            assert len(updated) == 1
            assert updated[0].current_count == 2
            assert updated[0].completed is False

            # Earn 1 more — now completed
            updated = service.check_campaign_stars_quests(test_user["id"], 1)
            assert len(updated) == 1
            assert updated[0].completed is True

    def test_check_campaign_stars_zero(self, app, test_user):
        """Zero stars should not trigger quest."""
        self._seed_quest(app, test_user["id"], "campaign_stars", target_count=3)
        with app.app_context():
            service = QuestService()
            updated = service.check_campaign_stars_quests(test_user["id"], 0)
            assert len(updated) == 0

    def test_check_ability_used(self, app, test_user):
        """Ability use should increment use_abilities quest."""
        self._seed_quest(app, test_user["id"], "use_abilities", target_count=3)
        with app.app_context():
            service = QuestService()
            service.check_ability_used_quests(test_user["id"])
            service.check_ability_used_quests(test_user["id"])
            updated = service.check_ability_used_quests(test_user["id"])
            assert len(updated) == 1
            assert updated[0].completed is True

    def test_no_quest_returns_empty(self, app, test_user):
        """If user has no quest of that type, returns empty list."""
        with app.app_context():
            service = QuestService()
            assert service.check_battle_win_quests(test_user["id"]) == []
            assert service.check_merge_quests(test_user["id"]) == []
            assert service.check_ability_used_quests(test_user["id"]) == []


# ============ Existing Quest API Tests ============


class TestQuestsAPI:
    """Test quests API endpoint (existing behaviour)."""

    def test_get_daily_quests(self, auth_client, test_user):
        """GET /quests should return quests."""
        response = auth_client.get("/api/v1/quests")
        assert response.status_code == 200
        data = response.json["data"]
        assert "quests" in data
        assert "completed_count" in data
        assert "total_count" in data

    def test_quest_generation_creates_three(self, app, test_user):
        """Quest generation should create exactly 3 quests."""
        with app.app_context():
            service = QuestService()
            quests = service.generate_daily_quests(test_user["id"])
            assert len(quests) == 3
            # All should be for today
            for q in quests:
                assert q.date == date.today()

    def test_quest_generation_idempotent(self, app, test_user):
        """Calling generate_daily_quests twice returns same quests."""
        with app.app_context():
            service = QuestService()
            quests1 = service.generate_daily_quests(test_user["id"])
            quests2 = service.generate_daily_quests(test_user["id"])
            assert len(quests1) == len(quests2)
            assert {q.id for q in quests1} == {q.id for q in quests2}
