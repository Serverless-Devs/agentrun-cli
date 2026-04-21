.PHONY: help install dev lint test test-unit test-integration test-cov coverage clean build build-linux build-macos build-all

PYTHON   ?= python3
VENV     := .venv
BIN      := $(VENV)/bin
PIP      := $(BIN)/pip
PIP_MIRROR := -i https://mirrors.aliyun.com/pypi/simple/
PYINST   := $(BIN)/pyinstaller
APP_NAME := agentrun
SPEC     := agentrun.spec
VERSION  := $(shell $(PYTHON) -c "from src.agentrun_cli import __version__; print(__version__)" 2>/dev/null || echo "0.1.0")

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install the package in editable mode
	$(PYTHON) -m venv $(VENV)
	$(PIP) install $(PIP_MIRROR) -e ".[dev]" 2>/dev/null || $(PIP) install $(PIP_MIRROR) -e .

dev: ## Install with dev dependencies
	$(PYTHON) -m venv $(VENV)
	$(PIP) install $(PIP_MIRROR) -e ".[dev]" || $(PIP) install $(PIP_MIRROR) -e .
	$(PIP) install $(PIP_MIRROR) pyinstaller

lint: ## Run ruff linter
	$(BIN)/ruff check src/ tests/

test: ## Run all tests (unit + integration)
	$(BIN)/pytest tests/unit tests/integration -v

test-unit: ## Run unit tests only
	$(BIN)/pytest tests/unit -v

test-integration: ## Run integration tests only
	$(BIN)/pytest tests/integration -v

test-cov: ## Run all tests with coverage report
	$(BIN)/pytest tests/unit tests/integration --cov=agentrun_cli --cov-report=term-missing --cov-branch

coverage: ## Enforce coverage threshold (>=95%) on the full test suite
	$(BIN)/pytest tests/unit tests/integration --cov=agentrun_cli --cov-report=term-missing --cov-branch --cov-fail-under=95

clean: ## Remove build artifacts
	rm -rf build/ dist/ *.spec __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

build: ## Build binary for the current platform (uses agentrun.spec)
	DISABLE_BREAKING_CHANGES_WARNING=1 \
	$(PYINST) --clean --noconfirm $(SPEC)
	@echo ""
	@echo "Binary built: dist/$(APP_NAME)"
	@ls -lh dist/$(APP_NAME)

build-macos: build ## Alias for build (on macOS, just run 'make build')
	@echo "macOS binary ready at dist/$(APP_NAME)"

# Cross-compiling Python to Linux is not supported by PyInstaller.
# Use this target inside a Linux environment (Docker / CI).
build-linux: build ## Build Linux binary (run inside Linux or Docker)
	@echo "Linux binary ready at dist/$(APP_NAME)"

build-all: ## Build for all platforms (macOS local + Linux via Docker)
	@echo "=== Building macOS binary ==="
	$(MAKE) build
	@mkdir -p dist/macos && cp dist/$(APP_NAME) dist/macos/$(APP_NAME)
	@echo ""
	@echo "=== Building Linux binary via Docker ==="
	tar cf - --exclude=.venv --exclude=.git --exclude=build --exclude=dist --exclude=__pycache__ --exclude='*.pyc' . | \
	docker run --rm -i -v $(PWD)/dist:/out python:3.10-slim sh -c \
		"mkdir /build && cd /build && tar xf - && \
		 apt-get update -qq && apt-get install -y -qq binutils >/dev/null 2>&1 && \
		 pip install $(PIP_MIRROR) -e . && pip install $(PIP_MIRROR) pyinstaller && \
		 DISABLE_BREAKING_CHANGES_WARNING=1 \
		 pyinstaller --clean --noconfirm $(SPEC) && \
		 cp dist/$(APP_NAME) /out/$(APP_NAME)"
	@mkdir -p dist/linux && cp dist/$(APP_NAME) dist/linux/$(APP_NAME)
	@echo ""
	@echo "=== Build complete ==="
	@ls -lh dist/macos/$(APP_NAME) dist/linux/$(APP_NAME)