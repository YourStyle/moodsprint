"""Arena/Battle API tests."""

import pytest

from app import db
from app.models.card import UserCard
from app.models.character import Monster


@pytest.fixture
def test_monster(app):
    """Create a test monster."""
    with app.app_context():
        monster = Monster(
            name="Test Goblin",
            description="A weak test monster",
            hp=50,
            attack=10,
            xp_reward=25,
            stat_reward=1,
            difficulty="easy",
            emoji="👺",
        )
        db.session.add(monster)
        db.session.commit()
        db.session.refresh(monster)
        return {"id": monster.id}


@pytest.fixture
def battle_deck(app, test_user):
    """Create a deck ready for battle."""
    with app.app_context():
        cards = []
        for i in range(3):
            card = UserCard(
                user_id=test_user["id"],
                name=f"Battle Card {i}",
                rarity="common",
                genre="magic",
                hp=100,
                attack=20,
                current_hp=100,
                is_in_deck=True,
            )
            db.session.add(card)
            cards.append(card)
        db.session.commit()
        return [{"id": c.id} for c in cards]


class TestGetMonsters:
    """Tests for monster listing."""

    def test_get_monsters_empty(self, auth_client):
        """Should return empty list when no monsters."""
        response = auth_client.get("/api/v1/arena/monsters")

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert "monsters" in data["data"]

    def test_get_monsters_with_data(self, auth_client, test_monster):
        """Should return available monsters."""
        response = auth_client.get("/api/v1/arena/monsters")

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert len(data["data"]["monsters"]) >= 1


class TestStartBattle:
    """Tests for starting a battle."""

    def test_start_battle_no_deck(self, auth_client, test_monster):
        """Should fail without cards in deck."""
        response = auth_client.post(
            "/api/v1/arena/battle",
            json={"monster_id": test_monster["id"]},
        )

        # Should fail due to empty deck
        assert response.status_code in [400, 404]

    def test_start_battle_success(self, auth_client, test_monster, battle_deck):
        """Should start battle with valid deck."""
        response = auth_client.post(
            "/api/v1/arena/battle",
            json={"monster_id": test_monster["id"]},
        )

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert "battle" in data["data"]


class TestActiveBattle:
    """Tests for getting active battle."""

    def test_no_active_battle(self, auth_client):
        """Should return no battle when none active."""
        response = auth_client.get("/api/v1/arena/battle/active")

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert data["data"]["battle"] is None


class TestBattleHistory:
    """Tests for battle history."""

    def test_get_history_empty(self, auth_client):
        """Should return empty history for new user."""
        response = auth_client.get("/api/v1/arena/history")

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert data["data"]["battles"] == []

    def test_get_history_unauthenticated(self, client):
        """Should return 401 when not authenticated."""
        response = client.get("/api/v1/arena/history")

        assert response.status_code == 401
