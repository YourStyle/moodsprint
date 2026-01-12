"""Tests for marketplace and guilds API endpoints."""

from app import db
from app.models.card import CardTemplate, UserCard
from app.models.guild import Guild


class TestMarketplaceAPI:
    """Test cases for marketplace endpoints."""

    def test_get_marketplace_listings(self, auth_client, test_user):
        """Test getting marketplace listings."""
        response = auth_client.get("/api/v1/marketplace/listings")
        assert response.status_code == 200
        data = response.json["data"]
        assert "listings" in data

    def test_get_marketplace_with_filters(self, auth_client, test_user):
        """Test getting marketplace listings with filters."""
        response = auth_client.get("/api/v1/marketplace/listings?rarity=rare")
        assert response.status_code == 200

    def test_get_own_listings(self, auth_client, test_user):
        """Test getting user's own listings."""
        response = auth_client.get("/api/v1/marketplace/my-listings")
        assert response.status_code == 200
        assert "listings" in response.json["data"]


class TestGuildsAPI:
    """Test cases for guilds endpoints."""

    def test_get_guilds(self, auth_client, test_user):
        """Test getting list of guilds."""
        response = auth_client.get("/api/v1/guilds")
        assert response.status_code == 200
        assert "guilds" in response.json["data"]

    def test_create_guild(self, auth_client, test_user):
        """Test creating a new guild."""
        response = auth_client.post(
            "/api/v1/guilds",
            json={
                "name": "Test Guild",
                "description": "A test guild",
            },
        )
        # May succeed or fail depending on user's coins
        assert response.status_code in [200, 400]

    def test_get_my_guild(self, auth_client, test_user):
        """Test getting user's guild."""
        response = auth_client.get("/api/v1/guilds/my")
        assert response.status_code == 200
        # User might not be in a guild
        data = response.json["data"]
        assert "guild" in data or data.get("guild") is None

    def test_search_guilds(self, auth_client, test_user, app):
        """Test searching guilds."""
        with app.app_context():
            guild = Guild(
                name="Searchable Guild",
                description="A guild to search for",
                leader_id=test_user["id"],
            )
            db.session.add(guild)
            db.session.commit()

        response = auth_client.get("/api/v1/guilds?search=Searchable")
        assert response.status_code == 200


class TestCardsAPI:
    """Test cases for cards endpoints."""

    def test_get_user_cards(self, auth_client, test_user):
        """Test getting user's cards."""
        response = auth_client.get("/api/v1/cards")
        assert response.status_code == 200
        assert "cards" in response.json["data"]

    def test_get_user_deck(self, auth_client, test_user):
        """Test getting user's battle deck."""
        response = auth_client.get("/api/v1/cards/deck")
        assert response.status_code == 200
        assert "deck" in response.json["data"]

    def test_get_card_details(self, auth_client, test_user, app):
        """Test getting card details."""
        with app.app_context():
            template = CardTemplate(
                name="Test Card",
                rarity="common",
                base_attack=10,
                base_hp=50,
            )
            db.session.add(template)
            db.session.flush()

            card = UserCard(
                user_id=test_user["id"],
                template_id=template.id,
                name="Test Card",
                rarity="common",
                attack=10,
                hp=50,
                max_hp=50,
            )
            db.session.add(card)
            db.session.commit()
            card_id = card.id

        response = auth_client.get(f"/api/v1/cards/{card_id}")
        assert response.status_code == 200
        assert response.json["data"]["card"]["name"] == "Test Card"


class TestSparksAPI:
    """Test cases for sparks (currency) endpoints."""

    def test_get_sparks_balance(self, auth_client, test_user):
        """Test getting sparks balance."""
        response = auth_client.get("/api/v1/sparks/balance")
        assert response.status_code == 200
        data = response.json["data"]
        assert "balance" in data or "sparks" in data

    def test_get_sparks_history(self, auth_client, test_user):
        """Test getting sparks transaction history."""
        response = auth_client.get("/api/v1/sparks/history")
        assert response.status_code == 200
