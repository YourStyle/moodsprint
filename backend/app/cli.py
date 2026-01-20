"""CLI commands for Flask application."""

import click
from flask.cli import with_appcontext


@click.group()
def translate():
    """Translation commands."""
    pass


@translate.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be translated without making changes",
)
@with_appcontext
def content(dry_run):
    """Translate database content from Russian to English using OpenAI."""
    from app import db
    from app.models import (
        CampaignChapter,
        CampaignLevel,
        CampaignReward,
        CardTemplate,
        Monster,
        MonsterCard,
    )
    from app.services.openai_client import get_openai_client

    client = get_openai_client()
    if not client:
        click.echo("Error: OpenAI client not available. Check OPENAI_API_KEY config.")
        return

    def translate_text(text: str) -> str:
        """Translate Russian text to English using OpenAI."""
        if not text:
            return ""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a translator. Translate the following Russian "
                            "text to English. Keep the same style and tone. "
                            "Only return the translation, nothing else."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                max_tokens=500,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            click.echo(f"    Error translating: {e}")
            return ""

    # Translate CardTemplates
    click.echo("Translating CardTemplates...")
    templates = CardTemplate.query.filter(
        (CardTemplate.name_en.is_(None)) | (CardTemplate.name_en == "")
    ).all()
    click.echo(f"  Found {len(templates)} templates to translate")

    for template in templates:
        if dry_run:
            click.echo(f"  Would translate: {template.name}")
        else:
            click.echo(f"  Translating: {template.name}")
            template.name_en = translate_text(template.name)
            if template.description:
                template.description_en = translate_text(template.description)
            db.session.commit()
            click.echo(f"    -> {template.name_en}")

    # Translate Monsters
    click.echo("\nTranslating Monsters...")
    monsters = Monster.query.filter(
        (Monster.name_en.is_(None)) | (Monster.name_en == "")
    ).all()
    click.echo(f"  Found {len(monsters)} monsters to translate")

    for monster in monsters:
        if dry_run:
            click.echo(f"  Would translate: {monster.name}")
        else:
            click.echo(f"  Translating: {monster.name}")
            monster.name_en = translate_text(monster.name)
            if monster.description:
                monster.description_en = translate_text(monster.description)
            db.session.commit()
            click.echo(f"    -> {monster.name_en}")

    # Translate MonsterCards
    click.echo("\nTranslating MonsterCards...")
    monster_cards = MonsterCard.query.filter(
        (MonsterCard.name_en.is_(None)) | (MonsterCard.name_en == "")
    ).all()
    click.echo(f"  Found {len(monster_cards)} monster cards to translate")

    for card in monster_cards:
        if dry_run:
            click.echo(f"  Would translate: {card.name}")
        else:
            click.echo(f"  Translating: {card.name}")
            card.name_en = translate_text(card.name)
            if card.description:
                card.description_en = translate_text(card.description)
            db.session.commit()
            click.echo(f"    -> {card.name_en}")

    # Translate CampaignChapters
    click.echo("\nTranslating CampaignChapters...")
    chapters = CampaignChapter.query.filter(
        (CampaignChapter.name_en.is_(None)) | (CampaignChapter.name_en == "")
    ).all()
    click.echo(f"  Found {len(chapters)} chapters to translate")

    for chapter in chapters:
        if dry_run:
            click.echo(f"  Would translate: {chapter.name}")
        else:
            click.echo(f"  Translating: {chapter.name}")
            chapter.name_en = translate_text(chapter.name)
            if chapter.description:
                chapter.description_en = translate_text(chapter.description)
            if chapter.story_intro:
                chapter.story_intro_en = translate_text(chapter.story_intro)
            if chapter.story_outro:
                chapter.story_outro_en = translate_text(chapter.story_outro)
            db.session.commit()
            click.echo(f"    -> {chapter.name_en}")

    # Translate CampaignLevels
    click.echo("\nTranslating CampaignLevels...")
    levels = CampaignLevel.query.filter(
        (CampaignLevel.title_en.is_(None)) | (CampaignLevel.title_en == "")
    ).all()
    click.echo(f"  Found {len(levels)} levels to translate")

    for level in levels:
        if dry_run:
            click.echo(f"  Would translate: {level.title}")
        else:
            click.echo(f"  Translating: {level.title}")
            if level.title:
                level.title_en = translate_text(level.title)
            # Translate dialogue_before and dialogue_after JSON if present
            if level.dialogue_before:
                level.dialogue_before_en = translate_json_dialogues(
                    level.dialogue_before, translate_text
                )
            if level.dialogue_after:
                level.dialogue_after_en = translate_json_dialogues(
                    level.dialogue_after, translate_text
                )
            db.session.commit()
            click.echo(f"    -> {level.title_en}")

    # Translate CampaignRewards
    click.echo("\nTranslating CampaignRewards...")
    rewards = CampaignReward.query.filter(
        (CampaignReward.name_en.is_(None)) | (CampaignReward.name_en == "")
    ).all()
    click.echo(f"  Found {len(rewards)} rewards to translate")

    for reward in rewards:
        if dry_run:
            click.echo(f"  Would translate: {reward.name}")
        else:
            if reward.name:
                click.echo(f"  Translating: {reward.name}")
                reward.name_en = translate_text(reward.name)
                if reward.description:
                    reward.description_en = translate_text(reward.description)
                db.session.commit()
                click.echo(f"    -> {reward.name_en}")

    click.echo("\nTranslation complete!")


def translate_json_dialogues(dialogues, translate_func):
    """Translate dialogue JSON structure."""
    if not dialogues:
        return None

    if isinstance(dialogues, list):
        translated = []
        for item in dialogues:
            if isinstance(item, dict):
                translated_item = item.copy()
                if "text" in translated_item:
                    translated_item["text"] = translate_func(translated_item["text"])
                translated.append(translated_item)
            else:
                translated.append(item)
        return translated
    return dialogues


def init_app(app):
    """Register CLI commands with the app."""
    app.cli.add_command(translate)
