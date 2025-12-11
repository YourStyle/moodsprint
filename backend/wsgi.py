"""WSGI entry point."""

import os

import click

from app import create_app, db
from app.models.achievement import ACHIEVEMENTS, Achievement

app = create_app(os.environ.get("FLASK_ENV", "production"))


def init_achievements():
    """Initialize and update default achievements in the database."""
    for ach_data in ACHIEVEMENTS:
        existing = Achievement.query.filter_by(code=ach_data["code"]).first()
        if existing:
            # Update existing achievement with new data
            existing.title = ach_data["title"]
            existing.description = ach_data["description"]
            existing.xp_reward = ach_data.get("xp_reward", 50)
            existing.icon = ach_data.get("icon", "trophy")
            existing.category = ach_data.get("category", "general")
            existing.progress_max = ach_data.get("progress_max")
            existing.is_hidden = ach_data.get("is_hidden", False)
        else:
            achievement = Achievement(**ach_data)
            db.session.add(achievement)

    db.session.commit()


# Initialize achievements on startup
with app.app_context():
    db.create_all()
    try:
        init_achievements()
    except Exception as e:
        print(f"Warning: Failed to init achievements: {e}")


@app.cli.command("generate-monsters")
@click.option("--no-images", is_flag=True, help="Skip image generation")
def generate_monsters_command(no_images):
    """Generate daily monsters for all genres using AI."""
    from app.services.monster_generator import MonsterGeneratorService

    click.echo("Starting daily monster generation...")
    service = MonsterGeneratorService()
    results = service.generate_daily_monsters(generate_images=not no_images)

    for genre, count in results.items():
        if count > 0:
            click.echo(f"  {genre}: {count} monsters generated")
        else:
            click.echo(f"  {genre}: skipped (already exist or error)")

    total = sum(results.values())
    click.echo(f"Done! Total monsters generated: {total}")


@app.cli.command("init-monsters")
@click.option("--genre", default=None, help="Generate for specific genre only")
@click.option("--no-images", is_flag=True, help="Skip image generation")
def init_monsters_command(genre, no_images):
    """Initialize monsters from scratch (useful for first-time setup)."""
    from datetime import date

    from app.models.character import GENRE_THEMES, DailyMonster
    from app.services.monster_generator import MonsterGeneratorService

    click.echo("Initializing monsters...")
    service = MonsterGeneratorService()

    genres = [genre] if genre else list(GENRE_THEMES.keys())
    today = date.today()

    for g in genres:
        # Check if monsters exist for today
        existing = DailyMonster.query.filter_by(genre=g, date=today).first()
        if existing:
            click.echo(f"  {g}: monsters already exist for today, skipping")
            continue

        click.echo(f"  Generating monsters for {g}...")
        try:
            monsters_data = service.generate_monsters_for_genre(g, count=6)

            for i, mdata in enumerate(monsters_data):
                monster = service.create_monster_from_data(
                    mdata, g, generate_image=not no_images
                )
                db.session.add(monster)
                db.session.flush()

                daily = DailyMonster(
                    monster_id=monster.id, genre=g, date=today, slot_number=i + 1
                )
                db.session.add(daily)

            db.session.commit()
            click.echo(f"  {g}: {len(monsters_data)} monsters created")

        except Exception as e:
            db.session.rollback()
            click.echo(f"  {g}: ERROR - {e}")

    click.echo("Done!")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
