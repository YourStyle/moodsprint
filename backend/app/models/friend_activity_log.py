"""Friend activity log model for tracking notable friend events."""

from datetime import datetime

from app import db


class FriendActivityLog(db.Model):
    """Log of notable user activities that friends should be notified about."""

    __tablename__ = "friend_activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_type = db.Column(db.String(50), nullable=False)
    activity_data = db.Column(db.JSON, nullable=True)
    notified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @classmethod
    def create(cls, user_id: int, activity_type: str, activity_data: dict = None):
        """Create a new activity log entry."""
        log = cls(
            user_id=user_id,
            activity_type=activity_type,
            activity_data=activity_data,
        )
        db.session.add(log)
        return log

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "activity_type": self.activity_type,
            "activity_data": self.activity_data,
            "notified": self.notified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
