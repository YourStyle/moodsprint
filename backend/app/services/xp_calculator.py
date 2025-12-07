"""XP calculation service."""


class XPCalculator:
    """Service for calculating XP rewards."""

    # Base XP rewards
    XP_SUBTASK_COMPLETE = 10
    XP_TASK_COMPLETE = 50
    XP_FOCUS_SESSION = 25
    XP_MOOD_CHECK = 5
    XP_DAILY_STREAK_BASE = 20
    XP_DAILY_STREAK_MAX_MULTIPLIER = 7

    @classmethod
    def subtask_completed(cls) -> int:
        """XP for completing a subtask."""
        return cls.XP_SUBTASK_COMPLETE

    @classmethod
    def task_completed(cls) -> int:
        """XP for completing a task."""
        return cls.XP_TASK_COMPLETE

    @classmethod
    def focus_session_completed(cls, duration_minutes: int) -> int:
        """
        XP for completing a focus session.
        Bonus XP for longer sessions.
        """
        base_xp = cls.XP_FOCUS_SESSION

        # Bonus for longer sessions
        if duration_minutes >= 45:
            bonus = 15
        elif duration_minutes >= 30:
            bonus = 10
        elif duration_minutes >= 20:
            bonus = 5
        else:
            bonus = 0

        return base_xp + bonus

    @classmethod
    def mood_check(cls) -> int:
        """XP for logging mood."""
        return cls.XP_MOOD_CHECK

    @classmethod
    def daily_streak(cls, streak_days: int) -> int:
        """
        XP bonus for maintaining a streak.
        Caps at 7 days multiplier.
        """
        multiplier = min(streak_days, cls.XP_DAILY_STREAK_MAX_MULTIPLIER)
        return cls.XP_DAILY_STREAK_BASE * multiplier

    @classmethod
    def daily_goals_bonus(cls) -> int:
        """XP bonus for completing all daily goals."""
        return 30

    @classmethod
    def calculate_level(cls, xp: int) -> int:
        """Calculate level from XP."""
        import math
        if xp < 100:
            return 1
        return int(math.floor(math.sqrt(xp / 100))) + 1

    @classmethod
    def xp_for_level(cls, level: int) -> int:
        """Calculate XP required for a specific level."""
        if level <= 1:
            return 0
        return ((level - 1) ** 2) * 100
