# MoodSprint — Spec Document

## Product Overview

| Section | Item | Details |
|---------|------|---------|
| **Концепция** | Описание | Умный планировщик задач с геймификацией и адаптацией под настроение |
| | Целевая аудитория | Люди с ADHD, прокрастинаторы, те кто хочет геймифицировать продуктивность |
| | Платформа | Telegram Mini App (TMA) |
| | Монетизация | Freemium (планируется) |

---

## Core Features

| Section | Item | Details |
|---------|------|---------|
| **Задачи** | Создание | Название, описание, приоритет (low/medium/high), дедлайн |
| | AI-классификация | Автоопределение типа задачи (creative, analytical, coding и др.) |
| | AI-декомпозиция | Разбиение на подзадачи с учётом настроения и энергии |
| | Умная сортировка | По приоритету, дедлайну, предпочтительному времени |
| | Автоперенос | Просроченные задачи переносятся на следующий день в полночь |
| **Фокус-таймер** | Режимы | Pomodoro (25/5), Deep Work (45/10), Quick (15/3) |
| | Функции | Пауза, пропуск перерыва, звуковые уведомления |
| | Награды | XP за завершённые сессии |
| **Геймификация** | XP-система | Очки за задачи, фокус-сессии, ежедневную активность |
| | Уровни | 15 уровней с прогрессией |
| | Достижения | 30+ ачивок (стрики, задачи, фокус и др.) |
| | Стрики | Серии ежедневной активности |
| | Daily Bonus | Ежедневный бонус XP |
| **Настроение** | Трекинг | Mood (1-5) и Energy (1-5) при входе |
| | Адаптация | AI подстраивает декомпозицию под состояние |

---

## Tech Stack

| Layer | Technology | Details |
|-------|------------|---------|
| **Frontend** | Next.js 14 | App Router, Server Components |
| | TypeScript | Strict mode |
| | Tailwind CSS | Utility-first styling |
| | Framer Motion | Анимации и переходы |
| | Zustand | State management |
| | Telegram WebApp SDK | Интеграция с Telegram |
| **Backend** | Flask | Python REST API |
| | SQLAlchemy | ORM |
| | Flask-JWT-Extended | Аутентификация |
| | Gunicorn | WSGI сервер (4 workers, gthread) |
| **AI** | OpenAI API | gpt-4o-mini |
| | Прокси | Squid proxy для обхода геоблокировки |
| | Сервисы | TaskClassifier, AIDecomposer, PriorityAdvisor, ProfileAnalyzer |
| **Telegram Bot** | aiogram 3.x | Асинхронный бот |
| | APScheduler | Cron-задачи (уведомления, автоперенос) |
| | FSM | Состояния для рассылки |
| **Database** | PostgreSQL 15 | Основная БД |
| | SQLAlchemy | Миграции через Flask-Migrate |
| **Admin Panel** | Flask | Отдельное приложение на порту 5001 |
| | Jinja2 | Server-side рендеринг |
| | Chart.js | Графики и дашборды |

---

## Infrastructure

| Component | Technology | Details |
|-----------|------------|---------|
| **Hosting** | Yandex Cloud | VPS |
| **Containerization** | Docker | Multi-container setup |
| | Docker Compose | Оркестрация сервисов |
| **Services** | backend (x2) | Flask API с load balancing |
| | frontend | Next.js standalone |
| | bot | aiogram Telegram bot |
| | admin | Admin panel |
| | db | PostgreSQL 15 Alpine |
| | nginx | Reverse proxy, SSL termination |
| **Proxy Server** | Squid | Отдельный VPS для OpenAI API |
| **CI/CD** | GitHub Actions | Build & push Docker images |
| | GHCR | GitHub Container Registry |
| **Reverse Proxy** | Nginx | SSL, routing, static files |
| **Domain** | moodsprint.ru | Cloudflare DNS |

---

## API Structure

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/telegram` | POST | Авторизация через Telegram |
| `/api/v1/tasks` | GET/POST | Список/создание задач |
| `/api/v1/tasks/<id>` | GET/PUT/DELETE | CRUD задачи |
| `/api/v1/tasks/<id>/decompose` | POST | AI-декомпозиция задачи |
| `/api/v1/tasks/<id>/subtasks` | GET/POST | Подзадачи |
| `/api/v1/focus/sessions` | GET/POST | Фокус-сессии |
| `/api/v1/users/me` | GET/PUT | Профиль пользователя |
| `/api/v1/users/me/mood` | POST | Запись настроения |
| `/api/v1/gamification/achievements` | GET | Достижения |
| `/api/v1/gamification/daily-bonus` | POST | Получить ежедневный бонус |

---

## Bot Commands

| Command | Description | Access |
|---------|-------------|--------|
| `/start` | Запуск бота, открытие WebApp | All |
| `/tasks` | Список задач | All |
| `/focus` | Запуск фокус-сессии | All |
| `/stats` | Статистика пользователя | All |
| `/admin` | Админ-панель | Admin only |

---

## Scheduled Jobs (APScheduler)

| Job | Schedule | Description |
|-----|----------|-------------|
| `postpone_overdue_tasks` | 00:05 daily | Перенос просроченных задач |
| `send_postpone_notifications` | 09:10, 13:00, 18:10, 21:00 | Уведомления о переносе по времени пользователя |
| `check_achievements` | Every 30 min | Проверка новых достижений |

---

## Environment Variables

| Variable | Service | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | backend, bot | Токен Telegram бота |
| `OPENAI_API_KEY` | backend | API ключ OpenAI |
| `OPENAI_PROXY` | backend | HTTP прокси для OpenAI |
| `DATABASE_URL` | backend, bot | PostgreSQL connection string |
| `JWT_SECRET_KEY` | backend | Секрет для JWT токенов |
| `SECRET_KEY` | backend, admin | Flask secret key |
| `ADMIN_IDS` | bot | Telegram ID администраторов |
| `WEBAPP_URL` | bot | URL фронтенда для TMA |

---

## Data Models

| Model | Key Fields |
|-------|------------|
| **User** | telegram_id, username, level, xp, streak, mood, energy |
| **Task** | title, description, priority, status, due_date, task_type, preferred_time |
| **Subtask** | task_id, title, estimated_minutes, order, is_completed |
| **FocusSession** | user_id, task_id, duration, completed_at |
| **Achievement** | user_id, achievement_type, unlocked_at |
| **MoodLog** | user_id, mood, energy, logged_at |
| **PostponeLog** | task_id, from_date, to_date, notified |
