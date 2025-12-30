"""Campaign API tests."""

import pytest

from app import db
from app.models.campaign import CampaignChapter, CampaignLevel
from app.models.character import Monster


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
        assert "monster" in data["data"]
