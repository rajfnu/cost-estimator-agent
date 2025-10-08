# Makefile for Cost Estimator Agent
# Provides convenient commands for development, testing, and deployment

.PHONY: help install dev-install test lint format clean docker-build docker-run docs serve-docs

# Default target
help:
	@echo "🤖 Cost Estimator Agent - Available Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  install       Install the package and dependencies"
	@echo "  dev-install   Install with development dependencies"
	@echo "  setup         Run interactive setup script"
	@echo ""
	@echo "Development:"
	@echo "  test          Run all tests"
	@echo "  test-unit     Run unit tests only"
	@echo "  test-coverage Run tests with coverage report"
	@echo "  lint          Run linting checks"
	@echo "  format        Format code with black and isort"
	@echo "  type-check    Run mypy type checking"
	@echo ""
	@echo "Running:"
	@echo "  serve         Start the API server"
	@echo "  cli-help      Show CLI help"
	@echo "  example       Run estimation on example file"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean         Clean build artifacts and cache"
	@echo "  docs          Build documentation"
	@echo "  serve-docs    Serve documentation locally"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build  Build Docker image"
	@echo "  docker-run    Run Docker container"

# Installation targets
install:
	@echo "📦 Installing Cost Estimator Agent..."
	pip install -e .

dev-install:
	@echo "📦 Installing with development dependencies..."
	pip install -e ".[dev,test,docs]"

setup:
	@echo "🚀 Running interactive setup..."
	python scripts/setup.py install

# Development targets
test:
	@echo "🧪 Running all tests..."
	pytest tests/ -v

test-unit:
	@echo "🧪 Running unit tests..."
	pytest tests/unit/ -v

test-integration:
	@echo "🧪 Running integration tests..."
	pytest tests/integration/ -v

test-coverage:
	@echo "🧪 Running tests with coverage..."
	pytest tests/ --cov=src/cost_estimator --cov-report=html --cov-report=term

lint:
	@echo "🔍 Running linting checks..."
	ruff check src/ tests/
	black --check src/ tests/
	isort --check-only src/ tests/

format:
	@echo "✨ Formatting code..."
	black src/ tests/
	isort src/ tests/
	ruff --fix src/ tests/

type-check:
	@echo "🔍 Running type checks..."
	mypy src/cost_estimator

# Running targets
serve:
	@echo "🚀 Starting API server..."
	uvicorn cost_estimator.api:app --reload --host 0.0.0.0 --port 8000

cli-help:
	@echo "📖 CLI Help:"
	python -m cost_estimator.cli --help

example:
	@echo "📊 Running example estimation..."
	python -m cost_estimator.cli estimate --input examples/minimal_example.json

example-sales:
	@echo "📊 Running sales coach example..."
	python -m cost_estimator.cli estimate --input examples/sales_coach_app.json

example-support:
	@echo "📊 Running support bot example..."
	python -m cost_estimator.cli estimate --input examples/customer_support_bot.json

validate-examples:
	@echo "🔍 Validating all examples..."
	python -m cost_estimator.cli validate examples/minimal_example.json
	python -m cost_estimator.cli validate examples/sales_coach_app.json
	python -m cost_estimator.cli validate examples/customer_support_bot.json
	python -m cost_estimator.cli validate examples/content_generator.json

compare-examples:
	@echo "📊 Comparing example scenarios..."
	python -m cost_estimator.cli compare examples/

# Maintenance targets
clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf docs/_build/

docs:
	@echo "📚 Building documentation..."
	cd docs && make html

serve-docs:
	@echo "📚 Serving documentation..."
	cd docs/_build/html && python -m http.server 8080

# Docker targets
docker-build:
	@echo "🐳 Building Docker image..."
	docker build -t cost-estimator-agent .

docker-run:
	@echo "🐳 Running Docker container..."
	docker run -p 8000:8000 -v $(PWD)/.env:/app/.env cost-estimator-agent

docker-dev:
	@echo "🐳 Running Docker container in development mode..."
	docker run -p 8000:8000 -v $(PWD):/app -v $(PWD)/.env:/app/.env cost-estimator-agent

# CI/CD targets
ci-install:
	@echo "🔧 Installing for CI..."
	pip install -e ".[test]"

ci-test:
	@echo "🧪 Running CI tests..."
	pytest tests/ --cov=src/cost_estimator --cov-report=xml --cov-fail-under=80

ci-lint:
	@echo "🔍 Running CI linting..."
	ruff check src/ tests/
	black --check src/ tests/
	isort --check-only src/ tests/
	mypy src/cost_estimator

# Release targets
pre-commit:
	@echo "🔍 Running pre-commit checks..."
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) type-check
	$(MAKE) test

release-check:
	@echo "🚀 Checking release readiness..."
	$(MAKE) clean
	$(MAKE) install
	$(MAKE) test
	$(MAKE) lint
	$(MAKE) validate-examples

# Development workflow targets
dev-setup: dev-install setup
	@echo "✅ Development environment ready!"

quick-test:
	@echo "⚡ Running quick tests..."
	pytest tests/unit/ -x --tb=short

watch-test:
	@echo "👀 Watching for changes and running tests..."
	pytest-watch tests/unit/

# Benchmark targets
benchmark:
	@echo "📈 Running performance benchmarks..."
	python -m cost_estimator.cli estimate --input examples/content_generator.json --format json > /tmp/benchmark.json
	@echo "Benchmark completed. Results in /tmp/benchmark.json"

# Database targets (if using database features)
db-init:
	@echo "🗄️ Initializing database..."
	# Add database initialization commands here

db-migrate:
	@echo "🗄️ Running database migrations..."
	# Add migration commands here

# Security targets
security-check:
	@echo "🔒 Running security checks..."
	bandit -r src/
	safety check

# API testing targets
test-api:
	@echo "🌐 Testing API endpoints..."
	python -c "import requests; print('API Health:', requests.get('http://localhost:8000/health').json())"

load-test:
	@echo "⚡ Running load tests..."
	# Add load testing commands here (e.g., with locust)

# Documentation targets
docs-clean:
	@echo "🧹 Cleaning documentation..."
	rm -rf docs/_build/

docs-auto:
	@echo "📚 Auto-building documentation..."
	sphinx-autobuild docs docs/_build/html

# Version management
version:
	@echo "📋 Current version:"
	python -c "from cost_estimator import __version__; print(__version__)"

bump-patch:
	@echo "⬆️ Bumping patch version..."
	# Add version bumping logic here

bump-minor:
	@echo "⬆️ Bumping minor version..."
	# Add version bumping logic here

bump-major:
	@echo "⬆️ Bumping major version..."
	# Add version bumping logic here