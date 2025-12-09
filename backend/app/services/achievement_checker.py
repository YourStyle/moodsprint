"""Achievement checking service."""

from datetime import date, datetime

from app import db
from app.models import Achievement, FocusSession, MoodCheck, Task, User, UserAchievement
from app.models.focus_session import FocusSessionStatus
from app.models.task import TaskStatus


class AchievementChecker:
    """Service for checking and unlocking achievements."""

    def __init__(self, user: User):
        self.user = user

    def check_all(self) -> list[Achievement]:
        """Check all achievements and return newly unlocked ones."""
        unlocked = []

        # Check each achievement type
        unlocked.extend(self._check_task_achievements())
        unlocked.extend(self._check_focus_achievements())
        unlocked.extend(self._check_streak_achievements())
        unlocked.extend(self._check_mood_achievements())
        unlocked.extend(self._check_level_achievements())

        return unlocked

    def _get_or_create_user_achievement(
        self, achievement: Achievement
    ) -> UserAchievement:
        """Get or create a user achievement record."""
        user_achievement = UserAchievement.query.filter_by(
            user_id=self.user.id, achievement_id=achievement.id
        ).first()

        if not user_achievement:
            user_achievement = UserAchievement(
                user_id=self.user.id, achievement_id=achievement.id, progress=0
            )
            db.session.add(user_achievement)

        return user_achievement

    def _check_task_achievements(self) -> list[Achievement]:
        """Check task-related achievements."""
        unlocked = []

        # Count completed tasks
        completed_tasks = Task.query.filter_by(
            user_id=self.user.id, status=TaskStatus.COMPLETED.value
        ).count()

        # First task
        achievement = Achievement.query.filter_by(code="first_task").first()
        if achievement and completed_tasks >= 1:
            user_ach = self._get_or_create_user_achievement(achievement)
            if not user_ach.is_unlocked:
                user_ach.unlock()
                unlocked.append(achievement)

        # Tasks 5
        achievement = Achievement.query.filter_by(code="tasks_5").first()
        if achievement:
            user_ach = self._get_or_create_user_achievement(achievement)
            user_ach.progress = min(completed_tasks, achievement.progress_max or 5)
            if completed_tasks >= 5 and not user_ach.is_unlocked:
                user_ach.unlock()
                unlocked.append(achievement)

        # Tasks 25
        achievement = Achievement.query.filter_by(code="tasks_25").first()
        if achievement:
            user_ach = self._get_or_create_user_achievement(achievement)
            user_ach.progress = min(completed_tasks, achievement.progress_max or 25)
            if completed_tasks >= 25 and not user_ach.is_unlocked:
                user_ach.unlock()
                unlocked.append(achievement)

        # Tasks 100
        achievement = Achievement.query.filter_by(code="tasks_100").first()
        if achievement:
            user_ach = self._get_or_create_user_achievement(achievement)
            user_ach.progress = min(completed_tasks, achievement.progress_max or 100)
            if completed_tasks >= 100 and not user_ach.is_unlocked:
                user_ach.unlock()
                unlocked.append(achievement)

        return unlocked

    def _check_focus_achievements(self) -> list[Achievement]:
        """Check focus-related achievements."""
        unlocked = []

        # Count completed focus sessions
        completed_sessions = FocusSession.query.filter_by(
            user_id=self.user.id, status=FocusSessionStatus.COMPLETED.value
        ).count()

        # First focus
        achievement = Achievement.query.filter_by(code="first_focus").first()
        if achievement and completed_sessions >= 1:
            user_ach = self._get_or_create_user_achievement(achievement)
            if not user_ach.is_unlocked:
                user_ach.unlock()
                unlocked.append(achievement)

        # Focus 5
        achievement = Achievement.query.filter_by(code="focus_5").first()
        if achievement:
            user_ach = self._get_or_create_user_achievement(achievement)
            user_ach.progress = min(completed_sessions, achievement.progress_max or 5)
            if completed_sessions >= 5 and not user_ach.is_unlocked:
                user_ach.unlock()
                unlocked.append(achievement)

        # Focus 25
        achievement = Achievement.query.filter_by(code="focus_25").first()
        if achievement:
            user_ach = self._get_or_create_user_achievement(achievement)
            user_ach.progress = min(completed_sessions, achievement.progress_max or 25)
            if completed_sessions >= 25 and not user_ach.is_unlocked:
                user_ach.unlock()
                unlocked.append(achievement)

        # Focus hour (60 min in one day)
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_minutes = (
            db.session.query(
                db.func.coalesce(db.func.sum(FocusSession.actual_duration_minutes), 0)
            )
            .filter(
                FocusSession.user_id == self.user.id,
                FocusSession.status == FocusSessionStatus.COMPLETED.value,
                FocusSession.started_at >= today_start,
            )
            .scalar()
        )

        achievement = Achievement.query.filter_by(code="focus_hour").first()
        if achievement and today_minutes >= 60:
            user_ach = self._get_or_create_user_achievement(achievement)
            if not user_ach.is_unlocked:
                user_ach.unlock()
                unlocked.append(achievement)

        return unlocked

    def _check_streak_achievements(self) -> list[Achievement]:
        """Check streak-related achievements."""
        unlocked = []
        streak = self.user.streak_days

        streak_achievements = [
            ("streak_3", 3),
            ("streak_7", 7),
            ("streak_14", 14),
            ("streak_30", 30),
        ]

        for code, required_streak in streak_achievements:
            achievement = Achievement.query.filter_by(code=code).first()
            if achievement:
                user_ach = self._get_or_create_user_achievement(achievement)
                user_ach.progress = min(
                    streak, achievement.progress_max or required_streak
                )
                if streak >= required_streak and not user_ach.is_unlocked:
                    user_ach.unlock()
                    unlocked.append(achievement)

        return unlocked

    def _check_mood_achievements(self) -> list[Achievement]:
        """Check mood-related achievements."""
        unlocked = []

        mood_count = MoodCheck.query.filter_by(user_id=self.user.id).count()

        # First mood
        achievement = Achievement.query.filter_by(code="first_mood").first()
        if achievement and mood_count >= 1:
            user_ach = self._get_or_create_user_achievement(achievement)
            if not user_ach.is_unlocked:
                user_ach.unlock()
                unlocked.append(achievement)

        # Mood tracker 5
        achievement = Achievement.query.filter_by(code="mood_tracker_5").first()
        if achievement:
            user_ach = self._get_or_create_user_achievement(achievement)
            user_ach.progress = min(mood_count, achievement.progress_max or 5)
            if mood_count >= 5 and not user_ach.is_unlocked:
                user_ach.unlock()
                unlocked.append(achievement)

        # Mood tracker 20
        achievement = Achievement.query.filter_by(code="mood_tracker_20").first()
        if achievement:
            user_ach = self._get_or_create_user_achievement(achievement)
            user_ach.progress = min(mood_count, achievement.progress_max or 20)
            if mood_count >= 20 and not user_ach.is_unlocked:
                user_ach.unlock()
                unlocked.append(achievement)

        return unlocked

    def _check_level_achievements(self) -> list[Achievement]:
        """Check level-related achievements."""
        unlocked = []
        level = self.user.level

        level_achievements = [("level_3", 3), ("level_5", 5), ("level_10", 10)]

        for code, required_level in level_achievements:
            achievement = Achievement.query.filter_by(code=code).first()
            if achievement:
                user_ach = self._get_or_create_user_achievement(achievement)
                user_ach.progress = min(
                    level, achievement.progress_max or required_level
                )
                if level >= required_level and not user_ach.is_unlocked:
                    user_ach.unlock()
                    unlocked.append(achievement)

        return unlocked
