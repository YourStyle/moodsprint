# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MoodSprint is a mood-aware task management Telegram Mini App with gamification. It uses AI to break down tasks into smaller steps based on user's mood and energy level.

## Development Commands

### Full Stack (Docker)
```bash
# Development environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Production
docker-compose up -d --build
```

Services run at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000/api/v1
- Full app via nginx: http://localhost:8080

### Frontend (Next.js)
```bash
cd frontend
npm run dev          # Start dev server
npm run build        # Build for production
npm run lint         # ESLint
npm run type-check   # TypeScript check
```

### Backend (Flask)
```bash
cd backend
python wsgi.py                                    # Run dev server
flask db migrate -m "description"                 # Create migration
flask db upgrade                                  # Apply migrations
python -m black app                               # Format code
python -m flake8 app --max-line-length=100       # Lint
```

### Telegram Bot
```bash
cd bot
python main.py                                    # Run bot
python -m black . && python -m flake8 . --max-line-length=100
```

## Architecture

### Three-Service Architecture
1. **Frontend** (`/frontend`) - Next.js 14 with App Router, TypeScript, Tailwind CSS
2. **Backend** (`/backend`) - Flask REST API with SQLAlchemy, PostgreSQL
3. **Bot** (`/bot`) - aiogram Telegram bot with APScheduler for notifications

### Frontend Structure
- `/src/app/` - Next.js pages using App Router
- `/src/components/` - React components organized by domain (ui, tasks, mood, focus, gamification, cards)
- `/src/services/` - API client modules (one file per domain)
- `/src/lib/store.ts` - Zustand global state
- `/src/domain/types/` - TypeScript interfaces

### Backend Structure
- `/app/api/` - Flask blueprints (REST endpoints)
- `/app/models/` - SQLAlchemy models
- `/app/services/` - Business logic (AI decomposition, XP calculation, achievements, card battles)
- `/app/utils/` - Utilities (response helpers, Telegram auth validation)
- `/migrations/` - Alembic migrations

### Key Patterns
- Frontend uses React Query for server state, Zustand for client state
- Backend uses Flask factory pattern (`create_app()`)
- All API responses follow format: `{ success: bool, data?: {}, error?: { code, message } }`
- Authentication via Telegram WebApp initData (validated in backend)
- JWT tokens for subsequent API calls

### Bot Features
- APScheduler runs cron jobs for reminders, weekly summaries, task postponement
- Connects to same PostgreSQL database as backend
- Admin commands for analytics and user management

## Database Migrations

Migrations are in `/backend/migrations/versions/`. Naming convention: `YYYYMMDD_NNNNNN_description.py`

Always run `flask db upgrade` in backend container after adding migrations.

## Environment Variables

Key variables (see `.env.example`):
- `TELEGRAM_BOT_TOKEN` - From @BotFather
- `OPENAI_API_KEY` - For AI task decomposition
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - For token signing

## Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

Hooks run black, isort, and flake8 on Python files.
