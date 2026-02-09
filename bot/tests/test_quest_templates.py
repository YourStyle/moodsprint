"""Standalone tests for quest template and prompt integrity (no Flask needed).

We extract the dict data by exec-ing just the data portion of quest.py to avoid
importing the full Flask/SQLAlchemy stack.
"""

import ast
import os


def _load_quest_data():
    """Load QUEST_TEMPLATES and QUEST_NAME_PROMPTS from quest.py without importing app."""
    quest_file = os.path.join(
        os.path.dirname(__file__), "..", "..", "backend", "app", "models", "quest.py"
    )
    with open(quest_file, "r") as f:
        source = f.read()

    # Parse the AST and extract the two dicts
    tree = ast.parse(source)
    data = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in (
                    "QUEST_TEMPLATES",
                    "QUEST_NAME_PROMPTS",
                ):
                    data[target.id] = ast.literal_eval(node.value)
    return data["QUEST_TEMPLATES"], data["QUEST_NAME_PROMPTS"]


QUEST_TEMPLATES, QUEST_NAME_PROMPTS = _load_quest_data()


class TestQuestTemplateIntegrity:
    """Verify quest template and prompt completeness."""

    EXPECTED_TYPES = [
        "early_bird",
        "task_before_noon",
        "streak_tasks",
        "high_priority_first",
        "focus_master",
        "subtask_warrior",
        "mood_tracker",
        "complete_all",
        "arena_battles",
        "merge_cards",
        "collect_rarity",
        "campaign_stars",
        "use_abilities",
    ]

    EXPECTED_GENRES = ["magic", "fantasy", "scifi", "cyberpunk", "anime"]

    def test_all_expected_templates_exist(self):
        """All 13 quest types must be in QUEST_TEMPLATES."""
        for qt in self.EXPECTED_TYPES:
            assert qt in QUEST_TEMPLATES, f"Missing template: {qt}"

    def test_template_fields(self):
        """Each template must have required numeric fields."""
        for name, tmpl in QUEST_TEMPLATES.items():
            assert isinstance(tmpl.get("description"), str), f"{name}: description"
            assert isinstance(tmpl.get("target_count"), int), f"{name}: target_count"
            assert isinstance(tmpl.get("xp_reward"), int), f"{name}: xp_reward"
            assert isinstance(
                tmpl.get("stat_points_reward"), int
            ), f"{name}: stat_points_reward"
            assert tmpl["target_count"] > 0
            assert tmpl["xp_reward"] > 0

    def test_all_genres_present(self):
        """All 5 genres must be in QUEST_NAME_PROMPTS."""
        for genre in self.EXPECTED_GENRES:
            assert genre in QUEST_NAME_PROMPTS, f"Missing genre: {genre}"

    def test_every_genre_has_every_quest_prompt(self):
        """Each genre must have a prompt for every quest type."""
        for genre in self.EXPECTED_GENRES:
            prompts = QUEST_NAME_PROMPTS[genre]
            for qt in self.EXPECTED_TYPES:
                assert qt in prompts, f"Genre '{genre}' missing prompt for '{qt}'"
                assert isinstance(prompts[qt], str)
                assert len(prompts[qt].strip()) > 0

    def test_no_extra_genres(self):
        """No unexpected genres in prompts."""
        for genre in QUEST_NAME_PROMPTS:
            assert genre in self.EXPECTED_GENRES, f"Unexpected genre: {genre}"

    def test_new_card_quest_templates(self):
        """New card/campaign quest types have correct values."""
        assert QUEST_TEMPLATES["arena_battles"]["target_count"] == 2
        assert QUEST_TEMPLATES["merge_cards"]["target_count"] == 1
        assert QUEST_TEMPLATES["collect_rarity"]["target_count"] == 1
        assert QUEST_TEMPLATES["campaign_stars"]["target_count"] == 3
        assert QUEST_TEMPLATES["use_abilities"]["target_count"] == 3
