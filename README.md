# MoodSprint

Adaptive task management app that adjusts task breakdown based on your mood and energy level.

## Features

- **Mood-aware task decomposition**: AI breaks down tasks into smaller steps based on your current state
- **Focus sessions**: Pomodoro-style timer with task tracking
- **Gamification**: XP, levels, streaks, and achievements
- **Telegram Mini App**: Optimized for use inside Telegram
- **PWA support**: Installable as mobile app

## Tech Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, React Query, Zustand
- **Backend**: Flask, SQLAlchemy, PostgreSQL
- **Infrastructure**: Docker, Nginx

## Quick Start

### Prerequisites

- Docker & Docker Compose
- (Optional) Telegram Bot Token from @BotFather
- (Optional) OpenAI API Key for AI task decomposition

### Development

1. Clone the repository:
```bash
git clone <repo-url>
cd moodsprint
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Edit `.env` with your settings (Telegram token, OpenAI key, etc.)

4. Start the development environment:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

5. Access the app:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:5000/api/v1
   - Full app via nginx: http://localhost:8080

### Production

1. Configure production environment:
```bash
cp .env.example .env
# Edit .env with production values
```

2. Build and start:
```bash
docker-compose up -d --build
```

3. Access the app on port 80 (or configured PORT)

## Project Structure

```
moodsprint/
├── backend/                 # Flask API
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic
│   │   └── utils/          # Utilities
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/               # Next.js App
│   ├── src/
│   │   ├── app/           # Pages (App Router)
│   │   ├── components/    # React components
│   │   ├── domain/        # Types & constants
│   │   ├── services/      # API clients
│   │   ├── hooks/         # Custom hooks
│   │   └── lib/           # Utilities
│   ├── Dockerfile
│   └── package.json
│
├── nginx/                  # Reverse proxy
│   ├── nginx.conf
│   └── Dockerfile
│
├── docker-compose.yml      # Production compose
├── docker-compose.dev.yml  # Development override
└── .env.example
```

## API Documentation

See [API.md](./API.md) for full API specification.

### Key Endpoints

- `POST /api/v1/auth/telegram` - Authenticate via Telegram
- `GET/POST /api/v1/tasks` - Task management
- `POST /api/v1/tasks/:id/decompose` - AI task decomposition
- `POST /api/v1/mood` - Log mood check
- `POST /api/v1/focus/start` - Start focus session
- `GET /api/v1/user/stats` - User statistics

## Telegram Mini App Setup

1. Create a bot with @BotFather
2. Enable Mini App for the bot
3. Set the Mini App URL to your deployed frontend
4. Add the bot token to `.env`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT
