"""Achievement checking service."""
from datetime import date, datetime
from app import db
from app.models import User, Achievement, UserAchievement, Task, FocusSession, MoodCheck
from app.models.task import TaskStatus
from app.models.focus_session import FocusSessionStatus


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

    def _get_or_create_user_achievement(self, achievement: Achievement) -> UserAchievement:
        """Get or create a user achievement record."""
        user_achievement = UserAchievement.query.filter_by(
            user_id=self.user.id,
            achievement_id=achievement.id
        ).first()

        if not user_achievement:
            user_achievement = UserAchievement(
                user_id=self.user.id,
                achievement_id=achievement.id,
                progress=0
            )
            db.session.add(user_achievement)

        return user_achievement

    def _check_task_achievements(self) -> list[Achievement]:
        """Check task-related achievements."""
        unlocked = []

        # Count completed tasks
        completed_tasks = Task.query.filter_by(
            user_id=self.user.id,
            status=TaskStatus.COMPLETED.value
        ).count()

        # First task
        achievement = Achievement.query.filter_by(code='first_task').first()
        if achievement and completed_tasks >= 1:
            user_ach = self._get_or_create_user_achievement(achievement)
            if not user_ach.is_unlocked:
                user_ach.unlock()
                unlocked.append(achievement)

        # Task master 10
        achievement = Achievement.query.filter_by(code='task_master_10').first()
        if achievement:
            user_ach = self._get_or_create_user_achievement(achievement)
            user_ach.progress = min(completed_tasks, achievement.progress_max or 10)
            if completed_tasks >= 10 and not user_ach.is_unlocked:
                user_ach.unlock()
                unlocked.append(achievement)

        # Task master 50
        achievement = Achievement.query.filter_by(code='task_master_50').first()
        if achievement:
            user_ach = self._get_or_create_user_achievement(achievement)
            user_ach.progress = min(completed_tasks, achievement.progress_max or 50)
            if completed_tasks >= 50 and not user_ach.is_unlocked:
                user_ach.unlock()
                unlocked.append(achievement)

        return unlocked

    def _check_focus_achievements(self) -> list[Achievement]:
        """Check focus-related achievements."""
        unlocked = []

        # Count completed focus sessions
        completed_sessions = FocusSession.query.filter_by(
            user_id=self.user.id,
            status=FocusSessionStatus.COMPLETED.value
        ).count()

        # First focus
        achievement = Achievement.query.filter_by(code='first_focus').first()
        if achievement and completed_sessions >= 1:
            user_ach = self._get_or_create_user_achievement(achievement)
            if not user_ach.is_unlocked:
                user_ach.unlock()
                unlocked.append(achievement)

        # Focus master 10
        achievement = Achievement.query.filter_by(code='focus_master_10').first()
        if achievement:
            user_ach = self._get_or_create_user_achievement(achievement)
            user_ach.progress = min(completed_sessions, achievement.progress_max or 10)
            if completed_sessions >= 10 and not user_ach.is_unlocked:
                user_ach.unlock()
                unlocked.append(achievement)

        # Focus hour (60 min in one day)
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_minutes = db.session.query(
            db.func.coalesce(db.func.sum(FocusSession.actual_duration_minutes), 0)
        ).filter(
            FocusSession.user_id == self.user.id,
            FocusSession.status == FocusSessionStatus.COMPLETED.value,
            FocusSession.started_at >= today_start
        ).scalar()

        achievement = Achievement.query.filter_by(code='focus_hour').first()
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
            ('streak_3', 3),
            ('streak_7', 7),
            ('streak_30', 30)
        ]

        for code, required_streak in streak_achievements:
            achievement = Achievement.query.filter_by(code=code).first()
            if achievement:
                user_ach = self._get_or_create_user_achievement(achievement)
                user_ach.progress = min(streak, achievement.progress_max or required_streak)
                if streak >= required_streak and not user_ach.is_unlocked:
                    user_ach.unlock()
                    unlocked.append(achievement)

        return unlocked

    def _check_mood_achievements(self) -> list[Achievement]:
        """Check mood-related achievements."""
        unlocked = []

        mood_count = MoodCheck.query.filter_by(user_id=self.user.id).count()

        # Mood tracker 10
        achievement = Achievement.query.filter_by(code='mood_tracker').first()
        if achievement:
            user_ach = self._get_or_create_user_achievement(achievement)
            user_ach.progress = min(mood_count, achievement.progress_max or 10)
            if mood_count >= 10 and not user_ach.is_unlocked:
                user_ach.unlock()
                unlocked.append(achievement)

        # Mood master 50
        achievement = Achievement.query.filter_by(code='mood_master').first()
        if achievement:
            user_ach = self._get_or_create_user_achievement(achievement)
            user_ach.progress = min(mood_count, achievement.progress_max or 50)
            if mood_count >= 50 and not user_ach.is_unlocked:
                user_ach.unlock()
                unlocked.append(achievement)

        return unlocked

    def _check_level_achievements(self) -> list[Achievement]:
        """Check level-related achievements."""
        unlocked = []
        level = self.user.level

        level_achievements = [
            ('level_5', 5),
            ('level_10', 10)
        ]

        for code, required_level in level_achievements:
            achievement = Achievement.query.filter_by(code=code).first()
            if achievement:
                user_ach = self._get_or_create_user_achievement(achievement)
                user_ach.progress = min(level, achievement.progress_max or required_level)
                if level >= required_level and not user_ach.is_unlocked:
                    user_ach.unlock()
                    unlocked.append(achievement)

        return unlocked
