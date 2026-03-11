.PHONY: help install install-dev run test test-cov lint format typecheck security clean docker-build docker-run

PYTHON      := python3
VENV        := .venv
PIP         := $(VENV)/bin/pip
PYTEST      := $(VENV)/bin/pytest
RUFF        := $(VENV)/bin/ruff
MYPY        := $(VENV)/bin/mypy
BANDIT      := $(VENV)/bin/bandit
SRC         := src

##@ General

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup

install: ## Install runtime dependencies
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-dev: ## Install all dependencies including dev/test tools
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt

##@ Run

run: ## Start the voice assistant
	PYTHONPATH=$(SRC) $(VENV)/bin/python main.py

##@ Testing

test: ## Run the full test suite
	PYTHONPATH=$(SRC) $(PYTEST) tests/ -v

test-cov: ## Run tests with coverage report
	PYTHONPATH=$(SRC) $(PYTEST) tests/ \
		--cov=$(SRC)/assistant \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		-v

test-fast: ## Run tests excluding slow/integration markers
	PYTHONPATH=$(SRC) $(PYTEST) tests/ -v -m "not slow and not integration"

##@ Code Quality

lint: ## Run ruff linter
	$(RUFF) check $(SRC) tests

format: ## Auto-format code with ruff
	$(RUFF) format $(SRC) tests
	$(RUFF) check --fix $(SRC) tests

typecheck: ## Run mypy static type checker
	PYTHONPATH=$(SRC) $(MYPY) $(SRC)/assistant

security: ## Run bandit security scanner
	$(BANDIT) -r $(SRC) -c pyproject.toml

check: lint typecheck security ## Run all quality checks

##@ Docker

docker-build: ## Build the Docker image
	docker build -t virtual-personal-assistant:latest .

docker-run: ## Run the assistant in Docker
	docker-compose up

##@ Cleanup

clean: ## Remove build artefacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	find . -name ".coverage" -delete
	@echo "Cleaned."
