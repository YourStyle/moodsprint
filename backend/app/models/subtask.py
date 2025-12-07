"""Subtask model."""
from datetime import datetime
from enum import Enum
from app import db


class SubtaskStatus(str, Enum):
    """Subtask status enum."""
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    SKIPPED = 'skipped'


class Subtask(db.Model):
    """Subtask (step) model."""

    __tablename__ = 'subtasks'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, index=True)

    title = db.Column(db.String(500), nullable=False)
    order = db.Column(db.Integer, default=0, nullable=False)
    estimated_minutes = db.Column(db.Integer, default=15, nullable=False)
    status = db.Column(db.String(20), default=SubtaskStatus.PENDING.value, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    focus_sessions = db.relationship('FocusSession', backref='subtask', lazy='dynamic')

    def complete(self):
        """Mark subtask as completed."""
        self.status = SubtaskStatus.COMPLETED.value
        self.completed_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert subtask to dictionary."""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'title': self.title,
            'order': self.order,
            'estimated_minutes': self.estimated_minutes,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

    def __repr__(self) -> str:
        return f'<Subtask {self.id}: {self.title[:30]}>'
