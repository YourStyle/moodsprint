"""Postpone log model for tracking task postponements."""

from datetime import date, datetime

from app import db


class PostponeLog(db.Model):
    """Log of daily task postponements per user."""

    __tablename__ = "postpone_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date = db.Column(db.Date, default=date.today, nullable=False, index=True)
    tasks_postponed = db.Column(db.Integer, default=0, nullable=False)
    priority_changes = db.Column(
        db.JSON, nullable=True
    )  # [{task_id, old, new, reason}]
    notified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Unique constraint: one log per user per day
    __table_args__ = (
        db.UniqueConstraint("user_id", "date", name="uq_user_date_postpone"),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "date": self.date.isoformat() if self.date else None,
            "tasks_postponed": self.tasks_postponed,
            "priority_changes": self.priority_changes or [],
            "notified": self.notified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<PostponeLog user={self.user_id} date={self.date} count={self.tasks_postponed}>"
