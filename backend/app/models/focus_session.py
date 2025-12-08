"""Focus session model."""

from datetime import datetime
from enum import Enum

from app import db


class FocusSessionStatus(str, Enum):
    """Focus session status enum."""

    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class FocusSession(db.Model):
    """Focus session model for tracking work sessions."""

    __tablename__ = "focus_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subtask_id = db.Column(
        db.Integer, db.ForeignKey("subtasks.id", ondelete="SET NULL"), nullable=True
    )

    planned_duration_minutes = db.Column(db.Integer, default=25, nullable=False)
    actual_duration_minutes = db.Column(db.Integer, nullable=True)

    status = db.Column(
        db.String(20), default=FocusSessionStatus.ACTIVE.value, nullable=False
    )

    # Timestamps
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)
    paused_at = db.Column(db.DateTime, nullable=True)

    # Accumulated pause time in seconds
    total_pause_seconds = db.Column(db.Integer, default=0, nullable=False)

    @property
    def elapsed_minutes(self) -> int:
        """Calculate elapsed time in minutes."""
        if self.ended_at:
            end_time = self.ended_at
        else:
            end_time = datetime.utcnow()

        elapsed_seconds = (end_time - self.started_at).total_seconds()
        elapsed_seconds -= self.total_pause_seconds

        return max(0, int(elapsed_seconds / 60))

    @property
    def remaining_minutes(self) -> int:
        """Calculate remaining time in minutes."""
        return max(0, self.planned_duration_minutes - self.elapsed_minutes)

    @property
    def is_overtime(self) -> bool:
        """Check if session has exceeded planned duration."""
        return self.elapsed_minutes > self.planned_duration_minutes

    def complete(self, complete_subtask: bool = False):
        """Complete the focus session."""
        self.status = FocusSessionStatus.COMPLETED.value
        self.ended_at = datetime.utcnow()
        self.actual_duration_minutes = self.elapsed_minutes

        if complete_subtask and self.subtask:
            self.subtask.complete()

    def cancel(self):
        """Cancel the focus session."""
        self.status = FocusSessionStatus.CANCELLED.value
        self.ended_at = datetime.utcnow()
        self.actual_duration_minutes = self.elapsed_minutes

    def pause(self):
        """Pause the focus session."""
        if self.status == FocusSessionStatus.ACTIVE.value:
            self.status = FocusSessionStatus.PAUSED.value
            self.paused_at = datetime.utcnow()

    def resume(self):
        """Resume the focus session."""
        if self.status == FocusSessionStatus.PAUSED.value and self.paused_at:
            pause_duration = (datetime.utcnow() - self.paused_at).total_seconds()
            self.total_pause_seconds += int(pause_duration)
            self.status = FocusSessionStatus.ACTIVE.value
            self.paused_at = None

    def to_dict(self) -> dict:
        """Convert focus session to dictionary."""
        result = {
            "id": self.id,
            "user_id": self.user_id,
            "subtask_id": self.subtask_id,
            "planned_duration_minutes": self.planned_duration_minutes,
            "actual_duration_minutes": self.actual_duration_minutes,
            "elapsed_minutes": self.elapsed_minutes,
            "remaining_minutes": self.remaining_minutes,
            "is_overtime": self.is_overtime,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
        }

        if self.subtask:
            result["subtask_title"] = self.subtask.title
            result["task_title"] = (
                self.subtask.task.title if self.subtask.task else None
            )

        return result

    def __repr__(self) -> str:
        return f"<FocusSession {self.id}: {self.status}>"
