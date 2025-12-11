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


@app.cli.command("init-card-templates")
@click.option("--genre", default=None, help="Generate for specific genre only")
def init_card_templates_command(genre):
    """Initialize base card templates for all genres (10 per genre)."""
    from app.models.card import CardTemplate
    from app.models.character import GENRE_THEMES

    # Base card templates for each genre
    CARD_TEMPLATES = {
        "magic": [
            {
                "name": "Ученик волшебника",
                "description": "Начинающий маг, изучающий основы магии",
                "base_hp": 45,
                "base_attack": 12,
                "emoji": "🧙",
            },
            {
                "name": "Алхимик",
                "description": "Мастер зелий и трансмутации",
                "base_hp": 50,
                "base_attack": 15,
                "emoji": "⚗️",
            },
            {
                "name": "Чародей огня",
                "description": "Повелевает огненной стихией",
                "base_hp": 40,
                "base_attack": 20,
                "emoji": "🔥",
            },
            {
                "name": "Ледяная ведьма",
                "description": "Хозяйка вечной мерзлоты",
                "base_hp": 55,
                "base_attack": 16,
                "emoji": "❄️",
            },
            {
                "name": "Некромант",
                "description": "Владеет тёмными искусствами",
                "base_hp": 35,
                "base_attack": 22,
                "emoji": "💀",
            },
            {
                "name": "Друид леса",
                "description": "Хранитель древних рощ",
                "base_hp": 60,
                "base_attack": 14,
                "emoji": "🌿",
            },
            {
                "name": "Мастер рун",
                "description": "Высекает руны силы",
                "base_hp": 48,
                "base_attack": 18,
                "emoji": "🔮",
            },
            {
                "name": "Звёздный маг",
                "description": "Черпает силу из созвездий",
                "base_hp": 42,
                "base_attack": 19,
                "emoji": "✨",
            },
            {
                "name": "Архимаг",
                "description": "Познавший все школы магии",
                "base_hp": 65,
                "base_attack": 25,
                "emoji": "⚡",
            },
            {
                "name": "Феникс",
                "description": "Возрождается из пепла",
                "base_hp": 70,
                "base_attack": 28,
                "emoji": "🦅",
            },
        ],
        "fantasy": [
            {
                "name": "Оруженосец",
                "description": "Верный спутник рыцаря",
                "base_hp": 50,
                "base_attack": 12,
                "emoji": "🛡️",
            },
            {
                "name": "Охотник",
                "description": "Мастер ловушек и лука",
                "base_hp": 45,
                "base_attack": 18,
                "emoji": "🏹",
            },
            {
                "name": "Паладин",
                "description": "Святой воин света",
                "base_hp": 65,
                "base_attack": 16,
                "emoji": "⚔️",
            },
            {
                "name": "Варвар",
                "description": "Дикая ярость севера",
                "base_hp": 70,
                "base_attack": 22,
                "emoji": "🪓",
            },
            {
                "name": "Эльф-лучник",
                "description": "Меткий страж лесов",
                "base_hp": 40,
                "base_attack": 20,
                "emoji": "🧝",
            },
            {
                "name": "Гном-кузнец",
                "description": "Создатель легендарного оружия",
                "base_hp": 60,
                "base_attack": 15,
                "emoji": "🔨",
            },
            {
                "name": "Разбойник",
                "description": "Бесшумный охотник за сокровищами",
                "base_hp": 35,
                "base_attack": 24,
                "emoji": "🗡️",
            },
            {
                "name": "Жрица луны",
                "description": "Благословлённая богиней",
                "base_hp": 55,
                "base_attack": 17,
                "emoji": "🌙",
            },
            {
                "name": "Рыцарь дракона",
                "description": "Укротитель драконов",
                "base_hp": 75,
                "base_attack": 26,
                "emoji": "🐲",
            },
            {
                "name": "Король-воин",
                "description": "Защитник королевства",
                "base_hp": 80,
                "base_attack": 30,
                "emoji": "👑",
            },
        ],
        "scifi": [
            {
                "name": "Курсант",
                "description": "Новобранец космофлота",
                "base_hp": 45,
                "base_attack": 14,
                "emoji": "🚀",
            },
            {
                "name": "Инженер",
                "description": "Чинит и улучшает технику",
                "base_hp": 55,
                "base_attack": 12,
                "emoji": "🔧",
            },
            {
                "name": "Пилот истребителя",
                "description": "Ас космических боёв",
                "base_hp": 40,
                "base_attack": 20,
                "emoji": "✈️",
            },
            {
                "name": "Киборг",
                "description": "Слияние человека и машины",
                "base_hp": 60,
                "base_attack": 18,
                "emoji": "🦾",
            },
            {
                "name": "Псионик",
                "description": "Владеет силой разума",
                "base_hp": 35,
                "base_attack": 22,
                "emoji": "🧠",
            },
            {
                "name": "Солдат штурма",
                "description": "Элита космодесанта",
                "base_hp": 65,
                "base_attack": 19,
                "emoji": "🎖️",
            },
            {
                "name": "Ксенобиолог",
                "description": "Изучает инопланетную жизнь",
                "base_hp": 50,
                "base_attack": 16,
                "emoji": "👽",
            },
            {
                "name": "Хакер",
                "description": "Взламывает любые системы",
                "base_hp": 38,
                "base_attack": 21,
                "emoji": "💻",
            },
            {
                "name": "Командор",
                "description": "Лидер космической эскадры",
                "base_hp": 70,
                "base_attack": 25,
                "emoji": "⭐",
            },
            {
                "name": "Искусственный интеллект",
                "description": "Совершенный разум",
                "base_hp": 75,
                "base_attack": 28,
                "emoji": "🤖",
            },
        ],
        "cyberpunk": [
            {
                "name": "Уличный самурай",
                "description": "Клинок в неоновых тенях",
                "base_hp": 50,
                "base_attack": 18,
                "emoji": "⚔️",
            },
            {
                "name": "Нетраннер",
                "description": "Погружается в сеть",
                "base_hp": 35,
                "base_attack": 22,
                "emoji": "🖥️",
            },
            {
                "name": "Медтехник",
                "description": "Лечит тело и душу",
                "base_hp": 55,
                "base_attack": 12,
                "emoji": "💉",
            },
            {
                "name": "Техник",
                "description": "Создаёт и ремонтирует импланты",
                "base_hp": 48,
                "base_attack": 15,
                "emoji": "🔩",
            },
            {
                "name": "Наёмник",
                "description": "Деньги решают всё",
                "base_hp": 60,
                "base_attack": 20,
                "emoji": "🎯",
            },
            {
                "name": "Фиксер",
                "description": "Знает все связи города",
                "base_hp": 45,
                "base_attack": 16,
                "emoji": "🤝",
            },
            {
                "name": "Рокербой",
                "description": "Бунтарь с гитарой",
                "base_hp": 40,
                "base_attack": 19,
                "emoji": "🎸",
            },
            {
                "name": "Корпорат",
                "description": "Хозяин мегакорпорации",
                "base_hp": 42,
                "base_attack": 23,
                "emoji": "💼",
            },
            {
                "name": "Легенда улиц",
                "description": "Имя, которое знают все",
                "base_hp": 65,
                "base_attack": 26,
                "emoji": "🌆",
            },
            {
                "name": "Призрак сети",
                "description": "Существует только в киберпространстве",
                "base_hp": 70,
                "base_attack": 30,
                "emoji": "👻",
            },
        ],
        "anime": [
            {
                "name": "Юный герой",
                "description": "Только начал свой путь",
                "base_hp": 45,
                "base_attack": 15,
                "emoji": "⭐",
            },
            {
                "name": "Ниндзя-новичок",
                "description": "Постигает путь тени",
                "base_hp": 40,
                "base_attack": 18,
                "emoji": "🥷",
            },
            {
                "name": "Маг-целитель",
                "description": "Защищает друзей",
                "base_hp": 55,
                "base_attack": 12,
                "emoji": "💖",
            },
            {
                "name": "Мечник",
                "description": "Путь меча бесконечен",
                "base_hp": 50,
                "base_attack": 20,
                "emoji": "⚔️",
            },
            {
                "name": "Призыватель духов",
                "description": "Дружит с потусторонним",
                "base_hp": 42,
                "base_attack": 22,
                "emoji": "👻",
            },
            {
                "name": "Боевой монах",
                "description": "Сила тела и духа",
                "base_hp": 60,
                "base_attack": 17,
                "emoji": "👊",
            },
            {
                "name": "Принцесса-воин",
                "description": "Благородство и отвага",
                "base_hp": 48,
                "base_attack": 19,
                "emoji": "👸",
            },
            {
                "name": "Мастер кунг-фу",
                "description": "Непревзойдённый в бою",
                "base_hp": 52,
                "base_attack": 24,
                "emoji": "🥋",
            },
            {
                "name": "Легендарный сеннин",
                "description": "Познал все техники",
                "base_hp": 70,
                "base_attack": 27,
                "emoji": "🔥",
            },
            {
                "name": "Избранный",
                "description": "Спаситель мира",
                "base_hp": 80,
                "base_attack": 32,
                "emoji": "🌟",
            },
        ],
    }

    click.echo("Initializing card templates...")

    genres_to_process = [genre] if genre else list(GENRE_THEMES.keys())

    for g in genres_to_process:
        if g not in CARD_TEMPLATES:
            click.echo(f"  {g}: no templates defined, skipping")
            continue

        # Check existing count
        existing_count = CardTemplate.query.filter_by(genre=g, is_active=True).count()
        if existing_count >= 10:
            click.echo(f"  {g}: already has {existing_count} templates, skipping")
            continue

        templates = CARD_TEMPLATES[g]
        created = 0

        for template_data in templates:
            # Check if template already exists
            existing = CardTemplate.query.filter_by(
                name=template_data["name"], genre=g
            ).first()
            if existing:
                continue

            template = CardTemplate(
                name=template_data["name"],
                description=template_data["description"],
                genre=g,
                base_hp=template_data["base_hp"],
                base_attack=template_data["base_attack"],
                emoji=template_data["emoji"],
                ai_generated=False,
                is_active=True,
            )
            db.session.add(template)
            created += 1

        db.session.commit()
        click.echo(f"  {g}: {created} templates created")

    click.echo("Done!")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
