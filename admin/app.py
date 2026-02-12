"""Admin panel application."""

import json
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
app.config["APPLICATION_ROOT"] = "/admin"


# Middleware to handle reverse proxy with path prefix
class PrefixMiddleware:
    def __init__(self, app, prefix="/admin"):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        # Check if path starts with prefix
        if environ.get("PATH_INFO", "").startswith(self.prefix):
            environ["PATH_INFO"] = environ["PATH_INFO"][len(self.prefix):] or "/"
            environ["SCRIPT_NAME"] = self.prefix
        return self.app(environ, start_response)


app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix="/admin")

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
            COUNT(DISTINCT CASE
                WHEN u.last_activity_date >= DATE_TRUNC('week', u.created_at) + INTERVAL '7 days'
                THEN u.id END) as week1,
            COUNT(DISTINCT CASE
                WHEN u.last_activity_date >= DATE_TRUNC('week', u.created_at) + INTERVAL '14 days'
                THEN u.id END) as week2,
            COUNT(DISTINCT CASE
                WHEN u.last_activity_date >= DATE_TRUNC('week', u.created_at) + INTERVAL '21 days'
                THEN u.id END) as week3
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


@app.route("/users/<int:user_id>/give-card", methods=["POST"])
@login_required
def give_card_to_user(user_id: int):
    """Give a specific card to a user."""
    data = request.json or {}
    template_id = data.get("template_id")
    rarity = data.get("rarity", "common")

    if not template_id:
        return jsonify({"success": False, "error": "template_id is required"}), 400

    valid_rarities = ["common", "uncommon", "rare", "epic", "legendary"]
    if rarity not in valid_rarities:
        return jsonify({"success": False, "error": f"Invalid rarity. Must be one of: {valid_rarities}"}), 400

    # Get template
    template = db.session.execute(
        text("""
            SELECT id, name, description, genre, base_hp, base_attack, image_url, emoji
            FROM card_templates WHERE id = :id
        """),
        {"id": template_id},
    ).fetchone()

    if not template:
        return jsonify({"success": False, "error": "Template not found"}), 404

    # Check if user exists
    user = db.session.execute(
        text("SELECT id, first_name, username, telegram_id FROM users WHERE id = :id"),
        {"id": user_id},
    ).fetchone()

    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    # Rarity multipliers for stats
    rarity_multipliers = {
        "common": 1.0,
        "uncommon": 1.2,
        "rare": 1.5,
        "epic": 2.0,
        "legendary": 3.0,
    }
    multiplier = rarity_multipliers.get(rarity, 1.0)

    try:
        # Create the card for the user
        result = db.session.execute(
            text("""
                INSERT INTO user_cards (
                    user_id, template_id, name, description, genre, rarity,
                    attack, hp, max_hp, image_url, emoji, level, xp, is_in_deck
                )
                VALUES (
                    :user_id, :template_id, :name, :description, :genre, :rarity,
                    :attack, :hp, :max_hp, :image_url, :emoji, 1, 0, false
                )
                RETURNING id
            """),
            {
                "user_id": user_id,
                "template_id": template_id,
                "name": template[1],  # name
                "description": template[2],  # description
                "genre": template[3],  # genre
                "rarity": rarity,
                "attack": int(template[5] * multiplier),  # base_attack * multiplier
                "hp": int(template[4] * multiplier),  # base_hp * multiplier
                "max_hp": int(template[4] * multiplier),
                "image_url": template[6],  # image_url
                "emoji": template[7] or "🎴",  # emoji
            },
        )
        card_id = result.fetchone()[0]
        db.session.commit()

        # Send Telegram notification to the user
        telegram_id = user[3]  # telegram_id from query
        if telegram_id and BOT_TOKEN:
            import requests as http_requests

            msg = (
                f"🎁 <b>Вам пришёл подарок!</b>\n\n"
                f"Вы получили карту <b>{template[1]}</b> ({rarity})\n\n"
                f"Откройте приложение, чтобы посмотреть!"
            )
            try:
                http_requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": telegram_id,
                        "text": msg,
                        "parse_mode": "HTML",
                    },
                    timeout=10,
                )
            except Exception:
                pass  # Don't fail card creation if notification fails

        return jsonify({
            "success": True,
            "message": f"Card '{template[1]}' ({rarity}) given to user {user[1] or user[2] or user_id}",
            "card_id": card_id,
            "card_name": template[1],
            "rarity": rarity,
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


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
        return jsonify(
            {
                "success": True,
                "data": {
                    "message": (
                        "All monsters already have images"
                        if not genre
                        else f"All {genre} monsters have images"
                    ),
                    "generated": 0,
                    "failed": 0,
                    "remaining": 0,
                },
            }
        )

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

    return jsonify(
        {
            "success": True,
            "data": {
                "generated": generated,
                "failed": failed,
                "remaining": remaining,
                "message": f"Generated {generated} images. {remaining} remaining.",
            },
        }
    )


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
            SELECT id, name, name_en, description, description_en, genre, base_level, base_hp, base_attack,
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
            SELECT id, name, name_en, description, description_en, emoji, attack, hp, ability
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
        base_level = data.get("base_level", 1)
        base_hp = data.get("base_hp", 100)
        base_attack = data.get("base_attack", 10)

        result = db.session.execute(
            text(
                """
                INSERT INTO monsters (name, description, genre, base_level, base_hp, base_attack,
                    level, hp, attack, sprite_url, emoji, is_boss)
                VALUES (:name, :description, :genre, :base_level, :base_hp, :base_attack,
                    :level, :hp, :attack, :sprite_url, :emoji, :is_boss)
                RETURNING id
            """
            ),
            {
                "name": data["name"],
                "description": data.get("description"),
                "genre": data["genre"],
                "base_level": base_level,
                "base_hp": base_hp,
                "base_attack": base_attack,
                "level": base_level,
                "hp": base_hp,
                "attack": base_attack,
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

        for field in [
            "name",
            "name_en",
            "description",
            "description_en",
            "genre",
            "base_level",
            "base_hp",
            "base_attack",
            "sprite_url",
            "emoji",
            "is_boss",
        ]:
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


@app.route("/monsters/<int:monster_id>/upload-image", methods=["POST"])
@login_required
def upload_monster_image(monster_id: int):
    """Upload image for a monster."""
    import uuid

    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image file"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No selected file"}), 400

    # Check file extension
    allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        return jsonify({"success": False, "error": f"Invalid file type. Allowed: {allowed_extensions}"}), 400

    try:
        # Generate unique filename
        filename = f"monster_{uuid.uuid4()}.{ext}"
        filepath = os.path.join("/app/static/monster_images", filename)

        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Save file
        file.save(filepath)

        # Update database
        image_url = f"/static/monster_images/{filename}"
        db.session.execute(
            text("UPDATE monsters SET sprite_url = :url WHERE id = :id"),
            {"url": image_url, "id": monster_id},
        )
        db.session.commit()

        return jsonify({"success": True, "sprite_url": image_url})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/cards/templates/<int:template_id>/upload-image", methods=["POST"])
@login_required
def upload_card_template_image(template_id: int):
    """Upload image for a card template."""
    import uuid

    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image file"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No selected file"}), 400

    # Check file extension
    allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        return jsonify({"success": False, "error": f"Invalid file type. Allowed: {allowed_extensions}"}), 400

    try:
        # Generate unique filename
        filename = f"card_{uuid.uuid4()}.{ext}"
        filepath = os.path.join("/app/media", filename)

        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Save file
        file.save(filepath)

        # Update database
        image_url = f"/media/{filename}"
        db.session.execute(
            text("UPDATE card_templates SET image_url = :url WHERE id = :id"),
            {"url": image_url, "id": template_id},
        )
        db.session.commit()

        return jsonify({"success": True, "image_url": image_url})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/monsters/<int:monster_id>/set-image", methods=["POST"])
@login_required
def set_monster_image_from_media(monster_id: int):
    """Set monster image from media URL."""
    data = request.json or {}
    image_url = data.get("image_url")

    if not image_url:
        return jsonify({"success": False, "error": "No image_url provided"}), 400

    # Validate the URL is from our media storage
    if not image_url.startswith("/media/"):
        return jsonify({"success": False, "error": "Invalid image URL. Must be from /media/"}), 400

    # Update the monster
    try:
        db.session.execute(
            text("UPDATE monsters SET sprite_url = :url WHERE id = :id"),
            {"url": image_url, "id": monster_id},
        )
        db.session.commit()
        return jsonify({"success": True, "sprite_url": image_url})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


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
                INSERT INTO monster_cards (monster_id, name, name_en, description, description_en, emoji, attack, hp, ability)
                VALUES (:monster_id, :name, :name_en, :description, :description_en, :emoji, :attack, :hp, :ability)
                RETURNING id
            """
            ),
            {
                "monster_id": monster_id,
                "name": data["name"],
                "name_en": data.get("name_en"),
                "description": data.get("description"),
                "description_en": data.get("description_en"),
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

        for field in ["name", "name_en", "description", "description_en", "emoji", "attack", "hp", "ability"]:
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
                INSERT INTO seasonal_events
                    (code, name, description, event_type, start_date, end_date,
                     emoji, theme_color, xp_multiplier, is_active)
                VALUES
                    (:code, :name, :description, :event_type, :start_date, :end_date,
                     :emoji, :theme_color, :xp_multiplier, true)
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
    """List all campaign chapters grouped by genre."""
    chapters = db.session.execute(
        text(
            """
            SELECT c.id, c.number, c.name, c.genre, c.description,
                   c.emoji, c.background_color, c.required_power,
                   c.xp_reward, c.guaranteed_card_rarity, c.is_active,
                   c.story_intro, c.story_outro, c.image_url,
                   (SELECT COUNT(*) FROM campaign_levels WHERE chapter_id = c.id) as levels_count
            FROM campaign_chapters c
            ORDER BY c.genre, c.number
        """
        )
    ).fetchall()

    # Group chapters by genre
    chapters_by_genre = {}
    for chapter in chapters:
        chapter_dict = dict(chapter._mapping)
        genre = chapter_dict.get("genre") or "other"
        if genre not in chapters_by_genre:
            chapters_by_genre[genre] = []
        chapters_by_genre[genre].append(chapter_dict)

    return render_template(
        "campaign.html",
        chapters=[dict(row._mapping) for row in chapters] if chapters else [],
        chapters_by_genre=chapters_by_genre,
    )


@app.route("/campaign/chapters/new", methods=["POST"])
@login_required
def create_chapter():
    """Create a new campaign chapter."""
    data = request.json
    try:
        genre = data["genre"]

        # Get next chapter number for this specific genre
        max_number = db.session.execute(
            text(
                "SELECT COALESCE(MAX(number), 0) FROM campaign_chapters WHERE genre = :genre"
            ),
            {"genre": genre},
        ).scalar()

        result = db.session.execute(
            text(
                """
                INSERT INTO campaign_chapters (number, name, name_en, genre, description, description_en, emoji,
                    background_color, required_power, xp_reward, guaranteed_card_rarity,
                    story_intro, story_intro_en, story_outro, story_outro_en, is_active)
                VALUES (:number, :name, :name_en, :genre, :description, :description_en, :emoji,
                    :background_color, :required_power, :xp_reward, :guaranteed_card_rarity,
                    :story_intro, :story_intro_en, :story_outro, :story_outro_en, true)
                RETURNING id
            """
            ),
            {
                "number": max_number + 1,
                "name": data["name"],
                "name_en": data.get("name_en"),
                "genre": genre,
                "description": data.get("description"),
                "description_en": data.get("description_en"),
                "emoji": data.get("emoji", "📖"),
                "background_color": data.get("background_color", "#1a1a2e"),
                "required_power": data.get("required_power", 0),
                "xp_reward": data.get("xp_reward", 500),
                "guaranteed_card_rarity": data.get("guaranteed_card_rarity", "rare"),
                "story_intro": data.get("story_intro"),
                "story_intro_en": data.get("story_intro_en"),
                "story_outro": data.get("story_outro"),
                "story_outro_en": data.get("story_outro_en"),
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
            SELECT id, number, name, name_en, genre, description, description_en, emoji, background_color,
                   image_url, required_power, xp_reward, guaranteed_card_rarity, is_active,
                   story_intro, story_intro_en, story_outro, story_outro_en
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
            SELECT l.id, l.number, l.monster_id, l.is_boss, l.is_final, l.title, l.title_en,
                   l.dialogue_before, l.dialogue_before_en, l.dialogue_after, l.dialogue_after_en,
                   l.difficulty_multiplier, l.required_power, l.xp_reward, l.stars_max, l.star_conditions, l.is_active,
                   m.name as monster_name, m.emoji as monster_emoji
            FROM campaign_levels l
            LEFT JOIN monsters m ON m.id = l.monster_id
            WHERE l.chapter_id = :chapter_id
            ORDER BY l.number
        """
        ),
        {"chapter_id": chapter_id},
    ).fetchall()

    # Filter monsters by chapter genre
    chapter_genre = chapter._mapping["genre"]
    all_monsters = db.session.execute(
        text("SELECT id, name, emoji, genre FROM monsters WHERE genre = :genre ORDER BY name"),
        {"genre": chapter_genre},
    ).fetchall()

    # Get chapter rewards
    rewards = db.session.execute(
        text("""SELECT id, reward_type, reward_data, name, description, emoji
                FROM campaign_rewards
                WHERE chapter_id = :chapter_id"""),
        {"chapter_id": chapter_id},
    ).fetchall()

    return render_template(
        "campaign_chapter.html",
        chapter=dict(chapter._mapping),
        levels=[dict(row._mapping) for row in levels] if levels else [],
        all_monsters=all_monsters,
        rewards=[dict(row._mapping) for row in rewards] if rewards else [],
    )


@app.route("/campaign/chapters/<int:chapter_id>/update", methods=["POST"])
@login_required
def update_chapter(chapter_id: int):
    """Update chapter details."""
    data = request.json

    try:
        updates = []
        params = {"chapter_id": chapter_id}

        for field in [
            "name",
            "name_en",
            "genre",
            "description",
            "description_en",
            "emoji",
            "background_color",
            "image_url",
            "required_power",
            "xp_reward",
            "guaranteed_card_rarity",
            "story_intro",
            "story_intro_en",
            "story_outro",
            "story_outro_en",
            "is_active",
        ]:
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


@app.route("/campaign/chapters/<int:chapter_id>/delete", methods=["POST"])
@login_required
def delete_chapter(chapter_id: int):
    """Delete a campaign chapter and its levels."""
    try:
        # Get chapter genre for renumbering
        chapter = db.session.execute(
            text("SELECT genre, number FROM campaign_chapters WHERE id = :id"),
            {"id": chapter_id},
        ).fetchone()

        if not chapter:
            return jsonify({"success": False, "error": "Chapter not found"}), 404

        genre = chapter[0]
        deleted_number = chapter[1]

        # Delete levels first (cascade should handle this but being explicit)
        db.session.execute(
            text("DELETE FROM campaign_levels WHERE chapter_id = :id"),
            {"id": chapter_id},
        )

        # Delete chapter
        db.session.execute(
            text("DELETE FROM campaign_chapters WHERE id = :id"),
            {"id": chapter_id},
        )

        # Renumber remaining chapters in same genre
        db.session.execute(
            text("""
                UPDATE campaign_chapters
                SET number = number - 1
                WHERE genre = :genre AND number > :deleted_number
            """),
            {"genre": genre, "deleted_number": deleted_number},
        )

        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/campaign/chapters/renumber/<genre>", methods=["POST"])
@login_required
def renumber_chapters(genre: str):
    """Renumber chapters in a genre to be sequential starting from 1."""
    try:
        # Get all chapters in genre ordered by current number
        chapters = db.session.execute(
            text("""
                SELECT id FROM campaign_chapters
                WHERE genre = :genre
                ORDER BY number
            """),
            {"genre": genre},
        ).fetchall()

        # Update each chapter with sequential number
        for idx, chapter in enumerate(chapters, start=1):
            db.session.execute(
                text("UPDATE campaign_chapters SET number = :num WHERE id = :id"),
                {"num": idx, "id": chapter[0]},
            )

        db.session.commit()
        return jsonify({
            "success": True,
            "message": f"Renumbered {len(chapters)} chapters in {genre}",
        })
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
                INSERT INTO campaign_levels (chapter_id, number, monster_id, is_boss, is_final, title, title_en,
                    dialogue_before, dialogue_before_en, dialogue_after, dialogue_after_en, difficulty_multiplier,
                    required_power, xp_reward, stars_max, star_conditions, is_active)
                VALUES (:chapter_id, :number, :monster_id, :is_boss, :is_final, :title, :title_en,
                    :dialogue_before, :dialogue_before_en, :dialogue_after, :dialogue_after_en, :difficulty_multiplier,
                    :required_power, :xp_reward, :stars_max, :star_conditions, true)
                RETURNING id
            """
            ),
            {
                "chapter_id": chapter_id,
                "number": max_number + 1,
                "monster_id": data.get("monster_id"),
                "is_boss": data.get("is_boss", False),
                "is_final": data.get("is_final", False),
                "title": data.get("title"),
                "title_en": data.get("title_en"),
                "dialogue_before": json.dumps(data.get("dialogue_before"))
                if data.get("dialogue_before")
                else None,
                "dialogue_before_en": json.dumps(data.get("dialogue_before_en"))
                if data.get("dialogue_before_en")
                else None,
                "dialogue_after": json.dumps(data.get("dialogue_after"))
                if data.get("dialogue_after")
                else None,
                "dialogue_after_en": json.dumps(data.get("dialogue_after_en"))
                if data.get("dialogue_after_en")
                else None,
                "difficulty_multiplier": data.get("difficulty_multiplier", 1.0),
                "required_power": data.get("required_power", 0),
                "xp_reward": data.get("xp_reward", 50),
                "stars_max": data.get("stars_max", 3),
                "star_conditions": json.dumps(data.get("star_conditions"))
                if data.get("star_conditions")
                else None,
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

        json_fields = ["dialogue_before", "dialogue_before_en", "dialogue_after", "dialogue_after_en", "star_conditions"]
        for field in [
            "monster_id",
            "is_boss",
            "is_final",
            "title",
            "title_en",
            "dialogue_before",
            "dialogue_before_en",
            "dialogue_after",
            "dialogue_after_en",
            "difficulty_multiplier",
            "required_power",
            "xp_reward",
            "stars_max",
            "star_conditions",
            "is_active",
        ]:
            if field in data:
                updates.append(f"{field} = :{field}")
                value = data[field]
                # Serialize JSON fields
                if field in json_fields and value is not None:
                    value = json.dumps(value)
                params[field] = value

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


# ============ Campaign Rewards ============


@app.route("/campaign/chapters/<int:chapter_id>/rewards", methods=["GET"])
@login_required
def get_chapter_rewards(chapter_id: int):
    """Get rewards for a chapter."""
    result = db.session.execute(
        text("""SELECT id, reward_type, reward_data, name, description, emoji
                FROM campaign_rewards
                WHERE chapter_id = :chapter_id"""),
        {"chapter_id": chapter_id},
    )
    rewards = [dict(row._mapping) for row in result]
    return jsonify({"success": True, "rewards": rewards})


@app.route("/campaign/chapters/<int:chapter_id>/rewards/new", methods=["POST"])
@login_required
def create_chapter_reward(chapter_id: int):
    """Create a new reward for a chapter."""
    import json

    data = request.json
    reward_type = data.get("reward_type", "sparks")
    reward_data = data.get("reward_data", {})

    try:
        db.session.execute(
            text("""
                INSERT INTO campaign_rewards
                    (chapter_id, reward_type, reward_data, name, description, emoji)
                VALUES
                    (:chapter_id, :reward_type, :reward_data, :name, :description, :emoji)
            """),
            {
                "chapter_id": chapter_id,
                "reward_type": reward_type,
                "reward_data": json.dumps(reward_data),
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "emoji": data.get("emoji", "✨"),
            },
        )
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/campaign/rewards/<int:reward_id>/delete", methods=["POST"])
@login_required
def delete_chapter_reward(reward_id: int):
    """Delete a chapter reward."""
    try:
        db.session.execute(
            text("DELETE FROM campaign_rewards WHERE id = :reward_id"),
            {"reward_id": reward_id},
        )
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/campaign/generate-dialogue", methods=["POST"])
@login_required
def generate_dialogue():
    """Generate dialogue using AI with genre-based conversation memory."""
    import json

    import openai

    data = request.json
    chapter_name = data.get("chapter_name", "")
    chapter_genre = data.get("chapter_genre", "fantasy")
    chapter_description = data.get("chapter_description", "")
    monster_name = data.get("monster_name", "Монстр")
    dialog_type = data.get("dialog_type", "before")
    existing_lines = data.get("existing_lines", [])
    reset_context = data.get("reset_context", False)

    # Genre descriptions for context
    genre_contexts = {
        "fantasy": "эпическое фэнтези в стиле Властелина Колец, рыцари и магия, средневековье",
        "magic": "волшебный мир как в Гарри Поттере, заклинания и магические существа, школа магии",
        "scifi": "научная фантастика, космос и технологии будущего, инопланетяне и роботы",
        "cyberpunk": "киберпанк, неоновые города и хакеры, корпорации и имплантаты",
        "anime": "аниме стиль, драматичные битвы и эмоциональные персонажи, яркие атаки",
    }

    genre_context = genre_contexts.get(chapter_genre, "фэнтези")

    # Get previous conversation state for this genre
    previous_response_id = None
    if not reset_context:
        try:
            state = db.session.execute(
                text("SELECT last_response_id FROM ai_conversation_state WHERE genre = :genre"),
                {"genre": chapter_genre},
            ).fetchone()
            if state and state[0]:
                previous_response_id = state[0]
        except Exception:
            pass  # Table might not exist yet

    # Build prompt
    if dialog_type == "before":
        context = f"""Ты пишешь диалог ПЕРЕД битвой для мобильной игры в жанре {genre_context}.

Глава: {chapter_name}
{f"Описание: {chapter_description}" if chapter_description else ""}
Монстр: {monster_name}

Напиши короткий диалог (3-5 реплик) где монстр угрожает герою, а герой храбро отвечает.
Диалог должен быть драматичным и подходящим для жанра."""
    else:
        context = f"""Ты пишешь диалог ПОСЛЕ победы над монстром для мобильной игры в жанре {genre_context}.

Глава: {chapter_name}
{f"Описание: {chapter_description}" if chapter_description else ""}
Монстр: {monster_name}

Напиши короткий диалог (2-4 реплики) где монстр признаёт поражение, а герой торжествует.
Можешь добавить намёк на следующее приключение."""

    if existing_lines:
        context += "\n\nУже есть такие реплики (продолжи их):\n"
        for line in existing_lines[-3:]:
            context += f"- {line.get('speaker', 'Персонаж')}: {line.get('text', '')}\n"

    # Available events for AI to use
    context += """

Для каждой реплики можешь указать событие (опционально):
- start_battle: начать битву
- skip_battle: монстр сдаётся, битва пропускается
- buff_player: усилить игрока (+20% атаки)
- debuff_monster: ослабить монстра (-20% HP)
- bonus_xp: бонусный опыт (+50 XP)
- heal_cards: исцелить все карты

Верни JSON массив в формате:
[
  {"speaker": "Monster", "text": "Текст реплики монстра", "emoji": "👹"},
  {"speaker": "Hero", "text": "Ответ героя", "emoji": "🦸"},
  {"speaker": "Narrator", "text": "Описание действия", "emoji": "📖", "event": "start_battle"}
]

Допустимые speaker: Monster, Hero, Narrator.
Выбирай подходящие эмодзи для жанра и настроения."""

    try:
        openai_key = os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            return jsonify({"success": False, "error": "OpenAI API key not configured"})

        # Create client with optional proxy support
        openai_proxy = os.environ.get("OPENAI_PROXY")
        if openai_proxy:
            import httpx

            http_client = httpx.Client(proxy=openai_proxy)
            client = openai.OpenAI(api_key=openai_key, http_client=http_client)
        else:
            client = openai.OpenAI(api_key=openai_key)

        # GPT-5.2 uses the Responses API with conversation memory
        system_instruction = f"""Ты сценарист для мобильной RPG игры в жанре {genre_context}.
Ты помнишь все предыдущие диалоги и персонажей этого жанра.
Пиши короткие драматичные диалоги на русском языке.
Сохраняй последовательность сюжета и характеры персонажей.
Отвечай ТОЛЬКО валидным JSON массивом."""

        full_input = f"{system_instruction}\n\n{context}"

        # Build API request with conversation memory
        api_params = {
            "model": "gpt-5-mini",
            "input": full_input,
        }

        # Chain with previous response for genre context continuity
        if previous_response_id:
            api_params["previous_response_id"] = previous_response_id

        response = client.responses.create(**api_params)

        # Save new response_id for this genre
        try:
            db.session.execute(
                text("""
                    INSERT INTO ai_conversation_state (genre, last_response_id, updated_at)
                    VALUES (:genre, :response_id, NOW())
                    ON CONFLICT (genre) DO UPDATE SET
                        last_response_id = :response_id,
                        updated_at = NOW()
                """),
                {"genre": chapter_genre, "response_id": response.id},
            )
            db.session.commit()
        except Exception:
            db.session.rollback()  # Non-critical, continue anyway

        content = response.output_text.strip()

        # Parse JSON from response
        # Handle markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        dialogue = json.loads(content)

        # Validate structure
        valid_dialogue = []
        for line in dialogue:
            if isinstance(line, dict) and "speaker" in line and "text" in line:
                valid_line = {
                    "speaker": line.get("speaker", "Narrator"),
                    "text": line.get("text", ""),
                    "emoji": line.get("emoji", "💬"),
                }
                if line.get("event"):
                    valid_line["event"] = line["event"]
                if line.get("choices"):
                    valid_line["choices"] = line["choices"]
                valid_dialogue.append(valid_line)

        return jsonify({
            "success": True,
            "dialogue": valid_dialogue,
            "context_used": previous_response_id is not None,
            "genre": chapter_genre,
        })

    except json.JSONDecodeError as e:
        return jsonify({"success": False, "error": f"Invalid JSON from AI: {str(e)}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/campaign/ai-contexts")
@login_required
def ai_contexts():
    """View AI conversation contexts by genre."""
    try:
        contexts = db.session.execute(
            text("""
                SELECT genre, last_response_id, updated_at
                FROM ai_conversation_state
                ORDER BY updated_at DESC
            """)
        ).fetchall()

        return jsonify({
            "success": True,
            "contexts": [
                {
                    "genre": row[0],
                    "has_context": row[1] is not None,
                    "updated_at": str(row[2]) if row[2] else None,
                }
                for row in contexts
            ],
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/campaign/ai-contexts/<genre>/reset", methods=["POST"])
@login_required
def reset_ai_context(genre: str):
    """Reset AI conversation context for a specific genre."""
    try:
        db.session.execute(
            text("DELETE FROM ai_conversation_state WHERE genre = :genre"),
            {"genre": genre},
        )
        db.session.commit()
        return jsonify({"success": True, "message": f"Context for {genre} reset"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})


@app.route("/campaign/ai-contexts/reset-all", methods=["POST"])
@login_required
def reset_all_ai_contexts():
    """Reset all AI conversation contexts."""
    try:
        db.session.execute(text("DELETE FROM ai_conversation_state"))
        db.session.commit()
        return jsonify({"success": True, "message": "All contexts reset"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})


@app.route("/campaign/generate-chapter-content", methods=["POST"])
@login_required
def generate_chapter_content():
    """Generate chapter name, description, intro and outro using AI."""
    import openai

    data = request.json
    genre = data.get("genre", "fantasy")

    # Get existing chapters for context
    existing_chapters = db.session.execute(
        text("SELECT name, description FROM campaign_chapters WHERE genre = :genre ORDER BY number"),
        {"genre": genre},
    ).fetchall()

    genre_contexts = {
        "fantasy": "эпическое фэнтези в стиле Властелина Колец, рыцари и магия",
        "magic": "волшебный мир как в Гарри Поттере, заклинания и магия",
        "scifi": "научная фантастика, космос и технологии будущего",
        "cyberpunk": "киберпанк, неоновые города и хакеры",
        "anime": "аниме стиль, драматичные битвы и яркие персонажи",
    }
    genre_context = genre_contexts.get(genre, "фэнтези")

    existing_context = ""
    if existing_chapters:
        existing_context = "\n\nУже существующие главы этого жанра:\n"
        for ch in existing_chapters:
            existing_context += f"- {ch[0]}: {ch[1] or 'без описания'}\n"
        existing_context += "\nСоздай новую главу, которая продолжает историю."

    prompt = f"""Ты сценарист для мобильной RPG игры в жанре {genre_context}.
{existing_context}

Создай новую главу кампании. Верни JSON:
{{
    "name": "Название главы (2-4 слова, эпичное)",
    "description": "Краткое описание главы (1-2 предложения)",
    "emoji": "Подходящий эмодзи для главы",
    "story_intro": "Вступительный текст главы (3-5 предложений, погружающий в атмосферу)",
    "story_outro": "Завершающий текст главы (2-3 предложения, триумф после победы)"
}}

Отвечай ТОЛЬКО валидным JSON."""

    try:
        openai_key = os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            return jsonify({"success": False, "error": "OpenAI API key not configured"})

        openai_proxy = os.environ.get("OPENAI_PROXY")
        if openai_proxy:
            import httpx
            http_client = httpx.Client(proxy=openai_proxy)
            client = openai.OpenAI(api_key=openai_key, http_client=http_client)
        else:
            client = openai.OpenAI(api_key=openai_key)

        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt,
        )

        content = response.output_text.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)
        return jsonify({"success": True, "content": result})

    except json.JSONDecodeError as e:
        return jsonify({"success": False, "error": f"Invalid JSON from AI: {str(e)}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/campaign/generate-chapter-image", methods=["POST"])
@login_required
def generate_chapter_image():
    """Generate chapter landscape image using Stability AI."""
    import requests
    from pathlib import Path
    import uuid

    data = request.json
    chapter_name = data.get("name", "")
    chapter_description = data.get("description", "")
    genre = data.get("genre", "fantasy")

    genre_styles = {
        "fantasy": "epic fantasy landscape, medieval castle, mountains, magical atmosphere",
        "magic": "magical academy, floating islands, aurora borealis, mystical towers",
        "scifi": "futuristic cityscape, space station, alien planet, neon lights",
        "cyberpunk": "cyberpunk city, neon signs, rain, dark alley, holographic billboards",
        "anime": "anime style landscape, cherry blossoms, dramatic sky, vibrant colors",
    }
    style = genre_styles.get(genre, genre_styles["fantasy"])

    prompt = f"{chapter_name}, {chapter_description}, {style}, panoramic view, cinematic lighting, highly detailed, game art, 4k"

    stability_key = os.environ.get("STABILITY_API_KEY")
    if not stability_key:
        return jsonify({"success": False, "error": "Stability API key not configured"})

    try:
        response = requests.post(
            "https://api.stability.ai/v2beta/stable-image/generate/sd3",
            headers={
                "authorization": f"Bearer {stability_key}",
                "accept": "image/*",
            },
            files={"none": ""},
            data={
                "prompt": prompt,
                "model": "sd3.5-large-turbo",
                "output_format": "jpeg",
                "aspect_ratio": "16:9",
            },
            timeout=60,
        )

        if response.status_code == 200:
            # Save image
            images_dir = Path("/app/static/chapter_images")
            images_dir.mkdir(parents=True, exist_ok=True)

            image_filename = f"chapter_{uuid.uuid4().hex[:8]}.jpg"
            image_path = images_dir / image_filename

            with open(image_path, "wb") as f:
                f.write(response.content)

            image_url = f"/static/chapter_images/{image_filename}"
            return jsonify({"success": True, "image_url": image_url})
        else:
            return jsonify({
                "success": False,
                "error": f"Stability API error: {response.status_code} - {response.text}"
            })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/campaign/levels/<int:level_id>/export", methods=["GET"])
@login_required
def export_level_json(level_id: int):
    """Export chapter template for AI prompting (genre, monsters, dialogue format)."""
    level = db.session.execute(
        text("""
            SELECT l.id, l.number, l.is_boss, l.title, l.title_en,
                   c.id as chapter_id, c.number as chapter_number,
                   c.name as chapter_name, c.name_en as chapter_name_en,
                   c.genre as chapter_genre,
                   c.description as chapter_description,
                   c.description_en as chapter_description_en,
                   c.story_intro, c.story_intro_en,
                   c.story_outro, c.story_outro_en
            FROM campaign_levels l
            LEFT JOIN campaign_chapters c ON c.id = l.chapter_id
            WHERE l.id = :level_id
        """),
        {"level_id": level_id},
    ).fetchone()

    if not level:
        return jsonify({"success": False, "error": "Level not found"}), 404

    level_dict = dict(level._mapping)
    genre = level_dict.get("chapter_genre") or "fantasy"

    # Get all monsters for this genre
    monsters = db.session.execute(
        text("""
            SELECT id, name, name_en, description, description_en, emoji, base_hp, base_attack, sprite_url
            FROM monsters WHERE genre = :genre ORDER BY base_hp ASC
        """),
        {"genre": genre},
    ).fetchall()

    # Get all levels in this chapter to show context
    chapter_levels = db.session.execute(
        text("""
            SELECT l.number, l.title, l.title_en, l.is_boss, m.name as monster_name, m.name_en as monster_name_en
            FROM campaign_levels l
            LEFT JOIN monsters m ON m.id = l.monster_id
            WHERE l.chapter_id = :chapter_id
            ORDER BY l.number
        """),
        {"chapter_id": level_dict.get("chapter_id")},
    ).fetchall()

    # Template for AI to fill
    export_data = {
        "_instructions": "Заполни поля ниже для уровня. Выбери monster_id из available_monsters.",
        "level_to_fill": {
            "id": level_dict["id"],
            "number": level_dict["number"],
            "is_boss": level_dict["is_boss"],
            "title": level_dict.get("title"),  # AI should fill: короткое название уровня (RU)
            "title_en": level_dict.get("title_en"),  # AI should fill: level title (EN)
            "monster_id": None,  # AI should fill: ID из available_monsters
            "dialogue_before": [
                # AI should fill array of dialogue lines
                # {"speaker": "monster" | "narrator", "text": "...", "text_en": "..."}
            ],
            "dialogue_after": [
                # AI should fill array of dialogue lines
            ],
        },
        "chapter_context": {
            "number": level_dict["chapter_number"],
            "name": level_dict["chapter_name"],
            "name_en": level_dict.get("chapter_name_en"),
            "genre": genre,
            "description": level_dict["chapter_description"],
            "description_en": level_dict.get("chapter_description_en"),
            "story_intro": level_dict.get("story_intro"),
            "story_intro_en": level_dict.get("story_intro_en"),
            "story_outro": level_dict.get("story_outro"),
            "story_outro_en": level_dict.get("story_outro_en"),
        },
        "existing_levels": [
            {
                "number": lvl[0],
                "title": lvl[1],
                "title_en": lvl[2],
                "is_boss": lvl[3],
                "monster": lvl[4],
                "monster_en": lvl[5],
            }
            for lvl in chapter_levels
        ],
        "available_monsters": [
            {
                "id": m[0],
                "name": m[1],
                "name_en": m[2],
                "description": m[3],
                "description_en": m[4],
                "emoji": m[5],
                "base_hp": m[6],
                "base_attack": m[7],
                "has_image": bool(m[8]),
            }
            for m in monsters
        ],
        "dialogue_format": {
            "example": [
                {"speaker": "monster", "text": "Ты осмелился прийти сюда?", "text_en": "You dare to come here?"},
                {"speaker": "narrator", "text": "Монстр готовится к атаке...", "text_en": "The monster prepares to attack..."},
            ],
            "speakers": ["monster", "narrator", "hero"],
            "tips": [
                "dialogue_before: 2-4 реплики перед боем",
                "dialogue_after: 1-3 реплики после победы",
                "Используй характер монстра из его description",
                "Добавляй text_en для английского перевода каждой реплики",
            ],
        },
    }

    return jsonify({"success": True, "data": export_data})


@app.route("/campaign/levels/<int:level_id>/import", methods=["POST"])
@login_required
def import_level_json(level_id: int):
    """Import level data from JSON (monster, dialogues, title)."""
    data = request.json

    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400

    try:
        updates = []
        params = {"level_id": level_id}

        # Update title if provided
        if "title" in data:
            updates.append("title = :title")
            params["title"] = data["title"]

        if "title_en" in data:
            updates.append("title_en = :title_en")
            params["title_en"] = data["title_en"]

        # Update monster_id if provided
        if "monster_id" in data:
            updates.append("monster_id = :monster_id")
            params["monster_id"] = data["monster_id"]

        # Update dialogue_before if provided
        if "dialogue_before" in data:
            updates.append("dialogue_before = :dialogue_before")
            # Use 'is not None' to preserve empty arrays []
            params["dialogue_before"] = json.dumps(data["dialogue_before"]) if data["dialogue_before"] is not None else None

        if "dialogue_before_en" in data:
            updates.append("dialogue_before_en = :dialogue_before_en")
            params["dialogue_before_en"] = json.dumps(data["dialogue_before_en"]) if data["dialogue_before_en"] is not None else None

        # Update dialogue_after if provided
        if "dialogue_after" in data:
            updates.append("dialogue_after = :dialogue_after")
            # Use 'is not None' to preserve empty arrays []
            params["dialogue_after"] = json.dumps(data["dialogue_after"]) if data["dialogue_after"] is not None else None

        if "dialogue_after_en" in data:
            updates.append("dialogue_after_en = :dialogue_after_en")
            params["dialogue_after_en"] = json.dumps(data["dialogue_after_en"]) if data["dialogue_after_en"] is not None else None

        # Update difficulty_multiplier if provided
        if "difficulty_multiplier" in data:
            updates.append("difficulty_multiplier = :difficulty_multiplier")
            params["difficulty_multiplier"] = data["difficulty_multiplier"]

        # Update is_boss if provided
        if "is_boss" in data:
            updates.append("is_boss = :is_boss")
            params["is_boss"] = data["is_boss"]

        if updates:
            db.session.execute(
                text(f"UPDATE campaign_levels SET {', '.join(updates)} WHERE id = :level_id"),
                params,
            )
            db.session.commit()
            return jsonify({"success": True, "message": "Level updated successfully"})
        else:
            return jsonify({"success": False, "error": "No valid fields to update"}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/campaign/chapters/<int:chapter_id>/levels/bulk-import", methods=["POST"])
@login_required
def bulk_import_levels(chapter_id: int):
    """Import multiple levels from JSON array. Creates new levels in order."""
    data = request.json

    if not data or not isinstance(data, list):
        return jsonify({"success": False, "error": "Expected array of level data"}), 400

    if len(data) == 0:
        return jsonify({"success": False, "error": "Empty array provided"}), 400

    try:
        # Get current max level number
        max_number = db.session.execute(
            text(
                """SELECT COALESCE(MAX(number), 0)
                   FROM campaign_levels WHERE chapter_id = :chapter_id"""
            ),
            {"chapter_id": chapter_id},
        ).scalar()

        created_ids = []

        for idx, level_data in enumerate(data):
            # Extract level_to_fill if present (export format)
            if "level_to_fill" in level_data:
                level_data = level_data["level_to_fill"]

            level_number = max_number + idx + 1

            result = db.session.execute(
                text(
                    """
                    INSERT INTO campaign_levels (chapter_id, number, monster_id, is_boss, is_final, title, title_en,
                        dialogue_before, dialogue_before_en, dialogue_after, dialogue_after_en, difficulty_multiplier,
                        required_power, xp_reward, stars_max, star_conditions, is_active)
                    VALUES (:chapter_id, :number, :monster_id, :is_boss, :is_final, :title, :title_en,
                        :dialogue_before, :dialogue_before_en, :dialogue_after, :dialogue_after_en, :difficulty_multiplier,
                        :required_power, :xp_reward, :stars_max, :star_conditions, true)
                    RETURNING id
                """
                ),
                {
                    "chapter_id": chapter_id,
                    "number": level_number,
                    "monster_id": level_data.get("monster_id"),
                    "is_boss": level_data.get("is_boss", False),
                    "is_final": level_data.get("is_final", False),
                    "title": level_data.get("title"),
                    "title_en": level_data.get("title_en"),
                    "dialogue_before": json.dumps(level_data.get("dialogue_before"))
                    if level_data.get("dialogue_before")
                    else None,
                    "dialogue_before_en": json.dumps(level_data.get("dialogue_before_en"))
                    if level_data.get("dialogue_before_en")
                    else None,
                    "dialogue_after": json.dumps(level_data.get("dialogue_after"))
                    if level_data.get("dialogue_after")
                    else None,
                    "dialogue_after_en": json.dumps(level_data.get("dialogue_after_en"))
                    if level_data.get("dialogue_after_en")
                    else None,
                    "difficulty_multiplier": level_data.get("difficulty_multiplier", 1.0),
                    "required_power": level_data.get("required_power", 0),
                    "xp_reward": level_data.get("xp_reward", 50),
                    "stars_max": level_data.get("stars_max", 3),
                    "star_conditions": json.dumps(level_data.get("star_conditions"))
                    if level_data.get("star_conditions")
                    else None,
                },
            )
            level_id = result.scalar()
            created_ids.append(level_id)

        db.session.commit()
        return jsonify({
            "success": True,
            "message": f"Created {len(created_ids)} levels",
            "ids": created_ids
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/campaign/generate-level", methods=["POST"])
@login_required
def generate_level():
    """Generate level name, monster and dialogue using AI."""
    import openai

    data = request.json
    chapter_name = data.get("chapter_name", "")
    chapter_genre = data.get("chapter_genre", "fantasy")
    chapter_description = data.get("chapter_description", "")
    is_boss = data.get("is_boss", False)
    level_number = data.get("level_number", 1)
    total_levels = data.get("total_levels", 5)

    # Get available monsters for this genre
    monsters = db.session.execute(
        text("SELECT id, name, description FROM monsters WHERE genre = :genre"),
        {"genre": chapter_genre},
    ).fetchall()

    if not monsters:
        return jsonify({"success": False, "error": f"No monsters found for genre {chapter_genre}"})

    monster_list = "\n".join([f"- ID {m[0]}: {m[1]} ({m[2] or 'без описания'})" for m in monsters])

    # Get existing levels in this chapter for context
    existing_levels = db.session.execute(
        text("""SELECT cl.title, m.name as monster_name
                FROM campaign_levels cl
                LEFT JOIN monsters m ON cl.monster_id = m.id
                WHERE cl.chapter_id = (
                    SELECT id FROM campaign_chapters WHERE name = :chapter_name LIMIT 1
                )
                ORDER BY cl.number"""),
        {"chapter_name": chapter_name},
    ).fetchall()

    existing_context = ""
    if existing_levels:
        existing_context = "\nУже существующие уровни в этой главе:\n"
        for i, lvl in enumerate(existing_levels, 1):
            existing_context += f"- Уровень {i}: {lvl[0] or 'без названия'} (монстр: {lvl[1] or 'не указан'})\n"

    prompt = f"""Ты создаёшь уровень для RPG игры MoodSprint.

Глава: {chapter_name}
Описание главы: {chapter_description or 'не указано'}
Жанр: {chapter_genre}
Номер уровня: {level_number} из {total_levels}
Это босс: {'Да - финальный босс главы!' if is_boss else 'Нет'}
{existing_context}

Доступные монстры для этого жанра:
{monster_list}

Создай название уровня и выбери монстра. Учти:
- Название уровня должно быть атмосферным (2-4 слова на русском)
- Для раннего уровня выбирай более слабых монстров
- Для позднего уровня и босса - самого сильного

Верни JSON:
{{"level_name": "Название уровня", "monster_id": <число>}}

Отвечай ТОЛЬКО валидным JSON."""

    try:
        openai_key = os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            return jsonify({"success": False, "error": "OpenAI API key not configured"})

        openai_proxy = os.environ.get("OPENAI_PROXY")
        if openai_proxy:
            import httpx
            http_client = httpx.Client(proxy=openai_proxy)
            client = openai.OpenAI(api_key=openai_key, http_client=http_client)
        else:
            client = openai.OpenAI(api_key=openai_key)

        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt,
        )

        content = response.output_text.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)

        # Verify monster exists
        monster_id = result.get("monster_id")
        monster = db.session.execute(
            text("SELECT id, name, emoji FROM monsters WHERE id = :id AND genre = :genre"),
            {"id": monster_id, "genre": chapter_genre},
        ).fetchone()

        if not monster:
            # Fallback to first monster if AI suggested invalid one
            monster = db.session.execute(
                text("SELECT id, name, emoji FROM monsters WHERE genre = :genre LIMIT 1"),
                {"genre": chapter_genre},
            ).fetchone()

        return jsonify({
            "success": True,
            "level_name": result.get("level_name", ""),
            "monster_id": monster[0] if monster else None,
            "monster_name": monster[1] if monster else "",
            "monster_emoji": monster[2] if monster else "",
        })

    except json.JSONDecodeError as e:
        return jsonify({"success": False, "error": f"Invalid JSON from AI: {str(e)}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# Card Pool Management
GENRES = ["magic", "fantasy", "scifi", "cyberpunk", "anime"]
RARITIES = ["common", "uncommon", "rare", "epic", "legendary"]
BASE_TEMPLATES_COUNT = 5
RARITY_POOL_FACTORS = {
    "common": 0.5,
    "uncommon": 0.3,
    "rare": 0.2,
    "epic": 0.1,
    "legendary": None,  # Always unique
}


@app.route("/card-pool")
@login_required
def card_pool():
    """Card pool management page."""
    # Get general stats
    total_templates = db.session.execute(
        text("SELECT COUNT(*) FROM card_templates")
    ).scalar() or 0

    active_templates = db.session.execute(
        text("SELECT COUNT(*) FROM card_templates WHERE is_active = true")
    ).scalar() or 0

    total_user_cards = db.session.execute(
        text("SELECT COUNT(*) FROM user_cards WHERE is_destroyed = false")
    ).scalar() or 0

    # Cards by rarity
    cards_by_rarity = {}
    for rarity in RARITIES:
        count = db.session.execute(
            text("SELECT COUNT(*) FROM user_cards WHERE rarity = :rarity AND is_destroyed = false"),
            {"rarity": rarity},
        ).scalar() or 0
        cards_by_rarity[rarity] = count

    # Genre data
    genres_data = {}
    for genre in GENRES:
        # Count users in genre
        users_count = db.session.execute(
            text("SELECT COUNT(*) FROM user_profiles WHERE favorite_genre = :genre"),
            {"genre": genre},
        ).scalar() or 0

        # Count templates
        active_count = db.session.execute(
            text("SELECT COUNT(*) FROM card_templates WHERE genre = :genre AND is_active = true"),
            {"genre": genre},
        ).scalar() or 0

        inactive_count = db.session.execute(
            text("SELECT COUNT(*) FROM card_templates WHERE genre = :genre AND is_active = false"),
            {"genre": genre},
        ).scalar() or 0

        # Rarity requirements
        rarity_status = {}
        for rarity in RARITIES:
            factor = RARITY_POOL_FACTORS.get(rarity)
            if factor is None:
                rarity_status[rarity] = {
                    "factor": None,
                    "required": "∞",
                    "needs_more": False,
                    "status": "always_new",
                }
            else:
                required = BASE_TEMPLATES_COUNT + int(users_count * factor)
                needs_more = active_count < required
                rarity_status[rarity] = {
                    "factor": factor,
                    "required": required,
                    "needs_more": needs_more,
                    "status": "needs_generation" if needs_more else "sufficient",
                }

        genres_data[genre] = {
            "users_count": users_count,
            "active_templates": active_count,
            "inactive_templates": inactive_count,
            "total_templates": active_count + inactive_count,
            "rarity_status": rarity_status,
        }

    return render_template(
        "card_pool.html",
        total_templates=total_templates,
        active_templates=active_templates,
        total_user_cards=total_user_cards,
        cards_by_rarity=cards_by_rarity,
        genres=GENRES,
        rarities=RARITIES,
        genres_data=genres_data,
    )


@app.route("/card-pool/<genre>/templates")
@login_required
def card_pool_templates(genre: str):
    """Get templates for a genre."""
    if genre not in GENRES:
        return jsonify({"success": False, "error": "Invalid genre"}), 400

    templates = db.session.execute(
        text("""
            SELECT id, name, name_en, description, description_en, genre, base_hp, base_attack,
                   image_url, emoji, ai_generated, is_active, created_at, rarity
            FROM card_templates
            WHERE genre = :genre
            ORDER BY is_active DESC, rarity NULLS LAST, created_at DESC
        """),
        {"genre": genre},
    ).fetchall()

    return jsonify({
        "success": True,
        "templates": [
            {
                "id": t[0],
                "name": t[1],
                "name_en": t[2],
                "description": t[3],
                "description_en": t[4],
                "genre": t[5],
                "base_hp": t[6],
                "base_attack": t[7],
                "image_url": t[8],
                "emoji": t[9],
                "ai_generated": t[10],
                "is_active": t[11],
                "created_at": t[12].isoformat() if t[12] else None,
                "rarity": t[13],
            }
            for t in templates
        ],
    })


@app.route("/card-pool/template/<int:template_id>/toggle", methods=["POST"])
@login_required
def toggle_card_template(template_id: int):
    """Toggle template active status."""
    template = db.session.execute(
        text("SELECT id, name, is_active FROM card_templates WHERE id = :id"),
        {"id": template_id},
    ).fetchone()

    if not template:
        return jsonify({"success": False, "error": "Template not found"}), 404

    new_status = not template[2]
    db.session.execute(
        text("UPDATE card_templates SET is_active = :status WHERE id = :id"),
        {"status": new_status, "id": template_id},
    )
    db.session.commit()

    return jsonify({
        "success": True,
        "template_id": template_id,
        "name": template[1],
        "is_active": new_status,
    })


@app.route("/card-pool/<genre>/generate", methods=["POST"])
@login_required
def generate_card_template(genre: str):
    """Generate a new card template."""
    import random

    if genre not in GENRES:
        return jsonify({"success": False, "error": "Invalid genre"}), 400

    data = request.json or {}
    custom_name = data.get("name")
    custom_description = data.get("description")

    genre_emojis = {
        "fantasy": ["🐉", "🧙", "⚔️", "🏰", "🦄", "🧝", "🗡️", "👑"],
        "magic": ["🔮", "✨", "🌟", "💫", "🎭", "🌙", "⭐", "🪄"],
        "scifi": ["🚀", "🤖", "👾", "🛸", "🌌", "⚡", "🔬", "💎"],
        "cyberpunk": ["🤖", "💀", "⚡", "🔥", "💻", "🎮", "🌃", "🔫"],
        "anime": ["⚔️", "🌸", "🎌", "👤", "💥", "🔥", "⭐", "🗡️"],
    }
    emojis = genre_emojis.get(genre, genre_emojis["fantasy"])

    custom_name_en = data.get("name_en")
    custom_description_en = data.get("description_en")

    if custom_name:
        # Create with custom name
        template_name = custom_name
        template_name_en = custom_name_en
        template_description = custom_description or f"Character from {genre} genre"
        template_description_en = custom_description_en
        ai_generated = False
    else:
        # Generate simple name (no AI for now)
        prefixes = {
            "fantasy": ["Dark", "Ancient", "Shadow", "Crystal", "Storm"],
            "magic": ["Mystic", "Arcane", "Ethereal", "Celestial", "Void"],
            "scifi": ["Cyber", "Quantum", "Plasma", "Nova", "Zero"],
            "cyberpunk": ["Neon", "Chrome", "Digital", "Synth", "Ghost"],
            "anime": ["Thunder", "Blade", "Spirit", "Dragon", "Star"],
        }
        suffixes = {
            "fantasy": ["Knight", "Mage", "Dragon", "Guardian", "Warrior"],
            "magic": ["Sorcerer", "Enchanter", "Wizard", "Summoner", "Sage"],
            "scifi": ["Bot", "Droid", "Unit", "Agent", "Core"],
            "cyberpunk": ["Runner", "Hacker", "Phantom", "Striker", "Rogue"],
            "anime": ["Slayer", "Master", "Hero", "Fighter", "Champion"],
        }
        prefix = random.choice(prefixes.get(genre, prefixes["fantasy"]))
        suffix = random.choice(suffixes.get(genre, suffixes["fantasy"]))
        template_name = f"{prefix} {suffix}"
        template_name_en = template_name  # Already in English
        template_description = f"A powerful {genre} character"
        template_description_en = template_description  # Already in English
        ai_generated = False

    # Insert template
    result = db.session.execute(
        text("""
            INSERT INTO card_templates (name, name_en, description, description_en, genre, base_hp, base_attack, emoji, ai_generated, is_active, created_at)
            VALUES (:name, :name_en, :description, :description_en, :genre, 50, 15, :emoji, :ai_generated, true, NOW())
            RETURNING id
        """),
        {
            "name": template_name,
            "name_en": template_name_en,
            "description": template_description,
            "description_en": template_description_en,
            "genre": genre,
            "emoji": random.choice(emojis),
            "ai_generated": ai_generated,
        },
    )
    template_id = result.fetchone()[0]
    db.session.commit()

    return jsonify({
        "success": True,
        "template": {
            "id": template_id,
            "name": template_name,
            "name_en": template_name_en,
            "description": template_description,
            "description_en": template_description_en,
            "genre": genre,
        },
    })


@app.route("/card-pool/template/<int:template_id>", methods=["GET"])
@login_required
def get_card_template(template_id: int):
    """Get a single template by ID."""
    template = db.session.execute(
        text("""
            SELECT id, name, name_en, description, description_en, genre, base_hp, base_attack,
                   image_url, emoji, ai_generated, is_active, created_at, rarity
            FROM card_templates
            WHERE id = :id
        """),
        {"id": template_id},
    ).fetchone()

    if not template:
        return jsonify({"success": False, "error": "Template not found"}), 404

    return jsonify({
        "success": True,
        "template": {
            "id": template[0],
            "name": template[1],
            "name_en": template[2],
            "description": template[3],
            "description_en": template[4],
            "genre": template[5],
            "base_hp": template[6],
            "base_attack": template[7],
            "image_url": template[8],
            "emoji": template[9],
            "ai_generated": template[10],
            "is_active": template[11],
            "created_at": template[12].isoformat() if template[12] else None,
            "rarity": template[13],
        },
    })


@app.route("/card-pool/template/<int:template_id>", methods=["PUT"])
@login_required
def update_card_template(template_id: int):
    """Update a card template."""
    template = db.session.execute(
        text("SELECT id FROM card_templates WHERE id = :id"),
        {"id": template_id},
    ).fetchone()

    if not template:
        return jsonify({"success": False, "error": "Template not found"}), 404

    data = request.json or {}

    # Build update query dynamically based on provided fields
    update_fields = []
    params = {"id": template_id}

    if "name" in data and data["name"]:
        update_fields.append("name = :name")
        params["name"] = data["name"]

    if "name_en" in data:
        update_fields.append("name_en = :name_en")
        params["name_en"] = data["name_en"]

    if "description" in data:
        update_fields.append("description = :description")
        params["description"] = data["description"]

    if "description_en" in data:
        update_fields.append("description_en = :description_en")
        params["description_en"] = data["description_en"]

    if "base_hp" in data:
        update_fields.append("base_hp = :base_hp")
        params["base_hp"] = int(data["base_hp"])

    if "base_attack" in data:
        update_fields.append("base_attack = :base_attack")
        params["base_attack"] = int(data["base_attack"])

    if "emoji" in data and data["emoji"]:
        update_fields.append("emoji = :emoji")
        params["emoji"] = data["emoji"]

    if "is_active" in data:
        update_fields.append("is_active = :is_active")
        params["is_active"] = bool(data["is_active"])

    if "rarity" in data:
        # Allow NULL for universal templates, or valid rarity value
        rarity_value = data["rarity"]
        if rarity_value and rarity_value not in RARITIES:
            return jsonify({"success": False, "error": f"Invalid rarity. Must be one of: {RARITIES}"}), 400
        update_fields.append("rarity = :rarity")
        params["rarity"] = rarity_value if rarity_value else None

    if not update_fields:
        return jsonify({"success": False, "error": "No fields to update"}), 400

    query = f"UPDATE card_templates SET {', '.join(update_fields)} WHERE id = :id"
    db.session.execute(text(query), params)
    db.session.commit()

    # Fetch updated template
    updated = db.session.execute(
        text("""
            SELECT id, name, name_en, description, description_en, genre, base_hp, base_attack,
                   image_url, emoji, ai_generated, is_active, rarity
            FROM card_templates
            WHERE id = :id
        """),
        {"id": template_id},
    ).fetchone()

    return jsonify({
        "success": True,
        "template": {
            "id": updated[0],
            "name": updated[1],
            "name_en": updated[2],
            "description": updated[3],
            "description_en": updated[4],
            "genre": updated[5],
            "base_hp": updated[6],
            "base_attack": updated[7],
            "image_url": updated[8],
            "emoji": updated[9],
            "ai_generated": updated[10],
            "is_active": updated[11],
            "rarity": updated[12],
        },
    })


@app.route("/card-pool/template/<int:template_id>/set-image", methods=["POST"])
@login_required
def set_template_image_from_gallery(template_id: int):
    """Set template image from gallery or media URL."""
    data = request.json or {}
    image_url = data.get("image_url")

    if not image_url:
        return jsonify({"success": False, "error": "No image_url provided"}), 400

    # Validate the URL is from our media storage or legacy gallery
    if not (image_url.startswith("/media/") or image_url.startswith("/static/gallery/")):
        return jsonify({"success": False, "error": "Invalid image URL. Must be from /media/ or /static/gallery/"}), 400

    # Update the template
    db.session.execute(
        text("UPDATE card_templates SET image_url = :url WHERE id = :id"),
        {"url": image_url, "id": template_id},
    )
    db.session.commit()

    return jsonify({"success": True, "image_url": image_url})


@app.route("/card-pool/template/<int:template_id>", methods=["DELETE"])
@login_required
def delete_card_template(template_id: int):
    """Delete a card template (if not used by any user cards)."""
    # Check if template is used
    used_count = db.session.execute(
        text("SELECT COUNT(*) FROM user_cards WHERE template_id = :id"),
        {"id": template_id},
    ).scalar() or 0

    if used_count > 0:
        return jsonify({
            "success": False,
            "error": f"Template is used by {used_count} user cards. Deactivate instead of deleting.",
        }), 400

    db.session.execute(
        text("DELETE FROM card_templates WHERE id = :id"),
        {"id": template_id},
    )
    db.session.commit()

    return jsonify({"success": True})


@app.route("/card-pool/export-template", methods=["GET"])
@login_required
def export_card_template_format():
    """Export JSON template format for bulk import."""
    template = {
        "templates": [
            {
                "name": "Название персонажа",
                "name_en": "Character Name",
                "description": "Описание персонажа (опционально)",
                "description_en": "Character description (optional)",
                "genre": "fantasy",  # fantasy, magic, scifi, cyberpunk, anime
                "base_hp": 50,
                "base_attack": 15,
                "emoji": "⚔️",
                "rarity": None,  # null = универсальный, или: common, uncommon, rare, epic, legendary
                "image_url": None,  # опционально, путь к изображению
                "is_active": True
            },
            {
                "name": "Легендарный Герой",
                "name_en": "Legendary Hero",
                "description": "Уникальный легендарный персонаж",
                "description_en": "Unique legendary character",
                "genre": "fantasy",
                "base_hp": 80,
                "base_attack": 25,
                "emoji": "👑",
                "rarity": "legendary",
                "image_url": None,
                "is_active": True
            }
        ]
    }
    return jsonify(template)


@app.route("/card-pool/bulk-import", methods=["POST"])
@login_required
def bulk_import_card_templates():
    """Bulk import card templates from JSON."""
    data = request.json

    if not data or "templates" not in data:
        return jsonify({"success": False, "error": "Missing 'templates' array"}), 400

    templates = data["templates"]
    if not isinstance(templates, list):
        return jsonify({"success": False, "error": "'templates' must be an array"}), 400

    valid_genres = ["fantasy", "magic", "scifi", "cyberpunk", "anime"]
    valid_rarities = [None, "common", "uncommon", "rare", "epic", "legendary"]

    imported = []
    errors = []

    for i, t in enumerate(templates):
        try:
            name = t.get("name")
            if not name:
                errors.append(f"Template {i+1}: missing 'name'")
                continue

            genre = t.get("genre", "fantasy")
            if genre not in valid_genres:
                errors.append(f"Template {i+1}: invalid genre '{genre}'")
                continue

            rarity = t.get("rarity")
            if rarity not in valid_rarities:
                errors.append(f"Template {i+1}: invalid rarity '{rarity}'")
                continue

            result = db.session.execute(
                text("""
                    INSERT INTO card_templates
                    (name, name_en, description, description_en, genre, base_hp, base_attack, emoji, rarity, image_url, is_active, ai_generated, created_at)
                    VALUES (:name, :name_en, :description, :description_en, :genre, :base_hp, :base_attack, :emoji, :rarity, :image_url, :is_active, false, NOW())
                    RETURNING id
                """),
                {
                    "name": name,
                    "name_en": t.get("name_en"),
                    "description": t.get("description"),
                    "description_en": t.get("description_en"),
                    "genre": genre,
                    "base_hp": t.get("base_hp", 50),
                    "base_attack": t.get("base_attack", 15),
                    "emoji": t.get("emoji", "🎴"),
                    "rarity": rarity,
                    "image_url": t.get("image_url"),
                    "is_active": t.get("is_active", True),
                },
            )
            template_id = result.fetchone()[0]
            imported.append({"id": template_id, "name": name, "name_en": t.get("name_en"), "genre": genre})
        except Exception as e:
            errors.append(f"Template {i+1} ({t.get('name', 'unknown')}): {str(e)}")

    db.session.commit()

    return jsonify({
        "success": True,
        "imported_count": len(imported),
        "imported": imported,
        "errors": errors,
    })


@app.route("/card-pool/legendary", methods=["GET"])
@login_required
def get_legendary_templates():
    """Get all legendary templates grouped by genre."""
    templates = db.session.execute(
        text("""
            SELECT id, name, name_en, description, description_en, genre, base_hp, base_attack,
                   image_url, emoji, is_active, created_at
            FROM card_templates
            WHERE rarity = 'legendary'
            ORDER BY genre, name
        """)
    ).fetchall()

    # Group by genre
    by_genre = {}
    for t in templates:
        genre = t[5]
        if genre not in by_genre:
            by_genre[genre] = []
        by_genre[genre].append({
            "id": t[0],
            "name": t[1],
            "name_en": t[2],
            "description": t[3],
            "description_en": t[4],
            "genre": t[5],
            "base_hp": t[6],
            "base_attack": t[7],
            "image_url": t[8],
            "emoji": t[9],
            "is_active": t[10],
            "created_at": t[11].isoformat() if t[11] else None,
        })

    return jsonify({
        "success": True,
        "legendary_by_genre": by_genre,
        "total_count": len(templates),
    })


# ============ Gallery ============

GALLERY_DIR = "/app/static/gallery"
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def get_gallery_images():
    """Get all images from gallery directory."""
    import glob

    images = []
    if os.path.exists(GALLERY_DIR):
        for ext in ALLOWED_IMAGE_EXTENSIONS:
            for filepath in glob.glob(os.path.join(GALLERY_DIR, f"*.{ext}")):
                filename = os.path.basename(filepath)
                stat = os.stat(filepath)
                images.append({
                    "filename": filename,
                    "url": f"/static/gallery/{filename}",
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime),
                })
    # Sort by creation time, newest first
    images.sort(key=lambda x: x["created_at"], reverse=True)
    return images


@app.route("/gallery")
@login_required
def gallery():
    """Gallery page with all uploaded images."""
    images = get_gallery_images()
    return render_template("gallery.html", images=images)


@app.route("/gallery/images")
@login_required
def gallery_images_api():
    """API to get all gallery images."""
    images = get_gallery_images()
    return jsonify({
        "success": True,
        "images": [
            {
                "filename": img["filename"],
                "url": img["url"],
                "size": img["size"],
                "created_at": img["created_at"].isoformat(),
            }
            for img in images
        ],
    })


@app.route("/gallery/upload", methods=["POST"])
@login_required
def upload_gallery_images():
    """Upload multiple images to gallery."""
    import uuid

    if "images" not in request.files:
        return jsonify({"success": False, "error": "No images provided"}), 400

    files = request.files.getlist("images")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"success": False, "error": "No files selected"}), 400

    # Ensure gallery directory exists
    os.makedirs(GALLERY_DIR, exist_ok=True)

    uploaded = []
    errors = []

    for file in files:
        if file.filename == "":
            continue

        # Check extension
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            errors.append(f"{file.filename}: invalid type (allowed: {ALLOWED_IMAGE_EXTENSIONS})")
            continue

        try:
            # Generate unique filename preserving original name base
            original_name = file.filename.rsplit(".", 1)[0]
            # Sanitize filename
            safe_name = "".join(c for c in original_name if c.isalnum() or c in "-_").strip()
            if not safe_name:
                safe_name = "image"
            filename = f"{safe_name}_{uuid.uuid4().hex[:6]}.{ext}"
            filepath = os.path.join(GALLERY_DIR, filename)

            file.save(filepath)
            uploaded.append({
                "filename": filename,
                "url": f"/static/gallery/{filename}",
                "original_name": file.filename,
            })
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")

    return jsonify({
        "success": True,
        "uploaded": uploaded,
        "uploaded_count": len(uploaded),
        "errors": errors,
    })


@app.route("/gallery/delete/<filename>", methods=["POST"])
@login_required
def delete_gallery_image(filename: str):
    """Delete an image from gallery."""
    # Security: prevent path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        return jsonify({"success": False, "error": "Invalid filename"}), 400

    filepath = os.path.join(GALLERY_DIR, filename)

    if not os.path.exists(filepath):
        return jsonify({"success": False, "error": "File not found"}), 404

    try:
        os.remove(filepath)
        return jsonify({"success": True, "message": f"Deleted {filename}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/gallery/delete-multiple", methods=["POST"])
@login_required
def delete_multiple_gallery_images():
    """Delete multiple images from gallery."""
    data = request.json or {}
    filenames = data.get("filenames", [])

    if not filenames:
        return jsonify({"success": False, "error": "No filenames provided"}), 400

    deleted = []
    errors = []

    for filename in filenames:
        # Security: prevent path traversal
        if "/" in filename or "\\" in filename or ".." in filename:
            errors.append(f"{filename}: invalid filename")
            continue

        filepath = os.path.join(GALLERY_DIR, filename)

        if not os.path.exists(filepath):
            errors.append(f"{filename}: not found")
            continue

        try:
            os.remove(filepath)
            deleted.append(filename)
        except Exception as e:
            errors.append(f"{filename}: {str(e)}")

    return jsonify({
        "success": True,
        "deleted": deleted,
        "deleted_count": len(deleted),
        "errors": errors,
    })


# ============ Media Browser (Unified Storage) ============

MEDIA_DIR = "/app/media"


def get_media_tree(base_path: str = "") -> dict:
    """Get folder tree structure from media directory."""
    import os

    full_path = os.path.join(MEDIA_DIR, base_path) if base_path else MEDIA_DIR

    if not os.path.exists(full_path):
        os.makedirs(full_path, exist_ok=True)

    items = []

    try:
        for entry in os.scandir(full_path):
            if entry.name.startswith('.'):
                continue

            item = {
                "name": entry.name,
                "path": os.path.join(base_path, entry.name) if base_path else entry.name,
                "is_dir": entry.is_dir(),
            }

            if entry.is_file():
                stat = entry.stat()
                item["size"] = stat.st_size
                item["modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                ext = entry.name.rsplit(".", 1)[-1].lower() if "." in entry.name else ""
                item["is_image"] = ext in {"png", "jpg", "jpeg", "gif", "webp"}
                if item["is_image"]:
                    item["url"] = f"/media/{item['path']}"
            else:
                # Count items in folder
                try:
                    item["items_count"] = len([f for f in os.listdir(entry.path) if not f.startswith('.')])
                except Exception:
                    item["items_count"] = 0

            items.append(item)
    except Exception as e:
        return {"error": str(e), "items": []}

    # Sort: folders first, then files by name
    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

    return {
        "current_path": base_path,
        "items": items,
    }


@app.route("/media")
@login_required
def media_browser():
    """Media browser page with folder support."""
    path = request.args.get("path", "")
    # Security: prevent path traversal
    if ".." in path:
        path = ""

    data = get_media_tree(path)

    # Build breadcrumbs
    breadcrumbs = [{"name": "Media", "path": ""}]
    if path:
        parts = path.split("/")
        current = ""
        for part in parts:
            current = f"{current}/{part}" if current else part
            breadcrumbs.append({"name": part, "path": current})

    return render_template(
        "media.html",
        current_path=path,
        breadcrumbs=breadcrumbs,
        items=data.get("items", []),
        error=data.get("error"),
    )


@app.route("/media/api/list")
@login_required
def media_list_api():
    """API to list media files and folders."""
    path = request.args.get("path", "")
    if ".." in path:
        return jsonify({"success": False, "error": "Invalid path"}), 400

    data = get_media_tree(path)
    return jsonify({"success": True, **data})


@app.route("/media/api/create-folder", methods=["POST"])
@login_required
def media_create_folder():
    """Create a new folder in media storage."""
    data = request.json or {}
    parent_path = data.get("parent_path", "")
    folder_name = data.get("name", "").strip()

    if not folder_name:
        return jsonify({"success": False, "error": "Folder name is required"}), 400

    # Security checks
    if ".." in parent_path or ".." in folder_name:
        return jsonify({"success": False, "error": "Invalid path"}), 400

    if "/" in folder_name or "\\" in folder_name:
        return jsonify({"success": False, "error": "Folder name cannot contain slashes"}), 400

    # Sanitize folder name
    safe_name = "".join(c for c in folder_name if c.isalnum() or c in "-_ ").strip()
    if not safe_name:
        return jsonify({"success": False, "error": "Invalid folder name"}), 400

    full_path = os.path.join(MEDIA_DIR, parent_path, safe_name) if parent_path else os.path.join(MEDIA_DIR, safe_name)

    if os.path.exists(full_path):
        return jsonify({"success": False, "error": "Folder already exists"}), 400

    try:
        os.makedirs(full_path, exist_ok=True)
        new_path = os.path.join(parent_path, safe_name) if parent_path else safe_name
        return jsonify({
            "success": True,
            "folder": {
                "name": safe_name,
                "path": new_path,
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/media/api/upload", methods=["POST"])
@login_required
def media_upload():
    """Upload files to media storage."""
    import uuid

    target_path = request.form.get("path", "")

    # Security check
    if ".." in target_path:
        return jsonify({"success": False, "error": "Invalid path"}), 400

    if "files" not in request.files:
        return jsonify({"success": False, "error": "No files provided"}), 400

    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"success": False, "error": "No files selected"}), 400

    # Ensure target directory exists
    full_target = os.path.join(MEDIA_DIR, target_path) if target_path else MEDIA_DIR
    os.makedirs(full_target, exist_ok=True)

    uploaded = []
    errors = []

    allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp", "svg", "mp4", "webm", "pdf"}

    for file in files:
        if file.filename == "":
            continue

        # Check extension
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in allowed_extensions:
            errors.append(f"{file.filename}: invalid type")
            continue

        try:
            # Sanitize and create unique filename
            original_name = file.filename.rsplit(".", 1)[0]
            safe_name = "".join(c for c in original_name if c.isalnum() or c in "-_").strip()
            if not safe_name:
                safe_name = "file"

            filename = f"{safe_name}_{uuid.uuid4().hex[:6]}.{ext}"
            filepath = os.path.join(full_target, filename)

            file.save(filepath)

            file_path = os.path.join(target_path, filename) if target_path else filename
            is_image = ext in {"png", "jpg", "jpeg", "gif", "webp"}

            uploaded.append({
                "filename": filename,
                "path": file_path,
                "url": f"/media/{file_path}" if is_image else None,
                "is_image": is_image,
            })
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")

    return jsonify({
        "success": True,
        "uploaded": uploaded,
        "uploaded_count": len(uploaded),
        "errors": errors,
    })


@app.route("/media/api/delete", methods=["POST"])
@login_required
def media_delete():
    """Delete a file or folder from media storage."""
    import shutil

    data = request.json or {}
    path = data.get("path", "")

    if not path:
        return jsonify({"success": False, "error": "Path is required"}), 400

    # Security check
    if ".." in path:
        return jsonify({"success": False, "error": "Invalid path"}), 400

    full_path = os.path.join(MEDIA_DIR, path)

    if not os.path.exists(full_path):
        return jsonify({"success": False, "error": "Path not found"}), 404

    try:
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)

        return jsonify({"success": True, "message": f"Deleted: {path}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/media/api/delete-multiple", methods=["POST"])
@login_required
def media_delete_multiple():
    """Delete multiple files/folders from media storage."""
    import shutil

    data = request.json or {}
    paths = data.get("paths", [])

    if not paths:
        return jsonify({"success": False, "error": "No paths provided"}), 400

    deleted = []
    errors = []

    for path in paths:
        # Security check
        if ".." in path:
            errors.append(f"{path}: invalid path")
            continue

        full_path = os.path.join(MEDIA_DIR, path)

        if not os.path.exists(full_path):
            errors.append(f"{path}: not found")
            continue

        try:
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
            else:
                os.remove(full_path)
            deleted.append(path)
        except Exception as e:
            errors.append(f"{path}: {str(e)}")

    return jsonify({
        "success": True,
        "deleted": deleted,
        "deleted_count": len(deleted),
        "errors": errors,
    })


@app.route("/media/api/rename", methods=["POST"])
@login_required
def media_rename():
    """Rename a file or folder."""
    data = request.json or {}
    old_path = data.get("path", "")
    new_name = data.get("new_name", "").strip()

    if not old_path or not new_name:
        return jsonify({"success": False, "error": "Path and new_name are required"}), 400

    # Security checks
    if ".." in old_path or ".." in new_name or "/" in new_name or "\\" in new_name:
        return jsonify({"success": False, "error": "Invalid path or name"}), 400

    full_old_path = os.path.join(MEDIA_DIR, old_path)

    if not os.path.exists(full_old_path):
        return jsonify({"success": False, "error": "Path not found"}), 404

    # Get parent directory and construct new path
    parent_dir = os.path.dirname(full_old_path)

    # Preserve extension for files
    if os.path.isfile(full_old_path):
        old_ext = old_path.rsplit(".", 1)[-1] if "." in old_path else ""
        if old_ext and not new_name.endswith(f".{old_ext}"):
            new_name = f"{new_name}.{old_ext}"

    full_new_path = os.path.join(parent_dir, new_name)

    if os.path.exists(full_new_path):
        return jsonify({"success": False, "error": "A file/folder with this name already exists"}), 400

    try:
        os.rename(full_old_path, full_new_path)

        # Calculate new relative path
        old_parent = os.path.dirname(old_path)
        new_path = os.path.join(old_parent, new_name) if old_parent else new_name

        return jsonify({
            "success": True,
            "old_path": old_path,
            "new_path": new_path,
            "new_name": new_name,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============ Level Rewards ============


@app.route("/levels")
@login_required
def levels():
    """Level rewards management page."""
    rewards_rows = db.session.execute(
        text("SELECT * FROM level_rewards ORDER BY level, id")
    ).fetchall()

    # Group rewards by level
    levels_data = {}
    for row in rewards_rows:
        r = dict(row._mapping)
        lvl = r["level"]
        if lvl not in levels_data:
            levels_data[lvl] = []
        levels_data[lvl].append(r)

    total_rewards = len(rewards_rows)
    levels_with_rewards = len(levels_data)

    max_player_level = db.session.execute(
        text("""
            SELECT COALESCE(MAX(
                CAST(FLOOR(SQRT(xp / 100.0)) + 1 AS INTEGER)
            ), 1) FROM user_profiles WHERE xp > 0
        """)
    ).scalar() or 1

    return render_template(
        "levels.html",
        levels_data=levels_data,
        total_rewards=total_rewards,
        levels_with_rewards=levels_with_rewards,
        max_player_level=max_player_level,
    )


@app.route("/levels/reward", methods=["POST"])
@login_required
def levels_reward_create():
    """Create a new level reward."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data"}), 400

    try:
        import json as json_mod

        reward_value = data.get("reward_value", {})
        if isinstance(reward_value, str):
            reward_value = json_mod.loads(reward_value)

        db.session.execute(
            text("""
                INSERT INTO level_rewards (level, reward_type, reward_value, description, is_active, created_at)
                VALUES (:level, :reward_type, :reward_value, :description, :is_active, NOW())
            """),
            {
                "level": data["level"],
                "reward_type": data["reward_type"],
                "reward_value": json_mod.dumps(reward_value),
                "description": data.get("description"),
                "is_active": data.get("is_active", True),
            },
        )
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/levels/reward/<int:reward_id>", methods=["GET"])
@login_required
def levels_reward_get(reward_id):
    """Get a single level reward."""
    row = db.session.execute(
        text("SELECT * FROM level_rewards WHERE id = :id"),
        {"id": reward_id},
    ).fetchone()

    if not row:
        return jsonify({"success": False, "error": "Not found"}), 404

    r = dict(row._mapping)
    # Ensure reward_value is parsed
    if isinstance(r.get("reward_value"), str):
        import json as json_mod
        r["reward_value"] = json_mod.loads(r["reward_value"])

    return jsonify({"success": True, "reward": r})


@app.route("/levels/reward/<int:reward_id>", methods=["POST"])
@login_required
def levels_reward_update(reward_id):
    """Update a level reward."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data"}), 400

    try:
        import json as json_mod

        reward_value = data.get("reward_value", {})
        if isinstance(reward_value, str):
            reward_value = json_mod.loads(reward_value)

        db.session.execute(
            text("""
                UPDATE level_rewards
                SET level = :level,
                    reward_type = :reward_type,
                    reward_value = :reward_value,
                    description = :description,
                    is_active = :is_active
                WHERE id = :id
            """),
            {
                "id": reward_id,
                "level": data["level"],
                "reward_type": data["reward_type"],
                "reward_value": json_mod.dumps(reward_value),
                "description": data.get("description"),
                "is_active": data.get("is_active", True),
            },
        )
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/levels/reward/<int:reward_id>/delete", methods=["POST"])
@login_required
def levels_reward_delete(reward_id):
    """Delete a level reward."""
    try:
        db.session.execute(
            text("DELETE FROM level_rewards WHERE id = :id"),
            {"id": reward_id},
        )
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# ============ Broadcast ============

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")


@app.route("/broadcast")
@login_required
def broadcast():
    """Broadcast message form."""
    # Get user counts for filter preview
    with db.engine.connect() as conn:
        total_users = conn.execute(
            text("SELECT COUNT(*) FROM users WHERE telegram_id IS NOT NULL")
        ).scalar()
        lang_counts = conn.execute(
            text("""
                SELECT COALESCE(up.language, 'ru') as lang, COUNT(*) as cnt
                FROM users u
                LEFT JOIN user_profiles up ON up.user_id = u.id
                WHERE u.telegram_id IS NOT NULL
                GROUP BY COALESCE(up.language, 'ru')
            """)
        ).fetchall()
        lang_stats = {row[0]: row[1] for row in lang_counts}

    return render_template(
        "broadcast.html",
        total_users=total_users,
        lang_stats=lang_stats,
    )


@app.route("/broadcast/send", methods=["POST"])
@login_required
def broadcast_send():
    """Send broadcast message to filtered users."""
    import requests as http_requests

    message_text = request.form.get("message", "").strip()
    filter_type = request.form.get("filter_type", "all")
    filter_language = request.form.get("filter_language", "")
    filter_level_min = request.form.get("filter_level_min", "")
    filter_level_max = request.form.get("filter_level_max", "")
    filter_active_days = request.form.get("filter_active_days", "")

    if not message_text:
        return jsonify({"success": False, "error": "Message is empty"}), 400

    if not BOT_TOKEN:
        return jsonify({"success": False, "error": "BOT_TOKEN not configured"}), 500

    # Build query based on filter
    base_query = """
        SELECT DISTINCT u.telegram_id
        FROM users u
        LEFT JOIN user_profiles up ON up.user_id = u.id
        WHERE u.telegram_id IS NOT NULL
    """
    params = {}

    if filter_type == "language" and filter_language:
        base_query += " AND COALESCE(up.language, 'ru') = :lang"
        params["lang"] = filter_language

    elif filter_type == "level":
        if filter_level_min:
            base_query += " AND u.level >= :level_min"
            params["level_min"] = int(filter_level_min)
        if filter_level_max:
            base_query += " AND u.level <= :level_max"
            params["level_max"] = int(filter_level_max)

    elif filter_type == "activity" and filter_active_days:
        days = int(filter_active_days)
        base_query += " AND u.last_activity_at >= NOW() - INTERVAL ':days days'".replace(
            ":days", str(days)
        )

    # Fetch user telegram IDs
    with db.engine.connect() as conn:
        result = conn.execute(text(base_query), params)
        telegram_ids = [row[0] for row in result.fetchall()]

    if not telegram_ids:
        return jsonify({"success": False, "error": "No users match the filter"}), 400

    # Send messages via Telegram Bot API
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    success_count = 0
    fail_count = 0

    for tid in telegram_ids:
        try:
            resp = http_requests.post(
                api_url,
                json={
                    "chat_id": tid,
                    "text": message_text,
                    "parse_mode": "HTML",
                },
                timeout=10,
            )
            if resp.status_code == 200 and resp.json().get("ok"):
                success_count += 1
            else:
                fail_count += 1
        except Exception:
            fail_count += 1

    return jsonify({
        "success": True,
        "total": len(telegram_ids),
        "sent": success_count,
        "failed": fail_count,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
