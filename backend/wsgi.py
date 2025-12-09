"""WSGI entry point."""
import os
from app import create_app, db
from app.models.achievement import Achievement, ACHIEVEMENTS

app = create_app(os.environ.get('FLASK_ENV', 'production'))


def init_achievements():
    """Initialize and update default achievements in the database."""
    for ach_data in ACHIEVEMENTS:
        existing = Achievement.query.filter_by(code=ach_data['code']).first()
        if existing:
            # Update existing achievement with new data
            existing.title = ach_data['title']
            existing.description = ach_data['description']
            existing.xp_reward = ach_data.get('xp_reward', 50)
            existing.icon = ach_data.get('icon', 'trophy')
            existing.category = ach_data.get('category', 'general')
            existing.progress_max = ach_data.get('progress_max')
            existing.is_hidden = ach_data.get('is_hidden', False)
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
