"""Task model."""

from datetime import date, datetime
from enum import Enum

from app import db


class TaskStatus(str, Enum):
    """Task status enum."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskPriority(str, Enum):
    """Task priority enum."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Task(db.Model):
    """Task model."""

    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=True)
    priority = db.Column(
        db.String(20), default=TaskPriority.MEDIUM.value, nullable=False
    )
    status = db.Column(db.String(20), default=TaskStatus.PENDING.value, nullable=False)
    due_date = db.Column(db.Date, default=date.today, nullable=True, index=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    subtasks = db.relationship(
        "Subtask",
        backref="task",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="Subtask.order",
    )

    @property
    def subtasks_count(self) -> int:
        """Get total subtasks count."""
        return self.subtasks.count()

    @property
    def subtasks_completed(self) -> int:
        """Get completed subtasks count."""
        from app.models.subtask import SubtaskStatus

        return self.subtasks.filter_by(status=SubtaskStatus.COMPLETED.value).count()

    @property
    def progress_percent(self) -> int:
        """Calculate completion percentage."""
        total = self.subtasks_count
        if total == 0:
            return 0
        return int((self.subtasks_completed / total) * 100)

    def update_status_from_subtasks(self):
        """Update task status based on subtask completion."""
        total = self.subtasks_count
        completed = self.subtasks_completed

        if total == 0:
            return

        if completed == total:
            self.status = TaskStatus.COMPLETED.value
            self.completed_at = datetime.utcnow()
        elif completed > 0:
            self.status = TaskStatus.IN_PROGRESS.value
            self.completed_at = None
        else:
            self.status = TaskStatus.PENDING.value
            self.completed_at = None

    def to_dict(self, include_subtasks: bool = False) -> dict:
        """Convert task to dictionary."""
        result = {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "subtasks_count": self.subtasks_count,
            "subtasks_completed": self.subtasks_completed,
            "progress_percent": self.progress_percent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }

        if include_subtasks:
            result["subtasks"] = [
                s.to_dict() for s in self.subtasks.order_by("order").all()
            ]

        return result

    def __repr__(self) -> str:
        return f"<Task {self.id}: {self.title[:30]}>"
