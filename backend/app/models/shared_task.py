"""Shared task model for task sharing between friends."""

from datetime import datetime
from enum import Enum

from app import db


class SharedTaskStatus(str, Enum):
    """Shared task status enum."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    COMPLETED = "completed"


class SharedTask(db.Model):
    """Task shared between users."""

    __tablename__ = "shared_tasks"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.Integer,
        db.ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assignee_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = db.Column(
        db.String(20), default=SharedTaskStatus.PENDING.value, nullable=False
    )
    message = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    accepted_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Card reward for assignee (generated when owner completes the task)
    reward_card_id = db.Column(
        db.Integer,
        db.ForeignKey("user_cards.id", ondelete="SET NULL"),
        nullable=True,
    )
    reward_shown = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("task_id", "assignee_id", name="unique_shared_task"),
    )

    # Relationships
    task = db.relationship("Task", backref=db.backref("shared_with", lazy="dynamic"))
    owner = db.relationship(
        "User",
        foreign_keys=[owner_id],
        backref=db.backref("shared_tasks_sent", lazy="dynamic"),
    )
    assignee = db.relationship(
        "User",
        foreign_keys=[assignee_id],
        backref=db.backref("shared_tasks_received", lazy="dynamic"),
    )
    reward_card = db.relationship("UserCard", foreign_keys=[reward_card_id])

    def to_dict(self, include_task: bool = False) -> dict:
        """Convert to dictionary."""
        data = {
            "id": self.id,
            "task_id": self.task_id,
            "owner_id": self.owner_id,
            "assignee_id": self.assignee_id,
            "status": self.status,
            "message": self.message,
            "owner_name": self.owner.first_name if self.owner else None,
            "assignee_name": self.assignee.first_name if self.assignee else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }
        if include_task and self.task:
            data["task"] = self.task.to_dict(include_subtasks=True)
        if self.reward_card_id:
            data["reward_card_id"] = self.reward_card_id
            if self.reward_card:
                data["reward_card"] = self.reward_card.to_dict()
        return data
