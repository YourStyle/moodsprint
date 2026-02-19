# MoodSprint

Adaptive task management Telegram Mini App that adjusts task breakdown based on your mood and energy level, with a full gamification layer including collectible cards, campaigns, and social features.

## Features

- **Mood-aware task decomposition**: AI breaks down tasks into smaller steps based on your current state
- **Focus sessions**: Pomodoro-style timer with task tracking
- **Collectible card system**: Earn cards by completing tasks, 5 genres, 5 rarities
- **Card merging & trading**: Combine cards for upgrades, trade with friends
- **Campaign mode**: PvE battles against genre-themed monsters
- **Gamification**: XP, levels, streaks, achievements, daily quests
- **Telegram Bot**: Voice task creation, reminders, weekly digest
- **Admin panel**: User management, analytics, AI cost tracking
- **i18n**: Russian and English

## Tech Stack

- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, React Query, Zustand
- **Backend**: Flask, SQLAlchemy, PostgreSQL, Redis
- **Bot**: aiogram 3.x, APScheduler
- **Admin**: Flask, Jinja2, Tailwind CDN
- **AI**: OpenAI GPT (task decomposition, classification, card generation)
- **Infrastructure**: Docker Compose, Nginx

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Telegram Bot Token from @BotFather
- OpenAI API Key

### Development

```bash
git clone <repo-url>
cd moodsprint
cp .env.example .env
# Edit .env with your Telegram token, OpenAI key, etc.

docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Services:
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000/api/v1
- Full app via nginx: http://localhost:8080

### Production

```bash
docker-compose up -d --build
```

### Local Development (without Docker)

```bash
# Frontend
cd frontend && npm install && npm run dev

# Backend
cd backend && pip install -r requirements.txt && python wsgi.py

# Bot
cd bot && pip install -r requirements.txt && python main.py
```

## Project Structure

```
moodsprint/
├── backend/                 # Flask REST API
│   ├── app/
│   │   ├── api/            # Route blueprints (tasks, cards, gamification, etc.)
│   │   ├── models/         # 30+ SQLAlchemy models
│   │   ├── services/       # Business logic (15+ service classes)
│   │   └── utils/          # Auth, response helpers, AI tracker
│   └── migrations/         # Alembic migrations
│
├── frontend/               # Next.js 14 App
│   ├── src/
│   │   ├── app/           # Pages (App Router)
│   │   ├── components/    # React components (ui, tasks, cards, etc.)
│   │   ├── domain/        # Types & constants
│   │   ├── services/      # API clients
│   │   └── lib/           # i18n, store, utilities
│   └── package.json
│
├── bot/                    # Telegram Bot (aiogram)
│   ├── handlers/          # Message & callback handlers
│   ├── services/          # Voice, digest, AI tracker
│   └── translations.py
│
├── admin/                  # Admin Panel (Flask + Jinja2)
│   ├── app.py
│   └── templates/
│
├── nginx/                  # Reverse proxy config
├── ARCHITECTURE.md         # Detailed architecture docs
├── CLAUDE.md              # AI assistant instructions
└── docker-compose.yml
```

## Key Commands

```bash
# Frontend
cd frontend
npm run dev          # Dev server
npm run build        # Production build
npm run type-check   # TypeScript check

# Backend
cd backend
flask db migrate -m "description"  # Create migration
flask db upgrade                   # Apply migrations
python -m black app                # Format
python -m flake8 app --max-line-length=100

# Bot
cd bot
python main.py
```

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed architecture documentation including service layer, AI tracking, card system, and gamification rules.

## Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

Runs black, isort, and flake8 on Python files automatically.

## License

MIT
