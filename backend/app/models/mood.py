"""Mood check model."""
from datetime import datetime
from app import db


class MoodCheck(db.Model):
    """Mood check model for tracking user's mood and energy."""

    __tablename__ = 'mood_checks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Mood and energy on scale 1-5
    mood = db.Column(db.Integer, nullable=False)  # 1=very low, 5=great
    energy = db.Column(db.Integer, nullable=False)  # 1=exhausted, 5=peak

    note = db.Column(db.String(500), nullable=True)

    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Mood labels for display
    MOOD_LABELS = {
        1: 'Very Low',
        2: 'Low',
        3: 'Neutral',
        4: 'Good',
        5: 'Great'
    }

    ENERGY_LABELS = {
        1: 'Exhausted',
        2: 'Tired',
        3: 'Normal',
        4: 'Energized',
        5: 'Peak'
    }

    @property
    def mood_label(self) -> str:
        """Get mood label."""
        return self.MOOD_LABELS.get(self.mood, 'Unknown')

    @property
    def energy_label(self) -> str:
        """Get energy label."""
        return self.ENERGY_LABELS.get(self.energy, 'Unknown')

    @property
    def decomposition_strategy(self) -> str:
        """
        Determine task decomposition strategy based on mood and energy.
        Returns: micro, gentle, careful, or standard
        """
        avg = (self.mood + self.energy) / 2

        if avg <= 2:
            return 'micro'  # Very small steps, frequent breaks
        elif avg <= 3:
            if self.energy <= 2:
                return 'careful'  # Medium steps, frequent breaks
            return 'gentle'  # Medium steps, moderate breaks
        else:
            return 'standard'  # Normal steps

    @property
    def recommended_step_minutes(self) -> tuple[int, int]:
        """Get recommended step duration range in minutes."""
        strategy = self.decomposition_strategy
        return {
            'micro': (5, 10),
            'gentle': (10, 15),
            'careful': (10, 15),
            'standard': (15, 25)
        }.get(strategy, (15, 25))

    def to_dict(self) -> dict:
        """Convert mood check to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'mood': self.mood,
            'mood_label': self.mood_label,
            'energy': self.energy,
            'energy_label': self.energy_label,
            'note': self.note,
            'strategy': self.decomposition_strategy,
            'recommended_step_minutes': self.recommended_step_minutes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self) -> str:
        return f'<MoodCheck {self.id}: mood={self.mood}, energy={self.energy}>'
