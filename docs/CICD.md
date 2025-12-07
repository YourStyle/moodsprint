# CI/CD Setup Guide

## Обзор

MoodSprint использует GitHub Actions для автоматизации CI/CD процессов:

- **CI (Continuous Integration)** - автоматическая проверка кода при каждом PR/push
- **CD (Continuous Deployment)** - автоматический деплой на staging/production

## Архитектура CI/CD

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   GitHub    │────▶│  CI Tests   │────▶│ Docker Build│
│    Push     │     │  & Linting  │     │   & Push    │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┴──────────────────────────┐
                    │                                                      │
                    ▼                                                      ▼
            ┌──────────────┐                                      ┌──────────────┐
            │   Staging    │                                      │  Production  │
            │  (auto on    │                                      │ (on tag or   │
            │   main)      │                                      │  manual)     │
            └──────────────┘                                      └──────────────┘
```

## CI Workflow (ci.yml)

### Триггеры
- Push в `main`, `develop`
- Pull Request в `main`, `develop`

### Jobs

| Job | Описание | Время |
|-----|----------|-------|
| `frontend-lint` | ESLint + TypeScript | ~1 мин |
| `frontend-test` | Jest тесты + coverage | ~2 мин |
| `frontend-build` | Next.js build | ~3 мин |
| `backend-lint` | flake8 + black + isort | ~1 мин |
| `backend-test` | pytest + coverage | ~2 мин |
| `bot-lint` | Python linting | ~30 сек |
| `admin-lint` | Python linting | ~30 сек |
| `docker-build` | Проверка сборки Docker | ~5 мин |
| `security-scan` | Trivy vulnerability scan | ~2 мин |

## CD Workflow (cd.yml)

### Триггеры
- Push в `main` → автодеплой на staging
- Git tag `v*` → деплой на production
- Manual workflow dispatch

### Environments

#### Staging
- URL: `https://staging.moodsprint.app`
- Автодеплой при push в main
- Для тестирования перед production

#### Production
- URL: `https://moodsprint.app`
- Деплой при создании тега или вручную
- Требует approval в GitHub

## Настройка

### 1. GitHub Secrets

Добавьте в Settings → Secrets and variables → Actions:

```
# Staging server
STAGING_HOST=staging.example.com
STAGING_USER=deploy
STAGING_SSH_KEY=<private key>

# Production server
PRODUCTION_HOST=prod.example.com
PRODUCTION_USER=deploy
PRODUCTION_SSH_KEY=<private key>

# Notifications (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

### 2. GitHub Environments

Создайте environments в Settings → Environments:

**staging:**
- Deployment branches: `main`
- No approval required

**production:**
- Deployment branches: tags `v*`
- Required reviewers: добавьте ответственных
- Wait timer: 0-60 минут

### 3. Server Setup

На каждом сервере:

```bash
# 1. Установите Docker
curl -fsSL https://get.docker.com | sh

# 2. Создайте директорию проекта
mkdir -p /opt/moodsprint
cd /opt/moodsprint

# 3. Создайте .env файл
cp .env.example .env
nano .env  # заполните переменные

# 4. Настройте Docker login для GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# 5. Создайте директорию для бэкапов
mkdir -p /backups
```

### 4. SSH Key Setup

```bash
# На локальной машине
ssh-keygen -t ed25519 -C "github-actions-deploy"

# Добавьте публичный ключ на сервер
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys

# Приватный ключ добавьте в GitHub Secrets
cat ~/.ssh/id_ed25519
```

## Использование

### Обычный workflow

```bash
# 1. Создайте feature branch
git checkout -b feature/my-feature

# 2. Commit и push
git add .
git commit -m "feat: add feature"
git push origin feature/my-feature

# 3. Создайте PR в main
# CI запустится автоматически

# 4. После merge в main
# Автодеплой на staging
```

### Релиз в production

```bash
# Вариант 1: Через tag
git tag v1.2.3
git push origin v1.2.3

# Вариант 2: Вручную
# GitHub → Actions → CD → Run workflow → production
```

### Rollback

```bash
# Через GitHub Actions
# Actions → CD → Run workflow → выберите rollback

# Или вручную на сервере
ssh deploy@server
cd /opt/moodsprint
docker compose down
docker compose pull  # предыдущие images
docker compose up -d
```

## Мониторинг

### Проверка статуса

```bash
# На сервере
docker compose ps
docker compose logs -f --tail=100

# Health check
curl http://localhost/health
```

### Alerts

Настройте уведомления:
1. **Slack** - через webhook в secrets
2. **Email** - GitHub notifications
3. **PagerDuty** - для критических алертов

## Оптимизация

### Кэширование

CI использует кэширование для ускорения:
- npm dependencies (frontend)
- pip dependencies (backend)
- Docker layers (GHA cache)

### Параллельность

Jobs выполняются параллельно где возможно:
```
frontend-lint ──┐
frontend-test ──┼──▶ docker-build
backend-lint ───┤
backend-test ───┘
```

## Troubleshooting

### CI fails на lint

```bash
# Локально исправьте
cd frontend && npm run lint -- --fix
cd backend && black app && isort app
```

### Docker build fails

```bash
# Проверьте локально
docker build -t test ./frontend
docker build -t test ./backend
```

### Deploy fails

1. Проверьте SSH доступ
2. Проверьте disk space на сервере
3. Проверьте Docker logs

```bash
# На сервере
df -h
docker system df
docker compose logs backend
```

## Security

### Секреты
- Никогда не коммитьте `.env` файлы
- Ротируйте ключи каждые 90 дней
- Используйте минимальные права для deploy user

### Сканирование
- Trivy сканирует на уязвимости
- Dependabot обновляет зависимости
- GitHub Security alerts включены

## Checklist для нового окружения

- [ ] Сервер настроен (Docker, SSH)
- [ ] GitHub Secrets добавлены
- [ ] GitHub Environment создан
- [ ] DNS настроен
- [ ] SSL сертификат (Let's Encrypt)
- [ ] Firewall настроен (80, 443, 22)
- [ ] Backup strategy определена
- [ ] Monitoring настроен
- [ ] Alerts настроены
