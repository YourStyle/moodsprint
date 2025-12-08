"""User activity logging model."""

from datetime import datetime
from enum import Enum

from app import db


class ActivityType(str, Enum):
    """Activity type enum."""

    # Auth
    LOGIN = "login"
    LOGOUT = "logout"

    # Tasks
    TASK_CREATE = "task_create"
    TASK_UPDATE = "task_update"
    TASK_COMPLETE = "task_complete"
    TASK_DELETE = "task_delete"

    # Subtasks
    SUBTASK_COMPLETE = "subtask_complete"
    SUBTASK_SKIP = "subtask_skip"

    # Focus
    FOCUS_START = "focus_start"
    FOCUS_COMPLETE = "focus_complete"
    FOCUS_CANCEL = "focus_cancel"
    FOCUS_PAUSE = "focus_pause"

    # Mood
    MOOD_CHECK = "mood_check"

    # Gamification
    LEVEL_UP = "level_up"
    ACHIEVEMENT_UNLOCK = "achievement_unlock"
    STREAK_UPDATE = "streak_update"

    # App
    APP_OPEN = "app_open"
    ONBOARDING_COMPLETE = "onboarding_complete"


class UserActivityLog(db.Model):
    """User activity log for analytics."""

    __tablename__ = "user_activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    action_type = db.Column(db.String(50), nullable=False, index=True)
    action_details = db.Column(db.Text, nullable=True)

    # Context
    entity_type = db.Column(
        db.String(50), nullable=True
    )  # task, subtask, session, etc.
    entity_id = db.Column(db.Integer, nullable=True)

    # Metadata
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)

    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    @classmethod
    def log(
        cls,
        user_id: int,
        action_type: str | ActivityType,
        action_details: str | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):
        """Create a new activity log entry."""
        if isinstance(action_type, ActivityType):
            action_type = action_type.value

        log_entry = cls(
            user_id=user_id,
            action_type=action_type,
            action_details=action_details,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.session.add(log_entry)
        return log_entry

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action_type": self.action_type,
            "action_details": self.action_details,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<ActivityLog {self.id}: {self.action_type}>"
