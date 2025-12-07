# MoodSprint Architecture

## Overview

MoodSprint is a productivity app that adapts task breakdown to user's current mood and energy level.
It combines AI-powered task decomposition, focus sessions, and gamification.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Telegram WebApp                          │
│                    (or Mobile Browser PWA)                      │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Nginx (Proxy)                           │
│                    Port 80/443 (Production)                     │
├─────────────────────────────┬───────────────────────────────────┤
│         /api/*              │              /*                   │
│            │                │               │                   │
│            ▼                │               ▼                   │
│   ┌─────────────────┐       │      ┌─────────────────┐         │
│   │  Flask Backend  │       │      │ Next.js Frontend│         │
│   │   Port 5000     │       │      │    Port 3000    │         │
│   └────────┬────────┘       │      └─────────────────┘         │
│            │                │                                   │
│            ▼                │                                   │
│   ┌─────────────────┐       │                                   │
│   │   PostgreSQL    │       │                                   │
│   │   Port 5432     │       │                                   │
│   └─────────────────┘       │                                   │
└─────────────────────────────┴───────────────────────────────────┘
```

## Domain Model

### Core Entities

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│     User     │       │     Task     │       │   Subtask    │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id           │──┐    │ id           │──┐    │ id           │
│ telegram_id  │  │    │ user_id      │  │    │ task_id      │
│ username     │  └───▶│ title        │  └───▶│ title        │
│ xp           │       │ description  │       │ order        │
│ level        │       │ priority     │       │ estimated_min│
│ streak_days  │       │ status       │       │ status       │
│ created_at   │       │ created_at   │       │ created_at   │
└──────────────┘       └──────────────┘       └──────────────┘
        │                                              │
        │              ┌──────────────┐                │
        │              │  MoodCheck   │                │
        │              ├──────────────┤                │
        └─────────────▶│ id           │                │
                       │ user_id      │                │
                       │ mood         │                │
                       │ energy       │                │
                       │ created_at   │                │
                       └──────────────┘                │
                                                       │
        ┌──────────────┐       ┌──────────────────────┘
        │ FocusSession │       │
        ├──────────────┤       │
        │ id           │◀──────┘
        │ user_id      │
        │ subtask_id   │
        │ started_at   │
        │ ended_at     │
        │ duration_min │
        │ completed    │
        └──────────────┘

┌──────────────┐       ┌──────────────┐
│ Achievement  │       │UserAchievement│
├──────────────┤       ├──────────────┤
│ id           │◀─────▶│ user_id      │
│ code         │       │ achievement_id│
│ title        │       │ unlocked_at  │
│ description  │       └──────────────┘
│ xp_reward    │
│ icon         │
└──────────────┘
```

## Frontend Architecture (Next.js)

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── layout.tsx          # Root layout with providers
│   │   ├── page.tsx            # Home/Dashboard
│   │   ├── tasks/              # Tasks pages
│   │   ├── focus/              # Focus session pages
│   │   └── profile/            # User profile & stats
│   │
│   ├── components/             # React components
│   │   ├── ui/                 # Base UI components
│   │   ├── tasks/              # Task-related components
│   │   ├── mood/               # Mood selector components
│   │   ├── focus/              # Focus session components
│   │   └── gamification/       # XP, achievements, etc.
│   │
│   ├── domain/                 # Domain layer
│   │   ├── types/              # TypeScript interfaces
│   │   ├── constants/          # App constants
│   │   └── utils/              # Domain utilities
│   │
│   ├── services/               # API layer
│   │   ├── api.ts              # Base API client
│   │   ├── tasks.ts            # Tasks API
│   │   ├── mood.ts             # Mood API
│   │   └── gamification.ts     # Gamification API
│   │
│   ├── hooks/                  # Custom React hooks
│   │   ├── useTasks.ts
│   │   ├── useFocusSession.ts
│   │   └── useTelegram.ts
│   │
│   └── lib/                    # Utilities
│       ├── telegram.ts         # Telegram WebApp SDK
│       └── storage.ts          # Local storage utils
│
├── public/                     # Static assets
└── next.config.js
```

## Backend Architecture (Flask)

```
backend/
├── app/
│   ├── __init__.py             # Flask app factory
│   ├── config.py               # Configuration
│   │
│   ├── models/                 # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── task.py
│   │   ├── subtask.py
│   │   ├── mood.py
│   │   ├── focus_session.py
│   │   └── achievement.py
│   │
│   ├── api/                    # API routes
│   │   ├── __init__.py
│   │   ├── auth.py             # Telegram auth
│   │   ├── tasks.py
│   │   ├── mood.py
│   │   ├── focus.py
│   │   └── gamification.py
│   │
│   ├── services/               # Business logic
│   │   ├── __init__.py
│   │   ├── ai_decomposer.py    # AI task breakdown
│   │   ├── xp_calculator.py    # XP/level logic
│   │   └── achievement_checker.py
│   │
│   └── utils/                  # Utilities
│       ├── telegram.py         # Telegram validation
│       └── response.py         # API response helpers
│
├── migrations/                 # Alembic migrations
├── requirements.txt
└── wsgi.py
```

## API Contract Overview

### Authentication
- `POST /api/auth/telegram` - Authenticate via Telegram initData

### Tasks
- `GET /api/tasks` - List user's tasks
- `POST /api/tasks` - Create task
- `PUT /api/tasks/:id` - Update task
- `DELETE /api/tasks/:id` - Delete task
- `POST /api/tasks/:id/decompose` - AI decompose task based on mood

### Subtasks
- `GET /api/tasks/:id/subtasks` - List subtasks
- `PUT /api/subtasks/:id` - Update subtask status
- `POST /api/subtasks/:id/reorder` - Reorder subtasks

### Mood
- `POST /api/mood` - Log mood check
- `GET /api/mood/latest` - Get latest mood
- `GET /api/mood/history` - Mood history

### Focus Sessions
- `POST /api/focus/start` - Start focus session
- `POST /api/focus/complete` - Complete session
- `POST /api/focus/cancel` - Cancel session
- `GET /api/focus/active` - Get active session
- `GET /api/focus/history` - Session history

### Gamification
- `GET /api/user/stats` - User XP, level, streak
- `GET /api/achievements` - All achievements
- `GET /api/user/achievements` - User's unlocked achievements

## Mood & Energy Scale

**Mood** (1-5):
1. Very Low - Feeling down, unmotivated
2. Low - Slightly off, distracted
3. Neutral - Okay, functional
4. Good - Positive, engaged
5. Great - Energized, motivated

**Energy** (1-5):
1. Exhausted - Need rest
2. Tired - Low capacity
3. Normal - Standard energy
4. Energized - High capacity
5. Peak - Maximum productivity

## AI Task Decomposition Strategy

Based on mood + energy combination:

| Mood/Energy | Strategy | Step Size | Break Frequency |
|-------------|----------|-----------|-----------------|
| Low/Low     | Micro    | 5-10 min  | Every 2 steps   |
| Low/High    | Gentle   | 10-15 min | Every 3 steps   |
| High/Low    | Careful  | 10-15 min | Every 2 steps   |
| High/High   | Standard | 15-25 min | Every 4 steps   |

## Gamification Rules

### XP Rewards
- Complete subtask: 10 XP
- Complete task: 50 XP
- Complete focus session: 25 XP
- Daily streak: 20 XP × streak_days (max 7)
- Mood check: 5 XP

### Levels
- Level = floor(sqrt(XP / 100))
- Level 1: 0-99 XP
- Level 2: 100-399 XP
- Level 3: 400-899 XP
- etc.

### Achievements
- First Task - Complete your first task
- Focus Master - Complete 10 focus sessions
- Week Warrior - 7-day streak
- Mood Tracker - Log mood 30 days
- etc.

## Security Considerations

1. **Telegram Auth** - Validate initData hash with bot token
2. **Rate Limiting** - Prevent API abuse
3. **Input Validation** - Sanitize all inputs
4. **CORS** - Restrict to known origins
5. **Environment Variables** - No secrets in code
