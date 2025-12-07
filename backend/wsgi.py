"""WSGI entry point."""
import os
from app import create_app, db
from app.models.achievement import Achievement, ACHIEVEMENTS

app = create_app(os.environ.get('FLASK_ENV', 'production'))


def init_achievements():
    """Initialize default achievements in the database."""
    with app.app_context():
        for ach_data in ACHIEVEMENTS:
            existing = Achievement.query.filter_by(code=ach_data['code']).first()
            if not existing:
                achievement = Achievement(**ach_data)
                db.session.add(achievement)

        db.session.commit()


# Initialize achievements on startup
with app.app_context():
    db.create_all()
    init_achievements()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
