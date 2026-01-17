# RoXX Development Makefile

.PHONY: help install test lint clean docker-build docker-up docker-down

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies (dev mode)
	pip install -e ".[dev]"

test: ## Run unit tests
	pytest

test-cov: ## Run tests with coverage report
	pytest --cov=roxx --cov-report=term-missing

lint: ## Run code linter (ruff)
	ruff check .

format: ## Format code (black/ruff)
	ruff format .

clean: ## Clean build artifacts and cache
	rm -rf dist/ build/ *.egg-info
	find . -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -exec rm -rf {} +
	rm -rf .coverage htmlcov

docker-build: ## Build Docker image
	docker compose build --no-cache

docker-up: ## Start Docker containers
	docker compose up -d

docker-down: ## Stop Docker containers
	docker compose down

docker-logs: ## View Docker logs
	docker compose logs -f
