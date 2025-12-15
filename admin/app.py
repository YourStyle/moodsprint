"""Admin panel application."""

import os
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
            text(
                "SELECT favorite_genre FROM onboarding_profiles WHERE user_id = :uid"
            ),
            {"uid": user_id},
        ).fetchone()
    except Exception:
        user_genre = None

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
