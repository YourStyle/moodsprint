"""Card system API tests."""

import pytest

from app import db
from app.models.card import UserCard


@pytest.fixture
def test_card(app, test_user):
    """Create a test card for the user."""
    with app.app_context():
        card = UserCard(
            user_id=test_user["id"],
            name="Test Dragon",
            description="A test card",
            rarity="rare",
            genre="fantasy",
            hp=100,
            attack=25,
            current_hp=100,
            emoji="🐉",
            is_in_deck=False,
        )
        db.session.add(card)
        db.session.commit()
        db.session.refresh(card)
        return {"id": card.id, "user_id": card.user_id}


@pytest.fixture
def deck_cards(app, test_user):
    """Create multiple cards in the deck."""
    with app.app_context():
        cards = []
        for i in range(3):
            card = UserCard(
                user_id=test_user["id"],
                name=f"Deck Card {i}",
                rarity="common",
                genre="magic",
                hp=50 + i * 10,
                attack=10 + i * 5,
                current_hp=50 + i * 10,
                is_in_deck=True,
            )
            db.session.add(card)
            cards.append(card)
        db.session.commit()
        return [{"id": c.id} for c in cards]


class TestGetUserCards:
    """Tests for getting user's card collection."""

    def test_get_cards_empty(self, auth_client):
        """Should return empty list for new user."""
        response = auth_client.get("/api/v1/cards")

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert data["data"]["cards"] == []
        assert data["data"]["total"] == 0

    def test_get_cards_with_card(self, auth_client, test_card):
        """Should return user's cards."""
        response = auth_client.get("/api/v1/cards")

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert data["data"]["total"] == 1
        assert data["data"]["cards"][0]["name"] == "Test Dragon"

    def test_get_cards_unauthenticated(self, client):
        """Should return 401 when not authenticated."""
        response = client.get("/api/v1/cards")

        assert response.status_code == 401


class TestGetCardDetails:
    """Tests for getting card details."""

    def test_get_card_exists(self, auth_client, test_card):
        """Should return card details."""
        response = auth_client.get(f"/api/v1/cards/{test_card['id']}")

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert data["data"]["card"]["name"] == "Test Dragon"
        assert data["data"]["card"]["rarity"] == "rare"

    def test_get_card_not_found(self, auth_client):
        """Should return 404 for non-existent card."""
        response = auth_client.get("/api/v1/cards/99999")

        assert response.status_code == 404


class TestGetDeck:
    """Tests for getting user's deck."""

    def test_get_deck_empty(self, auth_client):
        """Should return empty deck for new user."""
        response = auth_client.get("/api/v1/deck")

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert data["data"]["deck"] == []
        assert data["data"]["size"] == 0

    def test_get_deck_with_cards(self, auth_client, deck_cards):
        """Should return cards in deck."""
        response = auth_client.get("/api/v1/deck")

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert data["data"]["size"] == 3
        assert len(data["data"]["deck"]) == 3


class TestDeckManagement:
    """Tests for deck add/remove operations."""

    def test_add_to_deck(self, auth_client, test_card):
        """Should add card to deck."""
        response = auth_client.post(f"/api/v1/deck/add/{test_card['id']}")

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True

        # Verify card is in deck
        deck_response = auth_client.get("/api/v1/deck")
        assert deck_response.json["data"]["size"] == 1

    def test_remove_from_deck(self, auth_client, deck_cards):
        """Should remove card from deck."""
        card_id = deck_cards[0]["id"]
        response = auth_client.post(f"/api/v1/deck/remove/{card_id}")

        assert response.status_code == 200

        # Verify deck size decreased
        deck_response = auth_client.get("/api/v1/deck")
        assert deck_response.json["data"]["size"] == 2
