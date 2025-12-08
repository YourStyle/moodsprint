"""Admin panel application."""
import os
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'admin-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'postgresql://moodsprint:moodsprint@db:5432/moodsprint'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Admin credentials (in production, use proper auth)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'moodsprint')


def login_required(f):
    """Login required decorator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))

        return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Admin logout."""
    session.pop('logged_in', None)
    return redirect(url_for('login'))


@app.route('/')
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
        text("SELECT COALESCE(SUM(actual_duration_minutes), 0) FROM focus_sessions WHERE status = 'completed'")
    ).scalar()

    total_mood_checks = db.session.execute(text("SELECT COUNT(*) FROM mood_checks")).scalar()

    # Get daily active users for last 7 days
    daily_active = db.session.execute(text("""
        SELECT
            last_activity_date as date,
            COUNT(*) as users
        FROM users
        WHERE last_activity_date >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY last_activity_date
        ORDER BY last_activity_date
    """)).fetchall()

    # Get new users per day
    new_users = db.session.execute(text("""
        SELECT
            DATE(created_at) as date,
            COUNT(*) as users
        FROM users
        WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY DATE(created_at)
        ORDER BY date
    """)).fetchall()

    return render_template(
        'dashboard.html',
        total_users=total_users,
        active_today=active_today or 0,
        total_tasks=total_tasks or 0,
        completed_tasks=completed_tasks or 0,
        total_focus_minutes=total_focus_minutes or 0,
        total_mood_checks=total_mood_checks or 0,
        daily_active=[{'date': str(r[0]), 'users': r[1]} for r in daily_active],
        new_users=[{'date': str(r[0]), 'users': r[1]} for r in new_users]
    )


@app.route('/users')
@login_required
def users():
    """User list."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    search = request.args.get('search', '')

    if search:
        query = text("""
            SELECT * FROM users
            WHERE username ILIKE :search OR first_name ILIKE :search
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        users_data = db.session.execute(
            query,
            {'search': f'%{search}%', 'limit': per_page, 'offset': offset}
        ).fetchall()

        total = db.session.execute(
            text("SELECT COUNT(*) FROM users WHERE username ILIKE :search OR first_name ILIKE :search"),
            {'search': f'%{search}%'}
        ).scalar()
    else:
        users_data = db.session.execute(
            text("SELECT * FROM users ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
            {'limit': per_page, 'offset': offset}
        ).fetchall()
        total = db.session.execute(text("SELECT COUNT(*) FROM users")).scalar()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'users.html',
        users=[dict(row._mapping) for row in users_data],
        page=page,
        total_pages=total_pages,
        search=search
    )


@app.route('/users/<int:user_id>')
@login_required
def user_detail(user_id: int):
    """User detail view."""
    user = db.session.execute(
        text("SELECT * FROM users WHERE id = :id"),
        {'id': user_id}
    ).fetchone()

    if not user:
        return "User not found", 404

    # Get user's tasks
    tasks = db.session.execute(
        text("SELECT * FROM tasks WHERE user_id = :uid ORDER BY created_at DESC LIMIT 10"),
        {'uid': user_id}
    ).fetchall()

    # Get user's activity log
    activity = db.session.execute(
        text("""
            SELECT * FROM user_activity_logs
            WHERE user_id = :uid
            ORDER BY created_at DESC
            LIMIT 50
        """),
        {'uid': user_id}
    ).fetchall()

    # Get focus sessions
    sessions = db.session.execute(
        text("""
            SELECT * FROM focus_sessions
            WHERE user_id = :uid
            ORDER BY started_at DESC
            LIMIT 10
        """),
        {'uid': user_id}
    ).fetchall()

    return render_template(
        'user_detail.html',
        user=dict(user._mapping),
        tasks=[dict(row._mapping) for row in tasks],
        activity=[dict(row._mapping) for row in activity] if activity else [],
        sessions=[dict(row._mapping) for row in sessions]
    )


@app.route('/activity')
@login_required
def activity_log():
    """Global activity log."""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page

    logs = db.session.execute(
        text("""
            SELECT l.*, u.username, u.first_name
            FROM user_activity_logs l
            JOIN users u ON l.user_id = u.id
            ORDER BY l.created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {'limit': per_page, 'offset': offset}
    ).fetchall()

    total = db.session.execute(text("SELECT COUNT(*) FROM user_activity_logs")).scalar() or 0
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'activity.html',
        logs=[dict(row._mapping) for row in logs],
        page=page,
        total_pages=total_pages
    )


@app.route('/metrics')
@login_required
def metrics():
    """Product metrics page."""
    # Retention metrics
    day1_retention = db.session.execute(text("""
        SELECT
            COUNT(DISTINCT CASE WHEN last_activity_date > DATE(created_at) THEN id END)::float /
            NULLIF(COUNT(DISTINCT id), 0) * 100 as retention
        FROM users
        WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
    """)).scalar() or 0

    # Average session duration
    avg_session = db.session.execute(text("""
        SELECT AVG(actual_duration_minutes)
        FROM focus_sessions
        WHERE status = 'completed' AND actual_duration_minutes IS NOT NULL
    """)).scalar() or 0

    # Task completion rate
    completion_rate = db.session.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'completed')::float /
            NULLIF(COUNT(*), 0) * 100
        FROM tasks
    """)).scalar() or 0

    # Average XP per user
    avg_xp = db.session.execute(text("SELECT AVG(xp) FROM users")).scalar() or 0

    # Average streak
    avg_streak = db.session.execute(text("SELECT AVG(streak_days) FROM users")).scalar() or 0

    # Mood distribution
    mood_dist = db.session.execute(text("""
        SELECT mood, COUNT(*) as count
        FROM mood_checks
        GROUP BY mood
        ORDER BY mood
    """)).fetchall()

    # Energy distribution
    energy_dist = db.session.execute(text("""
        SELECT energy, COUNT(*) as count
        FROM mood_checks
        GROUP BY energy
        ORDER BY energy
    """)).fetchall()

    # Daily metrics for last 30 days
    daily_metrics = db.session.execute(text("""
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
    """)).fetchall()

    return render_template(
        'metrics.html',
        day1_retention=round(day1_retention, 1),
        avg_session=round(avg_session, 1),
        completion_rate=round(completion_rate, 1),
        avg_xp=round(avg_xp, 0),
        avg_streak=round(avg_streak, 1),
        mood_distribution=[{'mood': r[0], 'count': r[1]} for r in mood_dist],
        energy_distribution=[{'energy': r[0], 'count': r[1]} for r in energy_dist],
        daily_metrics=[{
            'date': str(r[0]),
            'new_users': r[1],
            'active_users': r[2],
            'tasks_completed': r[3],
            'focus_minutes': r[4]
        } for r in daily_metrics]
    )


@app.route('/api/metrics/realtime')
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

    return jsonify({
        'active_sessions': active_sessions or 0,
        'today_mood_checks': today_mood_checks or 0,
        'today_tasks_completed': today_tasks_completed or 0
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
