"""AI usage logging model for tracking OpenAI API costs."""

from datetime import datetime, timezone

from app import db


class AIUsageLog(db.Model):
    __tablename__ = "ai_usage_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
    )
    service_name = db.Column(db.String(100), nullable=False, index=True)
    model = db.Column(db.String(50), nullable=False)
    prompt_tokens = db.Column(db.Integer, nullable=False, default=0)
    completion_tokens = db.Column(db.Integer, nullable=False, default=0)
    total_tokens = db.Column(db.Integer, nullable=False, default=0)
    estimated_cost_usd = db.Column(db.Float, nullable=False, default=0.0)
    latency_ms = db.Column(db.Integer, nullable=True)
    endpoint = db.Column(db.String(100), nullable=False, index=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    user = db.relationship("User", backref=db.backref("ai_usage_logs", lazy="dynamic"))

    def __repr__(self):
        return (
            f"<AIUsageLog {self.service_name} {self.model} "
            f"{self.total_tokens}t ${self.estimated_cost_usd:.4f}>"
        )
