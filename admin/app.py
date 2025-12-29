"""Admin panel application."""

import os
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "admin-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "postgresql://moodsprint:moodsprint@db:5432/moodsprint"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Admin credentials (in production, use proper auth)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "moodsprint")

# Backend API URL and bot secret for calling protected endpoints
API_URL = os.environ.get("API_URL", "http://backend:5000")
BOT_SECRET = os.environ.get("BOT_SECRET", "")


def login_required(f):
    """Login required decorator."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/login", methods=["GET", "POST"])
def login():
    """Admin login."""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Admin logout."""
    session.pop("logged_in", None)
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    """Main dashboard with metrics."""
    # Get basic stats
    total_users = db.session.execute(text("SELECT COUNT(*) FROM users")).scalar()
    active_today = db.session.execute(
        text("SELECT COUNT(*) FROM users WHERE last_activity_date = CURRENT_DATE")
    ).scalar()

    total_tasks = db.session.execute(text("SELECT COUNT(*) FROM tasks")).scalar()
    completed_tasks = db.session.execute(
        text("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
    ).scalar()

    total_focus_minutes = db.session.execute(
        text(
            "SELECT COALESCE(SUM(actual_duration_minutes), 0) FROM focus_sessions WHERE status = 'completed'"
        )
    ).scalar()

    total_mood_checks = db.session.execute(
        text("SELECT COUNT(*) FROM mood_checks")
    ).scalar()

    # Get daily active users for last 7 days
    daily_active = db.session.execute(
        text(
            """
        SELECT
            last_activity_date as date,
            COUNT(*) as users
        FROM users
        WHERE last_activity_date >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY last_activity_date
        ORDER BY last_activity_date
    """
        )
    ).fetchall()

    # Get new users per day
    new_users = db.session.execute(
        text(
            """
        SELECT
            DATE(created_at) as date,
            COUNT(*) as users
        FROM users
        WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY DATE(created_at)
        ORDER BY date
    """
        )
    ).fetchall()

    return render_template(
        "dashboard.html",
        total_users=total_users,
        active_today=active_today or 0,
        total_tasks=total_tasks or 0,
        completed_tasks=completed_tasks or 0,
        total_focus_minutes=total_focus_minutes or 0,
        total_mood_checks=total_mood_checks or 0,
        daily_active=[{"date": str(r[0]), "users": r[1]} for r in daily_active],
        new_users=[{"date": str(r[0]), "users": r[1]} for r in new_users],
    )


@app.route("/users")
@login_required
def users():
    """User list."""
    page = request.args.get("page", 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    search = request.args.get("search", "")

    if search:
        query = text(
            """
            SELECT * FROM users
            WHERE username ILIKE :search OR first_name ILIKE :search
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """
        )
        users_data = db.session.execute(
            query, {"search": f"%{search}%", "limit": per_page, "offset": offset}
        ).fetchall()

        total = db.session.execute(
            text(
                "SELECT COUNT(*) FROM users WHERE username ILIKE :search OR first_name ILIKE :search"
            ),
            {"search": f"%{search}%"},
        ).scalar()
    else:
        users_data = db.session.execute(
            text(
                "SELECT * FROM users ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            {"limit": per_page, "offset": offset},
        ).fetchall()
        total = db.session.execute(text("SELECT COUNT(*) FROM users")).scalar()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "users.html",
        users=[dict(row._mapping) for row in users_data],
        page=page,
        total_pages=total_pages,
        search=search,
    )


@app.route("/users/<int:user_id>")
@login_required
def user_detail(user_id: int):
    """User detail view."""
    user = db.session.execute(
        text("SELECT * FROM users WHERE id = :id"), {"id": user_id}
    ).fetchone()

    if not user:
        return "User not found", 404

    # Get user's tasks
    try:
        tasks = db.session.execute(
            text(
                "SELECT * FROM tasks WHERE user_id = :uid ORDER BY created_at DESC LIMIT 10"
            ),
            {"uid": user_id},
        ).fetchall()
    except Exception:
        tasks = []

    # Get user's activity log
    try:
        activity = db.session.execute(
            text(
                """
                SELECT * FROM user_activity_logs
                WHERE user_id = :uid
                ORDER BY created_at DESC
                LIMIT 50
            """
            ),
            {"uid": user_id},
        ).fetchall()
    except Exception:
        activity = []

    # Get focus sessions
    try:
        sessions = db.session.execute(
            text(
                """
                SELECT * FROM focus_sessions
                WHERE user_id = :uid
                ORDER BY started_at DESC
                LIMIT 10
            """
            ),
            {"uid": user_id},
        ).fetchall()
    except Exception:
        sessions = []

    # Get productivity patterns
    try:
        productivity_patterns = db.session.execute(
            text(
                """
                SELECT
                    EXTRACT(HOUR FROM started_at)::int as hour,
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed
                FROM focus_sessions
                WHERE user_id = :uid
                    AND started_at >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY EXTRACT(HOUR FROM started_at)
                ORDER BY hour
            """
            ),
            {"uid": user_id},
        ).fetchall()
    except Exception:
        productivity_patterns = []

    # Get day of week patterns
    try:
        day_patterns = db.session.execute(
            text(
                """
                SELECT
                    EXTRACT(DOW FROM started_at)::int as day,
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed
                FROM focus_sessions
                WHERE user_id = :uid
                    AND started_at >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY EXTRACT(DOW FROM started_at)
                ORDER BY day
            """
            ),
            {"uid": user_id},
        ).fetchall()
    except Exception:
        day_patterns = []

    # Get user's cards
    try:
        cards = db.session.execute(
            text(
                """
                SELECT * FROM user_cards
                WHERE user_id = :uid AND is_destroyed = false
                ORDER BY rarity DESC, created_at DESC
                LIMIT 50
            """
            ),
            {"uid": user_id},
        ).fetchall()
    except Exception:
        cards = []

    # Get card statistics
    try:
        card_stats = db.session.execute(
            text(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE is_in_deck = true) as in_deck,
                    COUNT(*) FILTER (WHERE ability IS NOT NULL) as with_abilities,
                    COUNT(*) FILTER (WHERE rarity = 'common') as common,
                    COUNT(*) FILTER (WHERE rarity = 'uncommon') as uncommon,
                    COUNT(*) FILTER (WHERE rarity = 'rare') as rare,
                    COUNT(*) FILTER (WHERE rarity = 'epic') as epic,
                    COUNT(*) FILTER (WHERE rarity = 'legendary') as legendary
                FROM user_cards
                WHERE user_id = :uid AND is_destroyed = false
            """
            ),
            {"uid": user_id},
        ).fetchone()
    except Exception:
        card_stats = None

    # Get battle history
    try:
        battles = db.session.execute(
            text(
                """
                SELECT b.*, m.name as monster_name
                FROM battle_logs b
                LEFT JOIN monsters m ON b.monster_id = m.id
                WHERE b.user_id = :uid
                ORDER BY b.created_at DESC
                LIMIT 20
            """
            ),
            {"uid": user_id},
        ).fetchall()
    except Exception:
        battles = []

    # Get battle statistics
    try:
        battle_stats = db.session.execute(
            text(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE won = true) as wins,
                    COALESCE(SUM(xp_earned), 0) as total_xp,
                    COALESCE(SUM(damage_dealt), 0) as total_damage,
                    COALESCE(AVG(rounds), 0) as avg_rounds
                FROM battle_logs
                WHERE user_id = :uid
            """
            ),
            {"uid": user_id},
        ).fetchone()
    except Exception:
        battle_stats = None

    # Get user's genre preference
    try:
        user_genre = db.session.execute(
            text("SELECT favorite_genre FROM user_profiles WHERE user_id = :uid"),
            {"uid": user_id},
        ).fetchone()
    except Exception:
        user_genre = None

    # Get onboarding status
    try:
        onboarding_profile = db.session.execute(
            text(
                """
                SELECT onboarding_completed, onboarding_completed_at,
                       productivity_type, work_style, preferred_time
                FROM user_profiles WHERE user_id = :uid
                """
            ),
            {"uid": user_id},
        ).fetchone()
    except Exception:
        onboarding_profile = None

    # Format productivity data
    hour_data = {
        r[0]: {"total": r[1], "completed": r[2]} for r in productivity_patterns
    }
    day_data = {r[0]: {"total": r[1], "completed": r[2]} for r in day_patterns}

    # Find best hour
    best_hour = None
    max_success = 0
    for hour, data in hour_data.items():
        if data["total"] >= 2:
            success_rate = data["completed"] / data["total"]
            if success_rate > max_success or (
                success_rate == max_success
                and data["total"] > hour_data.get(best_hour, {}).get("total", 0)
            ):
                max_success = success_rate
                best_hour = hour

    # Find best day
    day_names = ["Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
    best_day = None
    max_day_success = 0
    for day, data in day_data.items():
        if data["total"] >= 2:
            success_rate = data["completed"] / data["total"]
            if success_rate > max_day_success:
                max_day_success = success_rate
                best_day = day

    return render_template(
        "user_detail.html",
        user=dict(user._mapping),
        tasks=[dict(row._mapping) for row in tasks],
        activity=[dict(row._mapping) for row in activity] if activity else [],
        sessions=[dict(row._mapping) for row in sessions],
        cards=[dict(row._mapping) for row in cards] if cards else [],
        card_stats=dict(card_stats._mapping) if card_stats else {},
        battles=[dict(row._mapping) for row in battles] if battles else [],
        battle_stats=dict(battle_stats._mapping) if battle_stats else {},
        user_genre=user_genre[0] if user_genre else None,
        onboarding=dict(onboarding_profile._mapping) if onboarding_profile else None,
        productivity={
            "hour_data": [
                {
                    "hour": h,
                    "total": hour_data.get(h, {}).get("total", 0),
                    "completed": hour_data.get(h, {}).get("completed", 0),
                }
                for h in range(24)
            ],
            "day_data": [
                {
                    "day": d,
                    "name": day_names[d],
                    "total": day_data.get(d, {}).get("total", 0),
                    "completed": day_data.get(d, {}).get("completed", 0),
                }
                for d in range(7)
            ],
            "best_hour": best_hour,
            "best_day": day_names[best_day] if best_day is not None else None,
            "best_hour_success": (
                round(max_success * 100) if best_hour is not None else 0
            ),
            "best_day_success": (
                round(max_day_success * 100) if best_day is not None else 0
            ),
        },
    )


@app.route("/activity")
@login_required
def activity_log():
    """Global activity log."""
    page = request.args.get("page", 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page

    logs = db.session.execute(
        text(
            """
            SELECT l.*, u.username, u.first_name
            FROM user_activity_logs l
            JOIN users u ON l.user_id = u.id
            ORDER BY l.created_at DESC
            LIMIT :limit OFFSET :offset
        """
        ),
        {"limit": per_page, "offset": offset},
    ).fetchall()

    total = (
        db.session.execute(text("SELECT COUNT(*) FROM user_activity_logs")).scalar()
        or 0
    )
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "activity.html",
        logs=[dict(row._mapping) for row in logs],
        page=page,
        total_pages=total_pages,
    )


@app.route("/metrics")
@login_required
def metrics():
    """Product metrics page."""
    # Retention metrics
    day1_retention = (
        db.session.execute(
            text(
                """
        SELECT
            COUNT(DISTINCT CASE WHEN last_activity_date > DATE(created_at) THEN id END)::float /
            NULLIF(COUNT(DISTINCT id), 0) * 100 as retention
        FROM users
        WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
    """
            )
        ).scalar()
        or 0
    )

    # Average session duration
    avg_session = (
        db.session.execute(
            text(
                """
        SELECT AVG(actual_duration_minutes)
        FROM focus_sessions
        WHERE status = 'completed' AND actual_duration_minutes IS NOT NULL
    """
            )
        ).scalar()
        or 0
    )

    # Task completion rate
    completion_rate = (
        db.session.execute(
            text(
                """
        SELECT
            COUNT(*) FILTER (WHERE status = 'completed')::float /
            NULLIF(COUNT(*), 0) * 100
        FROM tasks
    """
            )
        ).scalar()
        or 0
    )

    # Average XP per user
    avg_xp = db.session.execute(text("SELECT AVG(xp) FROM users")).scalar() or 0

    # Average streak
    avg_streak = (
        db.session.execute(text("SELECT AVG(streak_days) FROM users")).scalar() or 0
    )

    # Mood distribution
    mood_dist = db.session.execute(
        text(
            """
        SELECT mood, COUNT(*) as count
        FROM mood_checks
        GROUP BY mood
        ORDER BY mood
    """
        )
    ).fetchall()

    # Energy distribution
    energy_dist = db.session.execute(
        text(
            """
        SELECT energy, COUNT(*) as count
        FROM mood_checks
        GROUP BY energy
        ORDER BY energy
    """
        )
    ).fetchall()

    # Daily metrics for last 30 days
    daily_metrics = db.session.execute(
        text(
            """
        SELECT
            d.date,
            COALESCE(u.new_users, 0) as new_users,
            COALESCE(a.active_users, 0) as active_users,
            COALESCE(t.tasks_completed, 0) as tasks_completed,
            COALESCE(f.focus_minutes, 0) as focus_minutes
        FROM generate_series(
            CURRENT_DATE - INTERVAL '29 days',
            CURRENT_DATE,
            '1 day'::interval
        ) as d(date)
        LEFT JOIN (
            SELECT DATE(created_at) as date, COUNT(*) as new_users
            FROM users GROUP BY DATE(created_at)
        ) u ON d.date = u.date
        LEFT JOIN (
            SELECT last_activity_date as date, COUNT(*) as active_users
            FROM users GROUP BY last_activity_date
        ) a ON d.date = a.date
        LEFT JOIN (
            SELECT DATE(completed_at) as date, COUNT(*) as tasks_completed
            FROM tasks WHERE status = 'completed' GROUP BY DATE(completed_at)
        ) t ON d.date = t.date
        LEFT JOIN (
            SELECT DATE(started_at) as date, SUM(actual_duration_minutes) as focus_minutes
            FROM focus_sessions WHERE status = 'completed' GROUP BY DATE(started_at)
        ) f ON d.date = f.date
        ORDER BY d.date
    """
        )
    ).fetchall()

    return render_template(
        "metrics.html",
        day1_retention=round(day1_retention, 1),
        avg_session=round(avg_session, 1),
        completion_rate=round(completion_rate, 1),
        avg_xp=round(avg_xp, 0),
        avg_streak=round(avg_streak, 1),
        mood_distribution=[{"mood": r[0], "count": r[1]} for r in mood_dist],
        energy_distribution=[{"energy": r[0], "count": r[1]} for r in energy_dist],
        daily_metrics=[
            {
                "date": str(r[0]),
                "new_users": r[1],
                "active_users": r[2],
                "tasks_completed": r[3],
                "focus_minutes": r[4],
            }
            for r in daily_metrics
        ],
    )


@app.route("/business")
@login_required
def business_metrics():
    """Business metrics page with North Star metric."""
    # North Star: Completed Tasks / Created Tasks ratio
    north_star = (
        db.session.execute(
            text(
                """
        SELECT
            COUNT(*) FILTER (WHERE status = 'completed')::float /
            NULLIF(COUNT(*), 0) * 100 as ratio
        FROM tasks
        """
            )
        ).scalar()
        or 0
    )

    # Tasks created vs completed
    total_created = db.session.execute(text("SELECT COUNT(*) FROM tasks")).scalar() or 0
    total_completed = (
        db.session.execute(
            text("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
        ).scalar()
        or 0
    )

    # Weekly North Star trend
    weekly_north_star = db.session.execute(
        text(
            """
        SELECT
            DATE_TRUNC('week', created_at)::date as week,
            COUNT(*) FILTER (WHERE status = 'completed')::float /
            NULLIF(COUNT(*), 0) * 100 as ratio,
            COUNT(*) as total_created,
            COUNT(*) FILTER (WHERE status = 'completed') as total_completed
        FROM tasks
        WHERE created_at >= CURRENT_DATE - INTERVAL '12 weeks'
        GROUP BY DATE_TRUNC('week', created_at)
        ORDER BY week
        """
        )
    ).fetchall()

    # Daily North Star for last 30 days
    daily_north_star = db.session.execute(
        text(
            """
        SELECT
            d.date,
            COUNT(t.id) as created,
            COUNT(t.id) FILTER (WHERE t.status = 'completed') as completed,
            CASE WHEN COUNT(t.id) > 0 THEN
                COUNT(t.id) FILTER (WHERE t.status = 'completed')::float / COUNT(t.id) * 100
            ELSE 0 END as ratio
        FROM generate_series(
            CURRENT_DATE - INTERVAL '29 days',
            CURRENT_DATE,
            '1 day'::interval
        ) as d(date)
        LEFT JOIN tasks t ON DATE(t.created_at) = d.date
        GROUP BY d.date
        ORDER BY d.date
        """
        )
    ).fetchall()

    # Per-user completion rates (top and bottom performers)
    user_completion_rates = db.session.execute(
        text(
            """
        SELECT
            u.id,
            u.first_name,
            u.username,
            COUNT(t.id) as total_tasks,
            COUNT(t.id) FILTER (WHERE t.status = 'completed') as completed_tasks,
            CASE WHEN COUNT(t.id) > 0 THEN
                COUNT(t.id) FILTER (WHERE t.status = 'completed')::float / COUNT(t.id) * 100
            ELSE 0 END as completion_rate
        FROM users u
        LEFT JOIN tasks t ON t.user_id = u.id
        GROUP BY u.id, u.first_name, u.username
        HAVING COUNT(t.id) >= 3
        ORDER BY completion_rate DESC
        LIMIT 10
        """
        )
    ).fetchall()

    # Users with low completion (need attention)
    users_needing_help = db.session.execute(
        text(
            """
        SELECT
            u.id,
            u.first_name,
            u.username,
            COUNT(t.id) as total_tasks,
            COUNT(t.id) FILTER (WHERE t.status = 'completed') as completed_tasks,
            CASE WHEN COUNT(t.id) > 0 THEN
                COUNT(t.id) FILTER (WHERE t.status = 'completed')::float / COUNT(t.id) * 100
            ELSE 0 END as completion_rate
        FROM users u
        LEFT JOIN tasks t ON t.user_id = u.id
        GROUP BY u.id, u.first_name, u.username
        HAVING COUNT(t.id) >= 3
        ORDER BY completion_rate ASC
        LIMIT 10
        """
        )
    ).fetchall()

    # Cohort retention by week
    cohort_retention = db.session.execute(
        text(
            """
        SELECT
            DATE_TRUNC('week', u.created_at)::date as cohort_week,
            COUNT(DISTINCT u.id) as users,
            COUNT(DISTINCT CASE WHEN u.last_activity_date >= DATE_TRUNC('week', u.created_at) + INTERVAL '7 days' THEN u.id END) as week1,
            COUNT(DISTINCT CASE WHEN u.last_activity_date >= DATE_TRUNC('week', u.created_at) + INTERVAL '14 days' THEN u.id END) as week2,
            COUNT(DISTINCT CASE WHEN u.last_activity_date >= DATE_TRUNC('week', u.created_at) + INTERVAL '21 days' THEN u.id END) as week3
        FROM users u
        WHERE u.created_at >= CURRENT_DATE - INTERVAL '8 weeks'
        GROUP BY DATE_TRUNC('week', u.created_at)
        ORDER BY cohort_week DESC
        """
        )
    ).fetchall()

    return render_template(
        "business.html",
        north_star=round(north_star, 1),
        total_created=total_created,
        total_completed=total_completed,
        weekly_north_star=[
            {
                "week": str(r[0]),
                "ratio": round(r[1] or 0, 1),
                "created": r[2],
                "completed": r[3],
            }
            for r in weekly_north_star
        ],
        daily_north_star=[
            {
                "date": str(r[0]),
                "created": r[1],
                "completed": r[2],
                "ratio": round(r[3] or 0, 1),
            }
            for r in daily_north_star
        ],
        top_performers=[
            {
                "id": r[0],
                "name": r[1] or r[2] or "Unknown",
                "total": r[3],
                "completed": r[4],
                "rate": round(r[5] or 0, 1),
            }
            for r in user_completion_rates
        ],
        users_needing_help=[
            {
                "id": r[0],
                "name": r[1] or r[2] or "Unknown",
                "total": r[3],
                "completed": r[4],
                "rate": round(r[5] or 0, 1),
            }
            for r in users_needing_help
        ],
        cohort_retention=[
            {
                "week": str(r[0]),
                "users": r[1],
                "week1": round(r[2] / r[1] * 100, 1) if r[1] > 0 else 0,
                "week2": round(r[3] / r[1] * 100, 1) if r[1] > 0 else 0,
                "week3": round(r[4] / r[1] * 100, 1) if r[1] > 0 else 0,
            }
            for r in cohort_retention
        ],
    )


@app.route("/users/<int:user_id>/reset-onboarding", methods=["POST"])
@login_required
def reset_onboarding(user_id: int):
    """Reset onboarding for a user."""
    try:
        # Check if profile exists
        profile = db.session.execute(
            text("SELECT id FROM user_profiles WHERE user_id = :uid"),
            {"uid": user_id},
        ).fetchone()

        if profile:
            # Reset onboarding status
            db.session.execute(
                text(
                    """
                    UPDATE user_profiles
                    SET onboarding_completed = false,
                        onboarding_completed_at = NULL
                    WHERE user_id = :uid
                    """
                ),
                {"uid": user_id},
            )
            db.session.commit()
            return jsonify(
                {"success": True, "message": "Onboarding reset successfully"}
            )
        else:
            return jsonify(
                {
                    "success": True,
                    "message": "No profile found, user will see onboarding",
                }
            )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/users/<int:user_id>/reset-spotlight", methods=["POST"])
@login_required
def reset_spotlight(user_id: int):
    """Reset spotlight onboarding for a user."""
    try:
        # Check if profile exists
        profile = db.session.execute(
            text("SELECT id FROM user_profiles WHERE user_id = :uid"),
            {"uid": user_id},
        ).fetchone()

        if profile:
            # Set spotlight_reset_at to current time
            db.session.execute(
                text(
                    """
                    UPDATE user_profiles
                    SET spotlight_reset_at = NOW()
                    WHERE user_id = :uid
                    """
                ),
                {"uid": user_id},
            )
            db.session.commit()
            return jsonify(
                {"success": True, "message": "Spotlight onboarding will be shown again"}
            )
        else:
            return jsonify({"success": False, "error": "User profile not found"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/metrics/realtime")
@login_required
def realtime_metrics():
    """Realtime metrics API."""
    active_sessions = db.session.execute(
        text("SELECT COUNT(*) FROM focus_sessions WHERE status = 'active'")
    ).scalar()

    today_mood_checks = db.session.execute(
        text("SELECT COUNT(*) FROM mood_checks WHERE DATE(created_at) = CURRENT_DATE")
    ).scalar()

    today_tasks_completed = db.session.execute(
        text("SELECT COUNT(*) FROM tasks WHERE DATE(completed_at) = CURRENT_DATE")
    ).scalar()

    return jsonify(
        {
            "active_sessions": active_sessions or 0,
            "today_mood_checks": today_mood_checks or 0,
            "today_tasks_completed": today_tasks_completed or 0,
        }
    )


@app.route("/users/<int:user_id>/activity-heatmap")
@login_required
def user_activity_heatmap(user_id: int):
    """Get user activity data for GitHub-style heatmap."""
    # Get completions for the last 365 days
    try:
        task_completions = db.session.execute(
            text(
                """
                SELECT DATE(completed_at) as completion_date, COUNT(*) as count
                FROM tasks
                WHERE user_id = :uid
                    AND status = 'completed'
                    AND completed_at >= CURRENT_DATE - INTERVAL '365 days'
                GROUP BY DATE(completed_at)
                """
            ),
            {"uid": user_id},
        ).fetchall()

        subtask_completions = db.session.execute(
            text(
                """
                SELECT DATE(s.completed_at) as completion_date, COUNT(*) as count
                FROM subtasks s
                JOIN tasks t ON s.task_id = t.id
                WHERE t.user_id = :uid
                    AND s.status = 'completed'
                    AND s.completed_at >= CURRENT_DATE - INTERVAL '365 days'
                GROUP BY DATE(s.completed_at)
                """
            ),
            {"uid": user_id},
        ).fetchall()

        # Combine into a single dict
        activity = {}
        for row in task_completions:
            if row[0]:
                date_str = str(row[0])
                activity[date_str] = activity.get(date_str, 0) + row[1]

        for row in subtask_completions:
            if row[0]:
                date_str = str(row[0])
                activity[date_str] = activity.get(date_str, 0) + row[1]

        return jsonify({"success": True, "activity": activity})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/friends")
@login_required
def friends_list():
    """Friendships management page."""
    # Get all friendships with user details
    try:
        friendships = db.session.execute(
            text(
                """
                SELECT
                    f.id,
                    f.user_id,
                    f.friend_id,
                    f.created_at,
                    u1.username as user_username,
                    u1.first_name as user_first_name,
                    u2.username as friend_username,
                    u2.first_name as friend_first_name
                FROM friendships f
                JOIN users u1 ON f.user_id = u1.id
                JOIN users u2 ON f.friend_id = u2.id
                ORDER BY f.created_at DESC
                LIMIT 100
                """
            )
        ).fetchall()
    except Exception:
        friendships = []

    return render_template(
        "friends.html",
        friendships=[dict(row._mapping) for row in friendships] if friendships else [],
    )


@app.route("/friends/<int:friendship_id>/remove", methods=["POST"])
@login_required
def remove_friendship(friendship_id: int):
    """Remove a friendship."""
    try:
        db.session.execute(
            text("DELETE FROM friendships WHERE id = :id"),
            {"id": friendship_id},
        )
        db.session.commit()
        return jsonify({"success": True, "message": "Friendship removed"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/friends/remove-by-users", methods=["POST"])
@login_required
def remove_friendship_by_users():
    """Remove friendship by user IDs."""
    data = request.get_json() or {}
    user_id = data.get("user_id")
    friend_id = data.get("friend_id")

    if not user_id or not friend_id:
        return (
            jsonify({"success": False, "error": "user_id and friend_id required"}),
            400,
        )

    try:
        result = db.session.execute(
            text(
                """
                DELETE FROM friendships
                WHERE (user_id = :uid AND friend_id = :fid)
                   OR (user_id = :fid AND friend_id = :uid)
                """
            ),
            {"uid": user_id, "fid": friend_id},
        )
        db.session.commit()

        if result.rowcount > 0:
            return jsonify({"success": True, "message": "Friendship removed"})
        else:
            return jsonify({"success": False, "error": "Friendship not found"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# ============ Monsters ============


@app.route("/monsters/generate-images", methods=["POST"])
@login_required
def generate_monster_images():
    """Generate images for monsters without images, one by one."""
    import requests

    genre = request.args.get("genre")

    # Count total monsters without images
    count_query = """
        SELECT COUNT(*) FROM monsters
        WHERE sprite_url IS NULL OR sprite_url = ''
    """
    if genre:
        count_query += f" AND genre = '{genre}'"
    total_without_images = db.session.execute(text(count_query)).scalar() or 0

    if total_without_images == 0:
        return jsonify({
            "success": True,
            "data": {
                "message": "All monsters already have images" if not genre else f"All {genre} monsters have images",
                "generated": 0,
                "failed": 0,
                "remaining": 0
            }
        })

    # Get monsters without images (limit 5 at a time)
    query = """
        SELECT id, name, description, genre
        FROM monsters
        WHERE sprite_url IS NULL OR sprite_url = ''
    """
    if genre:
        query += f" AND genre = '{genre}'"
    query += " LIMIT 5"

    monsters = db.session.execute(text(query)).fetchall()

    generated = 0
    failed = 0

    for monster in monsters:
        try:
            response = requests.post(
                f"{API_URL}/api/v1/arena/monsters/{monster.id}/generate-image-admin",
                headers={"X-Bot-Secret": BOT_SECRET},
                timeout=60,
            )
            result = response.json()
            if result.get("success"):
                generated += 1
            else:
                failed += 1
        except Exception:
            failed += 1

    remaining = total_without_images - generated

    return jsonify({
        "success": True,
        "data": {
            "generated": generated,
            "failed": failed,
            "remaining": remaining,
            "message": f"Generated {generated} images. {remaining} remaining."
        }
    })


@app.route("/monsters/rotate", methods=["POST"])
@login_required
def rotate_monsters_proxy():
    """Proxy to backend for rotating monsters."""
    import requests

    try:
        response = requests.post(
            f"{API_URL}/api/v1/arena/monsters/rotate",
            headers={"X-Bot-Secret": BOT_SECRET},
            timeout=300,
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/monsters")
@login_required
def monsters():
    """List all monsters with image generation controls."""
    from datetime import date, timedelta

    # Get all monsters
    all_monsters = db.session.execute(
        text(
            """
            SELECT id, name, description, genre, base_level, base_hp, base_attack,
                   sprite_url, emoji, is_boss, ai_generated, created_at
            FROM monsters
            ORDER BY genre, is_boss DESC, base_level DESC
        """
        )
    ).fetchall()

    # Get current period (Monday of current week)
    today = date.today()
    days_since_monday = today.weekday()
    period_start = today - timedelta(days=days_since_monday)

    # Count stats
    total_monsters = len(all_monsters)
    with_images = sum(1 for m in all_monsters if m.sprite_url)
    without_images = total_monsters - with_images

    # Group by genre
    monsters_by_genre = {}
    for monster in all_monsters:
        genre = monster.genre or "unknown"
        if genre not in monsters_by_genre:
            monsters_by_genre[genre] = []
        monsters_by_genre[genre].append(monster)

    return render_template(
        "monsters.html",
        monsters_by_genre=monsters_by_genre,
        total_monsters=total_monsters,
        with_images=with_images,
        without_images=without_images,
        current_period=str(period_start),
    )


@app.route("/monsters/<int:monster_id>")
@login_required
def monster_detail(monster_id: int):
    """Monster detail page with cards."""
    monster = db.session.execute(
        text(
            """
            SELECT id, name, description, genre, base_level, base_hp, base_attack,
                   sprite_url, emoji, is_boss, ai_generated, created_at
            FROM monsters
            WHERE id = :monster_id
        """
        ),
        {"monster_id": monster_id},
    ).fetchone()

    if not monster:
        return "Monster not found", 404

    # Get monster's cards
    monster_cards = db.session.execute(
        text(
            """
            SELECT id, name, description, emoji, attack, hp, ability
            FROM monster_cards
            WHERE monster_id = :monster_id
            ORDER BY id
        """
        ),
        {"monster_id": monster_id},
    ).fetchall()

    return render_template(
        "monster_detail.html",
        monster=dict(monster._mapping),
        cards=[dict(row._mapping) for row in monster_cards] if monster_cards else [],
    )


@app.route("/monsters/new", methods=["POST"])
@login_required
def create_monster():
    """Create a new monster."""
    data = request.json
    try:
        result = db.session.execute(
            text(
                """
                INSERT INTO monsters (name, description, genre, base_level, base_hp, base_attack,
                    sprite_url, emoji, is_boss)
                VALUES (:name, :description, :genre, :base_level, :base_hp, :base_attack,
                    :sprite_url, :emoji, :is_boss)
                RETURNING id
            """
            ),
            {
                "name": data["name"],
                "description": data.get("description"),
                "genre": data["genre"],
                "base_level": data.get("base_level", 1),
                "base_hp": data.get("base_hp", 100),
                "base_attack": data.get("base_attack", 10),
                "sprite_url": data.get("sprite_url"),
                "emoji": data.get("emoji", "👹"),
                "is_boss": data.get("is_boss", False),
            },
        )
        monster_id = result.scalar()
        db.session.commit()
        return jsonify({"success": True, "id": monster_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/monsters/<int:monster_id>/update", methods=["POST"])
@login_required
def update_monster(monster_id: int):
    """Update monster details."""
    data = request.json

    try:
        updates = []
        params = {"monster_id": monster_id}

        for field in ["name", "description", "genre", "base_level", "base_hp",
                      "base_attack", "sprite_url", "emoji", "is_boss"]:
            if field in data:
                updates.append(f"{field} = :{field}")
                params[field] = data[field]

        if updates:
            db.session.execute(
                text(
                    f"UPDATE monsters SET {', '.join(updates)} WHERE id = :monster_id"
                ),
                params,
            )
            db.session.commit()

        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/monsters/<int:monster_id>/delete", methods=["POST"])
@login_required
def delete_monster(monster_id: int):
    """Delete a monster."""
    try:
        # Delete monster cards first
        db.session.execute(
            text("DELETE FROM monster_cards WHERE monster_id = :monster_id"),
            {"monster_id": monster_id},
        )
        # Delete monster
        db.session.execute(
            text("DELETE FROM monsters WHERE id = :monster_id"),
            {"monster_id": monster_id},
        )
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/monsters/<int:monster_id>/cards/add", methods=["POST"])
@login_required
def add_monster_card(monster_id: int):
    """Add a card to a monster."""
    data = request.json
    try:
        result = db.session.execute(
            text(
                """
                INSERT INTO monster_cards (monster_id, name, description, emoji, attack, hp, ability)
                VALUES (:monster_id, :name, :description, :emoji, :attack, :hp, :ability)
                RETURNING id
            """
            ),
            {
                "monster_id": monster_id,
                "name": data["name"],
                "description": data.get("description"),
                "emoji": data.get("emoji", "⚔️"),
                "attack": data.get("attack", 10),
                "hp": data.get("hp", 20),
                "ability": data.get("ability"),
            },
        )
        card_id = result.scalar()
        db.session.commit()
        return jsonify({"success": True, "id": card_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/monsters/cards/<int:card_id>/update", methods=["POST"])
@login_required
def update_monster_card(card_id: int):
    """Update a monster card."""
    data = request.json

    try:
        updates = []
        params = {"card_id": card_id}

        for field in ["name", "description", "emoji", "attack", "hp", "ability"]:
            if field in data:
                updates.append(f"{field} = :{field}")
                params[field] = data[field]

        if updates:
            db.session.execute(
                text(
                    f"UPDATE monster_cards SET {', '.join(updates)} WHERE id = :card_id"
                ),
                params,
            )
            db.session.commit()

        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/monsters/cards/<int:card_id>/delete", methods=["POST"])
@login_required
def delete_monster_card(card_id: int):
    """Delete a monster card."""
    try:
        db.session.execute(
            text("DELETE FROM monster_cards WHERE id = :card_id"),
            {"card_id": card_id},
        )
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


# ============ Seasonal Events ============


@app.route("/events")
@login_required
def events():
    """List all seasonal events."""
    all_events = db.session.execute(
        text(
            """
            SELECT id, code, name, description, event_type, start_date, end_date,
                   emoji, theme_color, xp_multiplier, is_active, created_at,
                   (is_active AND start_date <= NOW() AND end_date >= NOW()) as is_currently_active
            FROM seasonal_events
            ORDER BY start_date DESC
        """
        )
    ).fetchall()

    active_events = [e for e in all_events if e.is_currently_active]

    return render_template(
        "events.html",
        events=all_events,
        active_events=active_events,
        now=datetime.utcnow(),
    )


@app.route("/events/create", methods=["POST"])
@login_required
def create_event():
    """Create a new seasonal event."""
    data = request.json
    try:
        result = db.session.execute(
            text(
                """
                INSERT INTO seasonal_events (code, name, description, event_type, start_date, end_date, emoji, theme_color, xp_multiplier, is_active)
                VALUES (:code, :name, :description, :event_type, :start_date, :end_date, :emoji, :theme_color, :xp_multiplier, true)
                RETURNING id
            """
            ),
            {
                "code": data["code"],
                "name": data["name"],
                "description": data.get("description"),
                "event_type": data.get("event_type", "seasonal"),
                "start_date": datetime.fromisoformat(data["start_date"]),
                "end_date": datetime.fromisoformat(data["end_date"]),
                "emoji": data.get("emoji", "🎉"),
                "theme_color": data.get("theme_color", "#FF6B00"),
                "xp_multiplier": data.get("xp_multiplier", 1.0),
            },
        )
        event_id = result.scalar()
        db.session.commit()
        return jsonify({"success": True, "event_id": event_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/events/<int:event_id>")
@login_required
def event_detail(event_id: int):
    """Event detail page with monsters."""
    event = db.session.execute(
        text(
            """
            SELECT id, code, name, description, event_type, start_date, end_date,
                   emoji, theme_color, xp_multiplier, is_active, created_at,
                   (is_active AND start_date <= NOW() AND end_date >= NOW()) as is_currently_active
            FROM seasonal_events
            WHERE id = :event_id
        """
        ),
        {"event_id": event_id},
    ).fetchone()

    if not event:
        return "Event not found", 404

    event_monsters = db.session.execute(
        text(
            """
            SELECT em.id, em.event_id, em.monster_id, em.appear_day,
                   em.exclusive_reward_name, em.guaranteed_rarity,
                   m.name as monster_name, m.emoji as monster_emoji, m.genre as monster_genre
            FROM event_monsters em
            JOIN monsters m ON m.id = em.monster_id
            WHERE em.event_id = :event_id
            ORDER BY em.appear_day
        """
        ),
        {"event_id": event_id},
    ).fetchall()

    all_monsters = db.session.execute(
        text("SELECT id, name, emoji, genre FROM monsters ORDER BY genre, name")
    ).fetchall()

    return render_template(
        "event_detail.html",
        event=event,
        event_monsters=event_monsters,
        all_monsters=all_monsters,
        now=datetime.utcnow(),
    )


@app.route("/events/<int:event_id>/update", methods=["POST"])
@login_required
def update_event(event_id: int):
    """Update event details."""
    data = request.json

    try:
        updates = []
        params = {"event_id": event_id}

        if "code" in data:
            updates.append("code = :code")
            params["code"] = data["code"]
        if "name" in data:
            updates.append("name = :name")
            params["name"] = data["name"]
        if "description" in data:
            updates.append("description = :description")
            params["description"] = data["description"]
        if "start_date" in data:
            updates.append("start_date = :start_date")
            params["start_date"] = datetime.fromisoformat(data["start_date"])
        if "end_date" in data:
            updates.append("end_date = :end_date")
            params["end_date"] = datetime.fromisoformat(data["end_date"])
        if "emoji" in data:
            updates.append("emoji = :emoji")
            params["emoji"] = data["emoji"]
        if "theme_color" in data:
            updates.append("theme_color = :theme_color")
            params["theme_color"] = data["theme_color"]
        if "xp_multiplier" in data:
            updates.append("xp_multiplier = :xp_multiplier")
            params["xp_multiplier"] = data["xp_multiplier"]

        if updates:
            db.session.execute(
                text(
                    f"UPDATE seasonal_events SET {', '.join(updates)} WHERE id = :event_id"
                ),
                params,
            )
            db.session.commit()

        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/events/<int:event_id>/toggle", methods=["POST"])
@login_required
def toggle_event(event_id: int):
    """Enable/disable an event."""
    data = request.json

    try:
        if "is_active" in data:
            is_active = data["is_active"]
        else:
            # Toggle current state
            current = db.session.execute(
                text("SELECT is_active FROM seasonal_events WHERE id = :event_id"),
                {"event_id": event_id},
            ).scalar()
            is_active = not current

        db.session.execute(
            text(
                "UPDATE seasonal_events SET is_active = :is_active WHERE id = :event_id"
            ),
            {"event_id": event_id, "is_active": is_active},
        )
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/events/<int:event_id>/monsters/add", methods=["POST"])
@login_required
def add_event_monster(event_id: int):
    """Add a monster to an event."""
    data = request.json

    try:
        result = db.session.execute(
            text(
                """
                INSERT INTO event_monsters (event_id, monster_id, appear_day, exclusive_reward_name, guaranteed_rarity)
                VALUES (:event_id, :monster_id, :appear_day, :exclusive_reward_name, :guaranteed_rarity)
                RETURNING id
            """
            ),
            {
                "event_id": event_id,
                "monster_id": data["monster_id"],
                "appear_day": data.get("appear_day", 1),
                "exclusive_reward_name": data.get("exclusive_reward_name"),
                "guaranteed_rarity": data.get("guaranteed_rarity") or None,
            },
        )
        event_monster_id = result.scalar()
        db.session.commit()
        return jsonify({"success": True, "id": event_monster_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/events/monsters/<int:event_monster_id>/remove", methods=["POST"])
@login_required
def remove_event_monster(event_monster_id: int):
    """Remove a monster from an event."""
    try:
        db.session.execute(
            text("DELETE FROM event_monsters WHERE id = :id"), {"id": event_monster_id}
        )
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


# ============ Campaign Chapters ============


@app.route("/campaign")
@login_required
def campaign():
    """List all campaign chapters."""
    chapters = db.session.execute(
        text(
            """
            SELECT c.id, c.number, c.name, c.genre, c.description,
                   c.emoji, c.background_color, c.required_power,
                   c.xp_reward, c.guaranteed_card_rarity, c.is_active,
                   c.story_intro, c.story_outro,
                   (SELECT COUNT(*) FROM campaign_levels WHERE chapter_id = c.id) as levels_count
            FROM campaign_chapters c
            ORDER BY c.number
        """
        )
    ).fetchall()

    return render_template(
        "campaign.html",
        chapters=[dict(row._mapping) for row in chapters] if chapters else [],
    )


@app.route("/campaign/chapters/new", methods=["POST"])
@login_required
def create_chapter():
    """Create a new campaign chapter."""
    data = request.json
    try:
        # Get next chapter number
        max_number = db.session.execute(
            text("SELECT COALESCE(MAX(number), 0) FROM campaign_chapters")
        ).scalar()

        result = db.session.execute(
            text(
                """
                INSERT INTO campaign_chapters (number, name, genre, description, emoji,
                    background_color, required_power, xp_reward, guaranteed_card_rarity,
                    story_intro, story_outro, is_active)
                VALUES (:number, :name, :genre, :description, :emoji,
                    :background_color, :required_power, :xp_reward, :guaranteed_card_rarity,
                    :story_intro, :story_outro, true)
                RETURNING id
            """
            ),
            {
                "number": max_number + 1,
                "name": data["name"],
                "genre": data["genre"],
                "description": data.get("description"),
                "emoji": data.get("emoji", "📖"),
                "background_color": data.get("background_color", "#1a1a2e"),
                "required_power": data.get("required_power", 0),
                "xp_reward": data.get("xp_reward", 500),
                "guaranteed_card_rarity": data.get("guaranteed_card_rarity", "rare"),
                "story_intro": data.get("story_intro"),
                "story_outro": data.get("story_outro"),
            },
        )
        chapter_id = result.scalar()
        db.session.commit()
        return jsonify({"success": True, "id": chapter_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/campaign/chapters/<int:chapter_id>")
@login_required
def chapter_detail(chapter_id: int):
    """Chapter detail page with levels."""
    chapter = db.session.execute(
        text(
            """
            SELECT id, number, name, genre, description, emoji, background_color,
                   image_url, required_power, xp_reward, guaranteed_card_rarity, is_active,
                   story_intro, story_outro
            FROM campaign_chapters
            WHERE id = :chapter_id
        """
        ),
        {"chapter_id": chapter_id},
    ).fetchone()

    if not chapter:
        return "Chapter not found", 404

    levels = db.session.execute(
        text(
            """
            SELECT l.id, l.number, l.monster_id, l.is_boss, l.title,
                   l.dialogue_before, l.dialogue_after, l.difficulty_multiplier,
                   l.required_power, l.xp_reward, l.stars_max, l.is_active,
                   m.name as monster_name, m.emoji as monster_emoji
            FROM campaign_levels l
            LEFT JOIN monsters m ON m.id = l.monster_id
            WHERE l.chapter_id = :chapter_id
            ORDER BY l.number
        """
        ),
        {"chapter_id": chapter_id},
    ).fetchall()

    all_monsters = db.session.execute(
        text("SELECT id, name, emoji, genre FROM monsters ORDER BY genre, name")
    ).fetchall()

    return render_template(
        "campaign_chapter.html",
        chapter=dict(chapter._mapping),
        levels=[dict(row._mapping) for row in levels] if levels else [],
        all_monsters=all_monsters,
    )


@app.route("/campaign/chapters/<int:chapter_id>/update", methods=["POST"])
@login_required
def update_chapter(chapter_id: int):
    """Update chapter details."""
    data = request.json

    try:
        updates = []
        params = {"chapter_id": chapter_id}

        for field in ["name", "genre", "description", "emoji", "background_color",
                      "image_url", "required_power", "xp_reward", "guaranteed_card_rarity",
                      "story_intro", "story_outro", "is_active"]:
            if field in data:
                updates.append(f"{field} = :{field}")
                params[field] = data[field]

        if updates:
            db.session.execute(
                text(
                    f"UPDATE campaign_chapters SET {', '.join(updates)} WHERE id = :chapter_id"
                ),
                params,
            )
            db.session.commit()

        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/campaign/chapters/<int:chapter_id>/levels/new", methods=["POST"])
@login_required
def create_level(chapter_id: int):
    """Create a new level in a chapter."""
    data = request.json
    try:
        # Get next level number
        max_number = db.session.execute(
            text(
                """SELECT COALESCE(MAX(number), 0)
                   FROM campaign_levels WHERE chapter_id = :chapter_id"""
            ),
            {"chapter_id": chapter_id},
        ).scalar()

        result = db.session.execute(
            text(
                """
                INSERT INTO campaign_levels (chapter_id, number, monster_id, is_boss, title,
                    dialogue_before, dialogue_after, difficulty_multiplier,
                    required_power, xp_reward, stars_max, is_active)
                VALUES (:chapter_id, :number, :monster_id, :is_boss, :title,
                    :dialogue_before, :dialogue_after, :difficulty_multiplier,
                    :required_power, :xp_reward, :stars_max, true)
                RETURNING id
            """
            ),
            {
                "chapter_id": chapter_id,
                "number": max_number + 1,
                "monster_id": data.get("monster_id"),
                "is_boss": data.get("is_boss", False),
                "title": data.get("title"),
                "dialogue_before": data.get("dialogue_before"),
                "dialogue_after": data.get("dialogue_after"),
                "difficulty_multiplier": data.get("difficulty_multiplier", 1.0),
                "required_power": data.get("required_power", 0),
                "xp_reward": data.get("xp_reward", 50),
                "stars_max": data.get("stars_max", 3),
            },
        )
        level_id = result.scalar()
        db.session.commit()
        return jsonify({"success": True, "id": level_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/campaign/levels/<int:level_id>/update", methods=["POST"])
@login_required
def update_level(level_id: int):
    """Update level details."""
    data = request.json

    try:
        updates = []
        params = {"level_id": level_id}

        for field in ["monster_id", "is_boss", "title", "dialogue_before",
                      "dialogue_after", "difficulty_multiplier", "required_power",
                      "xp_reward", "stars_max", "is_active"]:
            if field in data:
                updates.append(f"{field} = :{field}")
                params[field] = data[field]

        if updates:
            db.session.execute(
                text(
                    f"UPDATE campaign_levels SET {', '.join(updates)} WHERE id = :level_id"
                ),
                params,
            )
            db.session.commit()

        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/campaign/levels/<int:level_id>/delete", methods=["POST"])
@login_required
def delete_level(level_id: int):
    """Delete a level."""
    try:
        db.session.execute(
            text("DELETE FROM campaign_levels WHERE id = :level_id"),
            {"level_id": level_id},
        )
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
