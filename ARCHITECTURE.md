# MoodSprint Architecture

## Overview

MoodSprint is a mood-aware task management Telegram Mini App with gamification. It uses AI to break down tasks into smaller steps based on user's mood and energy level. Features include a collectible card system, campaign mode, friend trading, and focus timer.

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
│   ┌─────────────────┐      │      ┌─────────────────┐          │
│   │  Flask Backend   │      │      │ Next.js Frontend│          │
│   │   Port 5000      │      │      │    Port 3000    │          │
│   └────────┬────────┘      │      └─────────────────┘          │
│            │                │                                   │
│   ┌────────▼────────┐      │      ┌─────────────────┐          │
│   │   PostgreSQL     │◄────┼─────►│   aiogram Bot   │          │
│   │   Port 5432      │     │      │  (APScheduler)  │          │
│   └────────┬────────┘      │      └─────────────────┘          │
│   ┌────────▼────────┐      │                                   │
│   │     Redis        │      │                                   │
│   │   (AI cache)     │      │                                   │
│   └─────────────────┘      │                                   │
└─────────────────────────────┴───────────────────────────────────┘
```

Three services share a PostgreSQL database. Redis is used for AI response caching.

## Backend Architecture

### API Blueprints (`backend/app/api/`)

| Blueprint | File | Prefix | Domain |
|-----------|------|--------|--------|
| `api_bp` | `tasks.py` | `/api/v1` | Core task CRUD, decomposition, smart sorting |
| `shared_tasks_bp` | `shared_tasks.py` | `/api/v1/tasks` | Task sharing between friends |
| `api_bp` | `cards.py` | `/api/v1` | Card system, deck, trading, friends |
| `api_bp` | `gamification.py` | `/api/v1` | XP, achievements, merging, quests |
| `api_bp` | `campaign.py` | `/api/v1` | Campaign (PvE) gameplay |
| `api_bp` | `focus.py` | `/api/v1` | Focus timer sessions |
| `api_bp` | `sparks.py` | `/api/v1` | Spark (in-app currency) system |
| `api_bp` | `onboarding.py` | `/api/v1` | User profile setup |
| `api_bp` | `admin.py` | `/api/v1` | Card pool admin endpoints |
| `api_bp` | `auth.py` | `/api/v1` | Telegram auth + JWT |

### Services (`backend/app/services/`)

| Service | Responsibility |
|---------|---------------|
| `card_service.py` | Card generation, AI descriptions, deck management, leveling, genre/archetype system |
| `friend_service.py` | Friend requests, friendship management |
| `card_trading_service.py` | Trade offers between users |
| `companion_service.py` | Active companion card (bonus system) |
| `showcase_service.py` | Profile showcase cards |
| `campaign_energy_service.py` | Campaign energy (earn, spend, limits) |
| `merge_service.py` | Card merging mechanics and probability |
| `ai_decomposer.py` | GPT-powered task decomposition into subtasks |
| `task_classifier.py` | AI task type classification and time recommendation |
| `task_service.py` | Task scoring, time slot logic, auto-postpone |
| `profile_analyzer.py` | GPT analysis of user onboarding responses |
| `priority_advisor.py` | AI-powered priority escalation |
| `quest_service.py` | Daily quest generation with themed names |
| `monster_generator.py` | AI monster generation for campaign |
| `cosmetics_service.py` | Cosmetic items and customization |
| `event_service.py` | Seasonal events and exclusive cards |
| `openai_client.py` | Shared OpenAI client with proxy support |

### AI Cost Tracking

All OpenAI API calls (9 call sites) are instrumented via `backend/app/utils/ai_tracker.py`:
- `tracked_openai_call()` wraps `client.chat.completions.create()`, measures latency, and logs to `ai_usage_log` table
- Tracks: user_id, model, prompt/completion tokens, estimated cost, latency, endpoint name
- Bot has its own async tracker at `bot/services/ai_tracker.py` (same DB table)
- Admin dashboard at `/ai-costs` shows cost breakdown by endpoint, model, and user

### Models (`backend/app/models/`)

30+ SQLAlchemy models across:
- `user.py` — User, UserSettings
- `task.py` — Task, Subtask, SharedTask, TaskStatus
- `card.py` — UserCard, CardTemplate, CardTrade, Friendship, MergeLog
- `user_profile.py` — UserProfile, UserAchievement
- `quest.py` — DailyQuest, quest templates
- `character.py` — Genre themes, campaign chapters
- `event.py` — SeasonalEvent, EventExclusiveCard
- `ai_usage_log.py` — AIUsageLog for cost tracking

## Frontend Architecture (Next.js 14 App Router)

### Pages (`frontend/src/app/`)

| Route | Page | Tab? |
|-------|------|------|
| `/` | Home — tasks, calendar, mood, focus timer | Yes |
| `/deck` | Card collection and deck builder | Yes |
| `/store` | Spark store | Yes |
| `/profile` | User profile, settings, stats | Yes |
| `/tasks/[id]` | Task detail with subtasks | No |
| `/campaign` | PvE campaign levels | Yes |
| `/focus` | Full focus timer | No |

### Key Components

- `components/tasks/` — WeekCalendar, TaskCardCompact, TaskCard, TaskForm, SubtaskItem
- `components/focus/` — FocusTimer, FocusWidget, MiniTimer
- `components/cards/` — DeckCard, CardEarnedModal, CardTutorial
- `components/gamification/` — DailyBonus, LevelUpModal, EventBanner, StreakIndicator
- `components/ui/` — Button, Card, Modal, Progress, Input, ScrollBackdrop

### State Management

- **React Query** — server state (tasks, cards, user data)
- **Zustand** (`lib/store.ts`) — client state (UI mode, selected date, modals)

### Utilities

- `lib/i18n/translations.ts` — ru/en translations, `TranslationKey` auto-derived from keys
- `lib/dateUtils.ts` — date formatting and elapsed time calculation
- `lib/telegram.ts` — Telegram WebApp SDK integration
- `services/` — API client modules (one per domain)

## Bot Structure (aiogram 3.x)

- `handlers/` — message/callback handlers with FSM
- `services/` — voice transcription, weekly digest, AI tracker
- `database.py` — async SQLAlchemy session (same DB as backend)
- `translations.py` — bot-specific ru/en translations
- APScheduler for cron jobs (reminders, auto-postpone, weekly summaries)

## Admin Panel

Separate Flask app (`admin/app.py`) with Jinja2 templates and Tailwind CDN:
- User management, task analytics
- Card pool CRUD, quest templates
- AI cache management (Redis)
- AI costs dashboard
- Decomposition template library

## Mood & Energy Scale

**Mood** (1-5): Very Low → Low → Neutral → Good → Great
**Energy** (1-5): Exhausted → Tired → Normal → Energized → Peak

## AI Task Decomposition Strategy

Based on mood + energy combination:

| Mood/Energy | Strategy | Step Size | Break Frequency |
|-------------|----------|-----------|-----------------|
| Low/Low     | Micro    | 5-10 min  | Every 2 steps   |
| Low/High    | Gentle   | 10-15 min | Every 3 steps   |
| High/Low    | Careful  | 10-15 min | Every 2 steps   |
| High/High   | Standard | 15-25 min | Every 4 steps   |

## Gamification

### XP Rewards
- Complete subtask: 10 XP
- Complete task: 50 XP
- Complete focus session: 25 XP
- Daily streak: 20 XP x streak_days (max 7)
- Mood check: 5 XP

### Card System
- Cards earned by completing tasks and focus sessions
- 5 rarities: Common, Uncommon, Rare, Epic, Legendary
- 5 genres: Fantasy, Sci-Fi, Cyberpunk, Mythology, Horror (unlocked by level)
- Card leveling: XP per level = cardLevel * 100, stats +5%/level
- Merging: combine two cards for a chance at higher rarity
- Companion: active card provides bonuses

### Campaign
- PvE chapters with monsters per genre
- Energy system: chapter 1 free, rest costs 1 energy
- Hard mode: difficulty * 1.5

## Security

1. **Telegram Auth** — validate initData hash with bot token
2. **JWT** — for subsequent API calls after auth
3. **Admin routes** — protected by `@admin_required` decorator (checks ADMIN_IDS env var)
4. **AI cost tracking** — monitors per-user API usage
5. **Input validation** — sanitize all inputs at API boundary
