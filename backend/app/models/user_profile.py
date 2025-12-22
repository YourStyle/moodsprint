"""User profile model for onboarding and personalization."""

from datetime import date, datetime

from app import db


class UserProfile(db.Model):
    """Extended user profile from onboarding."""

    __tablename__ = "user_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Productivity type from GPT analysis
    productivity_type = db.Column(
        db.String(50), nullable=True
    )  # e.g., 'morning_bird', 'night_owl', 'steady_pace'

    # Preferred work time
    preferred_time = db.Column(
        db.String(20), nullable=True
    )  # morning, afternoon, evening, night

    # Work style
    work_style = db.Column(
        db.String(50), nullable=True
    )  # deep_focus, multitasker, sprinter, marathon

    # Task preferences (JSON array)
    favorite_task_types = db.Column(
        db.JSON, nullable=True
    )  # ['creative', 'analytical', 'communication']

    # Challenges
    main_challenges = db.Column(
        db.JSON, nullable=True
    )  # ['procrastination', 'focus', 'overwhelm']

    # Goals
    productivity_goals = db.Column(db.JSON, nullable=True)

    # Gamification genre preference
    favorite_genre = db.Column(
        db.String(50), nullable=True
    )  # magic, fantasy, scifi, cyberpunk, anime

    # Raw GPT response
    gpt_analysis = db.Column(db.JSON, nullable=True)

    # Onboarding
    onboarding_completed = db.Column(db.Boolean, default=False, nullable=False)
    onboarding_completed_at = db.Column(db.DateTime, nullable=True)

    # Settings based on profile
    notifications_enabled = db.Column(db.Boolean, default=True)
    daily_reminder_time = db.Column(db.String(5), default="09:00")  # HH:MM format
    preferred_session_duration = db.Column(db.Integer, default=25)  # minutes

    # Work schedule preferences
    work_start_time = db.Column(db.String(5), default="09:00")  # HH:MM format
    work_end_time = db.Column(db.String(5), default="18:00")  # HH:MM format
    work_days = db.Column(db.JSON, default=[1, 2, 3, 4, 5])  # 1=Mon, 2=Tue, ..., 7=Sun
    timezone = db.Column(db.String(50), default="Europe/Moscow")

    # Card healing tracking
    heals_today = db.Column(db.Integer, default=0, nullable=False)
    last_heal_date = db.Column(db.Date, nullable=True)

    # Spotlight onboarding reset (set by admin to force re-show spotlight)
    spotlight_reset_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship
    user = db.relationship("User", backref=db.backref("profile", uselist=False))

    def get_heals_today(self) -> int:
        """Get number of heals performed today, resetting if new day."""
        today = date.today()
        if self.last_heal_date != today:
            # New day, reset count
            self.heals_today = 0
            self.last_heal_date = today
        return self.heals_today

    def record_heal(self):
        """Record a heal action."""
        today = date.today()
        if self.last_heal_date != today:
            self.heals_today = 1
            self.last_heal_date = today
        else:
            self.heals_today += 1

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "productivity_type": self.productivity_type,
            "preferred_time": self.preferred_time,
            "work_style": self.work_style,
            "favorite_task_types": self.favorite_task_types,
            "main_challenges": self.main_challenges,
            "productivity_goals": self.productivity_goals,
            "onboarding_completed": self.onboarding_completed,
            "notifications_enabled": self.notifications_enabled,
            "daily_reminder_time": self.daily_reminder_time,
            "preferred_session_duration": self.preferred_session_duration,
            "work_start_time": self.work_start_time,
            "work_end_time": self.work_end_time,
            "work_days": self.work_days,
            "timezone": self.timezone,
            "favorite_genre": self.favorite_genre,
            "spotlight_reset_at": (
                self.spotlight_reset_at.isoformat() if self.spotlight_reset_at else None
            ),
        }

    def __repr__(self) -> str:
        return f"<UserProfile {self.user_id}>"


# Productivity types definitions
PRODUCTIVITY_TYPES = {
    "morning_bird": {
        "name": "Morning Bird",
        "description": "You do your best work in the early hours",
        "emoji": "🌅",
        "tips": [
            "Schedule important tasks before noon",
            "Use morning energy for creative work",
            "Protect your morning routine",
        ],
    },
    "afternoon_peak": {
        "name": "Afternoon Peak",
        "description": "You hit your stride after lunch",
        "emoji": "☀️",
        "tips": [
            "Use mornings for warm-up tasks",
            "Schedule meetings in early afternoon",
            "Save challenging work for 2-5 PM",
        ],
    },
    "night_owl": {
        "name": "Night Owl",
        "description": "You thrive when others are asleep",
        "emoji": "🦉",
        "tips": [
            "Embrace late-night focus sessions",
            "Protect your sleep schedule",
            "Use quiet hours for deep work",
        ],
    },
    "steady_pace": {
        "name": "Steady Pacer",
        "description": "Consistent energy throughout the day",
        "emoji": "⚡",
        "tips": [
            "Maintain regular work blocks",
            "Take consistent breaks",
            "Avoid energy spikes and crashes",
        ],
    },
}

WORK_STYLES = {
    "deep_focus": {
        "name": "Deep Focus",
        "description": "Long, uninterrupted work sessions",
        "recommended_session": 45,
    },
    "sprinter": {
        "name": "Sprinter",
        "description": "Short, intense bursts of productivity",
        "recommended_session": 15,
    },
    "pomodoro": {
        "name": "Pomodoro Master",
        "description": "Classic 25/5 work-break cycles",
        "recommended_session": 25,
    },
    "flexible": {
        "name": "Flexible",
        "description": "Adapts session length to the task",
        "recommended_session": 25,
    },
}
