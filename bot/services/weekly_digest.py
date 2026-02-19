"""Weekly digest image generator using matplotlib.

Generates a PNG image with:
- Radar/spider chart (5 axes: Productivity, Focus, Mood, Cards, Social)
- Key stats with week-over-week comparison arrows
- Mood sparkline (daily averages)
- User level/XP/streak info

Uses only Unicode symbols (no emoji) to avoid font rendering issues.
"""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend for server

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

# Color palette (dark game theme)
BG_COLOR = "#0f1923"
ACCENT = "#4fc3f7"
ACCENT3 = "#ffb74d"
TEXT_PRIMARY = "#e0e0e0"
TEXT_SECONDARY = "#90a4ae"
GRID_COLOR = "#263238"
UP_COLOR = "#66bb6a"
DOWN_COLOR = "#ef5350"
NEUTRAL_COLOR = "#78909c"

# Stat card accent colors
STAT_COLORS = ["#66bb6a", "#42a5f5", "#ab47bc", "#ffb74d"]


def _normalize_radar_values(stats: dict) -> dict:
    """Normalize all stats to 0-100 scale for radar chart."""
    tasks_total = max(stats["tasks_total"], 1)
    productivity = min(stats["tasks_completed"] / tasks_total * 100, 100)

    # Focus: 300 min/week (5 hours) = 100%
    focus = min(stats["focus_minutes"] / 300 * 100, 100)

    # Mood: scale 1-5, normalize to 0-100
    mood = (stats["avg_mood"] / 5 * 100) if stats["avg_mood"] > 0 else 0

    # Cards: 10 cards/week = 100%
    cards = min(stats["cards_earned"] / 10 * 100, 100)

    # Social: 5 actions/week = 100%
    social = min(stats["social_actions"] / 5 * 100, 100)

    return {
        "productivity": productivity,
        "focus": focus,
        "mood": mood,
        "cards": cards,
        "social": social,
    }


def _comparison_arrow(current: int | float, previous: int | float) -> tuple[str, str]:
    """Return (arrow symbol, color) for week-over-week comparison."""
    if previous == 0 and current == 0:
        return "=", NEUTRAL_COLOR
    if previous == 0:
        return "+", UP_COLOR
    diff_pct = ((current - previous) / previous) * 100
    if diff_pct > 5:
        return "+", UP_COLOR
    elif diff_pct < -5:
        return "-", DOWN_COLOR
    return "=", NEUTRAL_COLOR


def _comparison_text(
    current: int | float, previous: int | float, lang: str
) -> tuple[str, str]:
    """Return (comparison text, color) for week-over-week."""
    if previous == 0 and current == 0:
        return ("без изменений" if lang == "ru" else "no change"), NEUTRAL_COLOR
    if previous == 0 and current > 0:
        return ("новый рекорд!" if lang == "ru" else "new record!"), UP_COLOR
    diff = current - previous
    if abs(diff) < 0.01:
        return ("без изменений" if lang == "ru" else "no change"), NEUTRAL_COLOR
    if diff > 0:
        return f"+{int(diff)} vs {('пред.' if lang == 'ru' else 'prev')}", UP_COLOR
    return f"{int(diff)} vs {('пред.' if lang == 'ru' else 'prev')}", DOWN_COLOR


def generate_weekly_digest_image(stats: dict, lang: str = "ru") -> io.BytesIO:
    """Generate weekly digest PNG image.

    Args:
        stats: Dict from get_weekly_digest_stats()
        lang: User language for labels

    Returns:
        BytesIO with PNG image data
    """
    user = stats["user"]
    normalized = _normalize_radar_values(stats)

    # Labels for radar axes
    if lang == "ru":
        labels = ["Продуктивность", "Фокус", "Настроение", "Карты", "Социальное"]
        title = "НЕДЕЛЬНЫЙ ОТЧЁТ"
        streak_label = "Серия"
        days_label = "дн."
        tasks_label = "Задачи"
        focus_label = "Фокус"
        cards_label = "Карты"
        mood_label = "Настроение"
        min_label = "мин"
        mood_title = "Настроение за неделю"
        no_mood_text = "Отмечай настроение, чтобы видеть график"
        footer_text = "MoodSprint"
    else:
        labels = ["Productivity", "Focus", "Mood", "Cards", "Social"]
        title = "WEEKLY REPORT"
        streak_label = "Streak"
        days_label = "d"
        tasks_label = "Tasks"
        focus_label = "Focus"
        cards_label = "Cards"
        mood_label = "Mood"
        min_label = "min"
        mood_title = "Mood This Week"
        no_mood_text = "Log your mood to see the chart"
        footer_text = "MoodSprint"

    # --- Create figure ---
    fig = plt.figure(figsize=(8, 10), facecolor=BG_COLOR, dpi=150)

    # --- Header ---
    name = user.get("first_name") or user.get("username") or "User"
    level = user.get("level", 1)
    xp = user.get("xp", 0)
    streak = user.get("streak_days", 0)

    # Title line
    fig.text(
        0.5,
        0.965,
        title,
        ha="center",
        va="top",
        fontsize=13,
        fontweight="bold",
        color=TEXT_SECONDARY,
        fontfamily="sans-serif",
    )

    # User name (prominent)
    fig.text(
        0.5,
        0.94,
        name,
        ha="center",
        va="top",
        fontsize=22,
        fontweight="bold",
        color=ACCENT,
        fontfamily="sans-serif",
    )

    # Level / XP / Streak bar
    info_parts = [
        f"Lv.{level}",
        f"{xp} XP",
        f"{streak_label}: {streak}{days_label}",
    ]
    info_text = "  ·  ".join(info_parts)
    fig.text(
        0.5,
        0.91,
        info_text,
        ha="center",
        va="top",
        fontsize=11,
        color=TEXT_SECONDARY,
        fontfamily="sans-serif",
    )

    # Thin separator line
    line_ax = fig.add_axes([0.15, 0.895, 0.7, 0.001])
    line_ax.axhline(y=0, color=GRID_COLOR, linewidth=1)
    line_ax.set_xlim(0, 1)
    line_ax.axis("off")

    # --- Radar Chart ---
    ax_radar = fig.add_axes([0.1, 0.40, 0.8, 0.45], polar=True, facecolor="none")

    values = [
        normalized["productivity"],
        normalized["focus"],
        normalized["mood"],
        normalized["cards"],
        normalized["social"],
    ]
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()

    # Close the polygon
    values_closed = values + [values[0]]
    angles_closed = angles + [angles[0]]

    # Draw radar
    ax_radar.set_theta_offset(np.pi / 2)
    ax_radar.set_theta_direction(-1)

    # Grid circles
    ax_radar.set_ylim(0, 110)
    ax_radar.set_yticks([25, 50, 75, 100])
    ax_radar.set_yticklabels(
        ["25", "50", "75", "100"],
        fontsize=7,
        color=TEXT_SECONDARY,
        alpha=0.4,
    )

    # Grid styling
    ax_radar.spines["polar"].set_color(GRID_COLOR)
    ax_radar.xaxis.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.5)
    ax_radar.yaxis.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.5)

    # Axis labels
    ax_radar.set_xticks(angles)
    ax_radar.set_xticklabels(
        labels,
        fontsize=10,
        color=TEXT_PRIMARY,
        fontweight="bold",
    )

    # Plot filled area with gradient-like effect
    ax_radar.fill(angles_closed, values_closed, color=ACCENT, alpha=0.12)
    ax_radar.plot(angles_closed, values_closed, color=ACCENT, linewidth=2.5, alpha=0.9)

    # Data points with glow effect
    ax_radar.scatter(
        angles,
        values,
        color=ACCENT,
        s=80,
        zorder=5,
        edgecolors="white",
        linewidths=1.2,
    )

    # Value labels near points
    for angle, value in zip(angles, values):
        offset_r = 14
        ax_radar.text(
            angle,
            value + offset_r,
            f"{int(value)}%",
            ha="center",
            va="center",
            fontsize=9,
            color=ACCENT,
            fontweight="bold",
        )

    # --- Stats Cards (bottom section) ---
    tasks_sub, tasks_sub_color = _comparison_text(
        stats["tasks_completed"], stats["prev_tasks_completed"], lang
    )
    focus_sub, focus_sub_color = _comparison_text(
        stats["focus_minutes"], stats["prev_focus_minutes"], lang
    )
    cards_sub, cards_sub_color = _comparison_text(
        stats["cards_earned"], stats["prev_cards_earned"], lang
    )

    card_data = [
        {
            "icon": "[ ]",  # checkbox
            "label": tasks_label,
            "value": str(stats["tasks_completed"]),
            "sub": tasks_sub,
            "sub_color": tasks_sub_color,
            "accent": STAT_COLORS[0],
        },
        {
            "icon": "( )",  # timer
            "label": focus_label,
            "value": f"{stats['focus_minutes']}{min_label}",
            "sub": focus_sub,
            "sub_color": focus_sub_color,
            "accent": STAT_COLORS[1],
        },
        {
            "icon": "< >",  # cards
            "label": cards_label,
            "value": str(stats["cards_earned"]),
            "sub": cards_sub,
            "sub_color": cards_sub_color,
            "accent": STAT_COLORS[2],
        },
        {
            "icon": "~ ~",  # mood wave
            "label": mood_label,
            "value": f"{stats['avg_mood']:.1f}/5" if stats["avg_mood"] > 0 else "--",
            "sub": f"{stats['mood_checks']}x",
            "sub_color": NEUTRAL_COLOR,
            "accent": STAT_COLORS[3],
        },
    ]

    # Draw stat cards as colored blocks
    card_width = 0.19
    card_start_x = 0.07
    card_y = 0.345

    for i, card in enumerate(card_data):
        x = card_start_x + i * (card_width + 0.04)

        # Accent dot
        fig.text(
            x + card_width / 2,
            card_y,
            "●",
            ha="center",
            va="center",
            fontsize=14,
            color=card["accent"],
        )
        # Value
        fig.text(
            x + card_width / 2,
            card_y - 0.03,
            card["value"],
            ha="center",
            va="center",
            fontsize=18,
            color=TEXT_PRIMARY,
            fontweight="bold",
            fontfamily="sans-serif",
        )
        # Label
        fig.text(
            x + card_width / 2,
            card_y - 0.055,
            card["label"],
            ha="center",
            va="center",
            fontsize=9,
            color=TEXT_SECONDARY,
            fontfamily="sans-serif",
        )
        # Comparison
        fig.text(
            x + card_width / 2,
            card_y - 0.075,
            card["sub"],
            ha="center",
            va="center",
            fontsize=7,
            color=card["sub_color"],
            fontfamily="sans-serif",
        )

    # --- Mood sparkline (bottom) ---
    mood_daily = stats.get("mood_daily", [])
    if mood_daily and len(mood_daily) >= 2:
        ax_mood = fig.add_axes([0.15, 0.06, 0.7, 0.14], facecolor="none")

        days = list(range(len(mood_daily)))
        moods = [d["avg_mood"] for d in mood_daily]
        day_labels = [d["day"][-5:] for d in mood_daily]  # MM-DD

        # Gradient fill under line
        ax_mood.fill_between(days, moods, alpha=0.15, color=ACCENT3)
        ax_mood.plot(
            days,
            moods,
            color=ACCENT3,
            linewidth=2.5,
            marker="o",
            markersize=6,
            markeredgecolor="white",
            markeredgewidth=1,
        )

        ax_mood.set_ylim(0.5, 5.5)
        ax_mood.set_xlim(-0.3, len(days) - 0.7)
        ax_mood.set_yticks([1, 2, 3, 4, 5])
        ax_mood.set_yticklabels(
            ["1", "2", "3", "4", "5"],
            fontsize=8,
            color=TEXT_SECONDARY,
        )
        ax_mood.set_xticks(days)
        ax_mood.set_xticklabels(day_labels, fontsize=7, color=TEXT_SECONDARY)

        ax_mood.spines["top"].set_visible(False)
        ax_mood.spines["right"].set_visible(False)
        ax_mood.spines["left"].set_color(GRID_COLOR)
        ax_mood.spines["bottom"].set_color(GRID_COLOR)
        ax_mood.tick_params(colors=TEXT_SECONDARY, labelsize=7)

        ax_mood.set_title(mood_title, fontsize=10, color=TEXT_SECONDARY, pad=8)
    else:
        # No mood data — show placeholder
        fig.text(
            0.5,
            0.12,
            no_mood_text,
            ha="center",
            va="center",
            fontsize=10,
            color=TEXT_SECONDARY,
        )

    # --- Footer ---
    fig.text(
        0.5,
        0.015,
        footer_text,
        ha="center",
        va="center",
        fontsize=9,
        color=TEXT_SECONDARY,
        alpha=0.4,
        fontfamily="sans-serif",
    )

    # --- Save to BytesIO ---
    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        bbox_inches="tight",
        pad_inches=0.3,
        facecolor=BG_COLOR,
    )
    plt.close(fig)
    buf.seek(0)

    return buf
