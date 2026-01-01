"""Campaign API tests."""

import pytest

from app import db
from app.models.campaign import CampaignChapter, CampaignLevel
from app.models.character import Monster
from app.models.user_profile import UserProfile
from app.services.campaign_service import CampaignService


@pytest.fixture
def test_chapter(app):
    """Create a test campaign chapter."""
    with app.app_context():
        chapter = CampaignChapter(
            number=1,
            name="Test Chapter",
            genre="fantasy",
            description="A test chapter",
            emoji="📖",
            background_color="#1a1a2e",
            required_power=0,
            xp_reward=100,
            guaranteed_card_rarity="rare",
            is_active=True,
        )
        db.session.add(chapter)
        db.session.commit()
        db.session.refresh(chapter)
        return {"id": chapter.id, "number": chapter.number}


@pytest.fixture
def multi_genre_chapters(app):
    """Create campaign chapters in multiple genres."""
    with app.app_context():
        chapters = []
        for genre in ["fantasy", "anime", "scifi", "magic", "cyberpunk"]:
            chapter = CampaignChapter(
                number=1,
                name=f"Test Chapter {genre}",
                genre=genre,
                description=f"A {genre} chapter",
                emoji="📖",
                background_color="#1a1a2e",
                required_power=0,
                xp_reward=100,
                guaranteed_card_rarity="rare",
                is_active=True,
            )
            db.session.add(chapter)
            chapters.append({"genre": genre})
        db.session.commit()
        return chapters


@pytest.fixture
def test_level(app, test_chapter, test_monster):
    """Create a test campaign level."""
    with app.app_context():
        level = CampaignLevel(
            chapter_id=test_chapter["id"],
            number=1,
            monster_id=test_monster["id"],
            is_boss=False,
            title="Test Level",
            difficulty_multiplier=1.0,
            required_power=0,
            xp_reward=50,
            stars_max=3,
            is_active=True,
        )
        db.session.add(level)
        db.session.commit()
        db.session.refresh(level)
        return {
            "id": level.id,
            "number": level.number,
            "chapter_id": test_chapter["id"],
        }


@pytest.fixture
def test_monster(app):
    """Create a test monster for campaign."""
    with app.app_context():
        monster = Monster(
            name="Campaign Goblin",
            description="A test monster",
            genre="fantasy",
            level=1,
            base_level=1,
            hp=50,
            base_hp=50,
            attack=10,
            base_attack=10,
            xp_reward=25,
            stat_points_reward=1,
            emoji="👺",
        )
        db.session.add(monster)
        db.session.commit()
        db.session.refresh(monster)
        return {"id": monster.id}


class TestCampaignOverview:
    """Tests for campaign overview endpoint."""

    def test_get_overview_unauthenticated(self, client):
        """Should return 401 when not authenticated."""
        response = client.get("/api/v1/campaign")
        assert response.status_code == 401

    def test_get_overview_empty(self, auth_client):
        """Should return empty campaign when no chapters."""
        response = auth_client.get("/api/v1/campaign")

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert "chapters" in data["data"]

    def test_get_overview_with_data(self, auth_client, test_chapter):
        """Should return campaign chapters."""
        response = auth_client.get("/api/v1/campaign")

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert len(data["data"]["chapters"]) >= 1


class TestCampaignProgress:
    """Tests for campaign progress endpoint."""

    def test_get_progress(self, auth_client):
        """Should return user's campaign progress."""
        response = auth_client.get("/api/v1/campaign/progress")

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert "progress" in data["data"]


class TestChapterDetails:
    """Tests for chapter details endpoint."""

    def test_get_chapter_not_found(self, auth_client):
        """Should return error for non-existent chapter."""
        response = auth_client.get("/api/v1/campaign/chapters/999")

        assert response.status_code == 400

    def test_get_chapter_details(self, auth_client, test_chapter, test_level):
        """Should return chapter details with levels."""
        response = auth_client.get(
            f"/api/v1/campaign/chapters/{test_chapter['number']}"
        )

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert "chapter" in data["data"]
        assert "levels" in data["data"]


class TestStartLevel:
    """Tests for starting a campaign level."""

    def test_start_level_not_found(self, auth_client):
        """Should return error for non-existent level."""
        response = auth_client.post("/api/v1/campaign/levels/999/start")

        assert response.status_code == 400

    def test_start_level_success(self, auth_client, test_level):
        """Should start a campaign level."""
        response = auth_client.post(f"/api/v1/campaign/levels/{test_level['id']}/start")

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True


class TestCompleteLevel:
    """Tests for completing a campaign level."""

    def test_complete_level_won(self, auth_client, test_level):
        """Should complete level with victory."""
        # First start the level
        auth_client.post(f"/api/v1/campaign/levels/{test_level['id']}/start")

        response = auth_client.post(
            f"/api/v1/campaign/levels/{test_level['id']}/complete",
            json={
                "won": True,
                "rounds": 5,
                "hp_remaining": 80,
                "cards_lost": 0,
            },
        )

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True

    def test_complete_level_lost(self, auth_client, test_level):
        """Should handle level loss."""
        auth_client.post(f"/api/v1/campaign/levels/{test_level['id']}/start")

        response = auth_client.post(
            f"/api/v1/campaign/levels/{test_level['id']}/complete",
            json={
                "won": False,
                "rounds": 10,
                "hp_remaining": 0,
                "cards_lost": 3,
            },
        )

        assert response.status_code == 200


class TestDialogueChoice:
    """Tests for dialogue choice processing."""

    def test_dialogue_choice_no_action(self, auth_client, test_level):
        """Should return error when no action specified."""
        response = auth_client.post(
            f"/api/v1/campaign/levels/{test_level['id']}/dialogue-choice",
            json={},
        )

        assert response.status_code == 400

    def test_dialogue_choice_buff_player(self, auth_client, test_level):
        """Should process buff_player action."""
        response = auth_client.post(
            f"/api/v1/campaign/levels/{test_level['id']}/dialogue-choice",
            json={"action": "buff_player"},
        )

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True


class TestBattleConfig:
    """Tests for level battle configuration."""

    def test_get_battle_config_not_found(self, auth_client):
        """Should return error for non-existent level."""
        response = auth_client.get("/api/v1/campaign/levels/999/battle-config")

        assert response.status_code == 400

    def test_get_battle_config(self, auth_client, test_level):
        """Should return battle configuration."""
        response = auth_client.get(
            f"/api/v1/campaign/levels/{test_level['id']}/battle-config"
        )

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert "monster_id" in data["data"]
        assert "monster_name" in data["data"]
        assert "scaled_stats" in data["data"]


class TestCampaignGenreFiltering:
    """Tests for genre-based campaign filtering."""

    def test_user_with_anime_genre_gets_anime_chapters(
        self, app, test_user, multi_genre_chapters
    ):
        """User with anime genre should see anime chapters."""
        with app.app_context():
            # Set user profile to anime genre
            profile = UserProfile.query.filter_by(user_id=test_user["id"]).first()
            if not profile:
                profile = UserProfile(user_id=test_user["id"])
                db.session.add(profile)
            profile.favorite_genre = "anime"
            db.session.commit()

            # Get campaign overview
            service = CampaignService()
            result = service.get_campaign_overview(test_user["id"])

            # Should only return anime chapters
            assert "chapters" in result
            chapters = result["chapters"]
            assert len(chapters) == 1
            assert chapters[0]["genre"] == "anime"

    def test_user_with_scifi_genre_gets_scifi_chapters(
        self, app, test_user, multi_genre_chapters
    ):
        """User with scifi genre should see scifi chapters."""
        with app.app_context():
            # Set user profile to scifi genre
            profile = UserProfile.query.filter_by(user_id=test_user["id"]).first()
            if not profile:
                profile = UserProfile(user_id=test_user["id"])
                db.session.add(profile)
            profile.favorite_genre = "scifi"
            db.session.commit()

            # Get campaign overview
            service = CampaignService()
            result = service.get_campaign_overview(test_user["id"])

            # Should only return scifi chapters
            assert "chapters" in result
            chapters = result["chapters"]
            assert len(chapters) == 1
            assert chapters[0]["genre"] == "scifi"

    def test_user_without_genre_gets_fantasy_default(
        self, app, test_user, multi_genre_chapters
    ):
        """User without genre preference should default to fantasy."""
        with app.app_context():
            # Ensure user has no profile or genre
            profile = UserProfile.query.filter_by(user_id=test_user["id"]).first()
            if profile:
                profile.favorite_genre = None
                db.session.commit()

            # Get campaign overview
            service = CampaignService()
            result = service.get_campaign_overview(test_user["id"])

            # Should return fantasy chapters (default)
            assert "chapters" in result
            chapters = result["chapters"]
            assert len(chapters) == 1
            assert chapters[0]["genre"] == "fantasy"

    def test_genre_change_returns_new_genre_chapters(
        self, app, test_user, multi_genre_chapters
    ):
        """Changing genre should return chapters of the new genre."""
        with app.app_context():
            service = CampaignService()

            # Set to anime first
            profile = UserProfile.query.filter_by(user_id=test_user["id"]).first()
            if not profile:
                profile = UserProfile(user_id=test_user["id"])
                db.session.add(profile)
            profile.favorite_genre = "anime"
            db.session.commit()

            result1 = service.get_campaign_overview(test_user["id"])
            assert result1["chapters"][0]["genre"] == "anime"

            # Change to cyberpunk
            profile.favorite_genre = "cyberpunk"
            db.session.commit()

            result2 = service.get_campaign_overview(test_user["id"])
            assert result2["chapters"][0]["genre"] == "cyberpunk"

            # Change to magic
            profile.favorite_genre = "magic"
            db.session.commit()

            result3 = service.get_campaign_overview(test_user["id"])
            assert result3["chapters"][0]["genre"] == "magic"

    def test_no_chapters_for_genre_returns_all(self, app, test_user, test_chapter):
        """If no chapters exist for user's genre, return all chapters."""
        with app.app_context():
            # Set user to a genre that has no chapters
            profile = UserProfile.query.filter_by(user_id=test_user["id"]).first()
            if not profile:
                profile = UserProfile(user_id=test_user["id"])
                db.session.add(profile)
            profile.favorite_genre = "anime"  # Only fantasy chapter exists
            db.session.commit()

            # Get campaign overview
            service = CampaignService()
            result = service.get_campaign_overview(test_user["id"])

            # Should fallback to showing all chapters
            assert "chapters" in result
            chapters = result["chapters"]
            assert len(chapters) >= 1
