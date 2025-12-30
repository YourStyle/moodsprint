"""Tests for AI dialogue generation in admin panel."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app import app


@pytest.fixture
def client():
    """Create test client."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def auth_client(client):
    """Create authenticated test client."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True
    return client


class TestDialogueGeneration:
    """Tests for /campaign/generate-dialogue endpoint."""

    def test_unauthenticated(self, client):
        """Should redirect when not authenticated."""
        response = client.post("/campaign/generate-dialogue", json={})
        assert response.status_code == 302  # Redirect to login

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    def test_no_api_key(self, auth_client):
        """Should return error when API key not configured."""
        response = auth_client.post(
            "/campaign/generate-dialogue",
            json={
                "chapter_name": "Test Chapter",
                "chapter_genre": "fantasy",
                "monster_name": "Goblin",
                "dialog_type": "before",
            },
        )

        data = response.json
        assert data["success"] is False
        assert "API key" in data["error"]

    @patch("openai.OpenAI")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_generate_before_dialogue(self, mock_openai_class, auth_client):
        """Should generate dialogue before battle."""
        # Mock the OpenAI response
        mock_response = MagicMock()
        mock_response.id = "resp_test123"
        mock_response.output_text = json.dumps([
            {"speaker": "Monster", "text": "Ты не пройдёшь!", "emoji": "👹"},
            {"speaker": "Hero", "text": "Посмотрим!", "emoji": "🦸"},
        ])

        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        response = auth_client.post(
            "/campaign/generate-dialogue",
            json={
                "chapter_name": "Тёмный лес",
                "chapter_genre": "fantasy",
                "chapter_description": "Древний лес с монстрами",
                "monster_name": "Лесной тролль",
                "dialog_type": "before",
            },
        )

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert "dialogue" in data
        assert len(data["dialogue"]) == 2
        assert data["dialogue"][0]["speaker"] == "Monster"
        assert data["genre"] == "fantasy"

    @patch("openai.OpenAI")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_generate_after_dialogue(self, mock_openai_class, auth_client):
        """Should generate dialogue after battle."""
        mock_response = MagicMock()
        mock_response.id = "resp_test456"
        mock_response.output_text = json.dumps([
            {"speaker": "Monster", "text": "Ты победил...", "emoji": "😵"},
            {"speaker": "Hero", "text": "Справедливость восторжествовала!", "emoji": "🎉"},
        ])

        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        response = auth_client.post(
            "/campaign/generate-dialogue",
            json={
                "chapter_name": "Тёмный лес",
                "chapter_genre": "fantasy",
                "monster_name": "Лесной тролль",
                "dialog_type": "after",
            },
        )

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert len(data["dialogue"]) == 2

    @patch("openai.OpenAI")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_genre_contexts(self, mock_openai_class, auth_client):
        """Should use correct genre context."""
        mock_response = MagicMock()
        mock_response.id = "resp_test789"
        mock_response.output_text = json.dumps([
            {"speaker": "Hero", "text": "Hack the planet!", "emoji": "💻"},
        ])

        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        # Test cyberpunk genre
        response = auth_client.post(
            "/campaign/generate-dialogue",
            json={
                "chapter_name": "Neon District",
                "chapter_genre": "cyberpunk",
                "monster_name": "Corporate AI",
                "dialog_type": "before",
            },
        )

        assert response.status_code == 200

        # Verify the API was called with cyberpunk context
        call_args = mock_client.responses.create.call_args
        assert "cyberpunk" in call_args.kwargs["input"].lower() or \
               "cyberpunk" in str(call_args)

    @patch("openai.OpenAI")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_dialogue_with_events(self, mock_openai_class, auth_client):
        """Should handle dialogue with events."""
        mock_response = MagicMock()
        mock_response.id = "resp_events"
        mock_response.output_text = json.dumps([
            {"speaker": "Monster", "text": "Prepare!", "emoji": "👹"},
            {"speaker": "Narrator", "text": "Battle begins!", "emoji": "⚔️", "event": "start_battle"},
        ])

        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        response = auth_client.post(
            "/campaign/generate-dialogue",
            json={
                "chapter_name": "Test",
                "chapter_genre": "fantasy",
                "monster_name": "Boss",
                "dialog_type": "before",
            },
        )

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        # Check that event is preserved
        narrator_line = next(
            (d for d in data["dialogue"] if d["speaker"] == "Narrator"), None
        )
        assert narrator_line is not None
        assert narrator_line.get("event") == "start_battle"

    @patch("openai.OpenAI")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_invalid_json_response(self, mock_openai_class, auth_client):
        """Should handle invalid JSON from AI."""
        mock_response = MagicMock()
        mock_response.id = "resp_invalid"
        mock_response.output_text = "This is not valid JSON"

        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        response = auth_client.post(
            "/campaign/generate-dialogue",
            json={
                "chapter_name": "Test",
                "chapter_genre": "fantasy",
                "monster_name": "Test",
                "dialog_type": "before",
            },
        )

        assert response.status_code == 200
        data = response.json
        assert data["success"] is False
        assert "Invalid JSON" in data["error"]

    @patch("openai.OpenAI")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_reset_context(self, mock_openai_class, auth_client):
        """Should not use previous_response_id when reset_context is True."""
        mock_response = MagicMock()
        mock_response.id = "resp_new"
        mock_response.output_text = json.dumps([
            {"speaker": "Hero", "text": "Fresh start!", "emoji": "🌟"},
        ])

        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        response = auth_client.post(
            "/campaign/generate-dialogue",
            json={
                "chapter_name": "Test",
                "chapter_genre": "fantasy",
                "monster_name": "Test",
                "dialog_type": "before",
                "reset_context": True,
            },
        )

        assert response.status_code == 200

        # Verify previous_response_id was not passed
        call_kwargs = mock_client.responses.create.call_args.kwargs
        assert "previous_response_id" not in call_kwargs


class TestAIContextsEndpoints:
    """Tests for AI context management endpoints."""

    def test_get_contexts_unauthenticated(self, client):
        """Should redirect when not authenticated."""
        response = client.get("/campaign/ai-contexts")
        assert response.status_code == 302

    def test_get_contexts(self, auth_client):
        """Should return contexts list."""
        response = auth_client.get("/campaign/ai-contexts")

        # May fail if table doesn't exist, but should not crash
        assert response.status_code == 200

    def test_reset_context(self, auth_client):
        """Should reset context for genre."""
        response = auth_client.post("/campaign/ai-contexts/fantasy/reset")

        assert response.status_code == 200

    def test_reset_all_contexts(self, auth_client):
        """Should reset all contexts."""
        response = auth_client.post("/campaign/ai-contexts/reset-all")

        assert response.status_code == 200
