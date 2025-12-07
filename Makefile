.PHONY: help install dev build test lint format clean deploy-staging deploy-prod

# Colors
YELLOW := \033[1;33m
GREEN := \033[1;32m
NC := \033[0m

help: ## Show this help
	@echo "$(GREEN)MoodSprint$(NC) - Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# ===========================================
# Development
# ===========================================

install: ## Install all dependencies
	cd frontend && npm install
	cd backend && pip install -r requirements.txt
	cd bot && pip install -r requirements.txt
	cd admin && pip install -r requirements.txt

dev: ## Start development environment
	docker compose up -d db
	@echo "$(GREEN)Starting services...$(NC)"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend:  http://localhost:5000"
	@echo "Admin:    http://localhost:5001"

dev-frontend: ## Start frontend dev server
	cd frontend && npm run dev

dev-backend: ## Start backend dev server
	cd backend && flask run --reload --port 5000

dev-bot: ## Start bot in dev mode
	cd bot && python main.py

dev-admin: ## Start admin panel dev server
	cd admin && flask run --reload --port 5001

# ===========================================
# Docker
# ===========================================

docker-build: ## Build all Docker images
	docker compose build

docker-up: ## Start all services
	docker compose up -d

docker-down: ## Stop all services
	docker compose down

docker-logs: ## Show logs
	docker compose logs -f

docker-clean: ## Clean Docker resources
	docker compose down -v
	docker system prune -af

# ===========================================
# Testing
# ===========================================

test: test-frontend test-backend ## Run all tests

test-frontend: ## Run frontend tests
	cd frontend && npm test

test-backend: ## Run backend tests
	cd backend && pytest tests/ -v

test-coverage: ## Run tests with coverage
	cd frontend && npm test -- --coverage
	cd backend && pytest tests/ -v --cov=app --cov-report=html

# ===========================================
# Linting & Formatting
# ===========================================

lint: lint-frontend lint-backend ## Run all linters

lint-frontend: ## Lint frontend code
	cd frontend && npm run lint

lint-backend: ## Lint backend code
	cd backend && flake8 app --max-line-length=120
	cd backend && black --check app
	cd backend && isort --check-only app

format: format-frontend format-backend ## Format all code

format-frontend: ## Format frontend code
	cd frontend && npm run lint -- --fix

format-backend: ## Format backend code
	cd backend && black app
	cd backend && isort app

typecheck: ## Run TypeScript type checking
	cd frontend && npm run type-check

# ===========================================
# Database
# ===========================================

db-migrate: ## Run database migrations
	cd backend && flask db upgrade

db-rollback: ## Rollback last migration
	cd backend && flask db downgrade

db-reset: ## Reset database
	cd backend && flask db downgrade base
	cd backend && flask db upgrade

db-seed: ## Seed database with test data
	cd backend && flask seed

# ===========================================
# Deployment
# ===========================================

deploy-staging: ## Deploy to staging
	@echo "$(YELLOW)Deploying to staging...$(NC)"
	gh workflow run cd.yml -f environment=staging

deploy-prod: ## Deploy to production (requires confirmation)
	@echo "$(YELLOW)⚠️  You are about to deploy to PRODUCTION$(NC)"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	gh workflow run cd.yml -f environment=production

release: ## Create a new release
	@read -p "Enter version (e.g., 1.2.3): " version; \
	git tag -a "v$$version" -m "Release v$$version"; \
	git push origin "v$$version"

# ===========================================
# Utilities
# ===========================================

clean: ## Clean build artifacts
	rm -rf frontend/.next frontend/node_modules
	rm -rf backend/__pycache__ backend/.pytest_cache
	rm -rf bot/__pycache__
	rm -rf admin/__pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

logs-backend: ## Show backend logs
	docker compose logs -f backend

logs-frontend: ## Show frontend logs
	docker compose logs -f frontend

logs-bot: ## Show bot logs
	docker compose logs -f bot

shell-backend: ## Open shell in backend container
	docker compose exec backend /bin/bash

shell-db: ## Open PostgreSQL shell
	docker compose exec db psql -U moodsprint moodsprint

health: ## Check service health
	@echo "$(YELLOW)Checking health...$(NC)"
	@curl -s http://localhost/health | jq . || echo "Backend not responding"
	@curl -s http://localhost:5001/health | jq . || echo "Admin not responding"
