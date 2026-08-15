.PHONY: help install dev-install hooks lint format check typecheck fix \
        validate test test-verbose test-cov ci run run-debug relock clean

# Every `uv run` and `uv sync` re-resolves and rewrites uv.lock, baking in
# whichever index the environment points at (UV_INDEX_URL / UV_DEFAULT_INDEX).
# Behind an internal mirror that leaks private hostnames into this public repo --
# see scripts/check-lockfile-index.sh. UV_FROZEN tells uv to use uv.lock as-is
# and never write it, so running tests can't dirty the tree. Use `make relock`
# after changing dependencies in pyproject.toml.
export UV_FROZEN = 1

# Pass extra pytest arguments through, e.g.
#   make test ARGS="-k conversation"
#   make test ARGS="neural_dive/tests/test_items.py -x"
ARGS ?=

# Default target
help:
	@echo "Neural Dive - Development Commands"
	@echo "==================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install package dependencies"
	@echo "  make dev-install   Install package + dev dependencies"
	@echo "  make hooks         Install git pre-commit hooks"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run tests (ARGS=\"-k name\" to filter)"
	@echo "  make test-verbose  Run tests with per-test output"
	@echo "  make test-cov      Run tests with coverage report"
	@echo ""
	@echo "Checks:"
	@echo "  make lint          Lint (ruff)"
	@echo "  make format        Auto-format (ruff)"
	@echo "  make typecheck     Type check (mypy)"
	@echo "  make fix           Auto-fix lint + format"
	@echo "  make check         lint + format check + typecheck"
	@echo "  make validate      Check NPC -> question references resolve"
	@echo "  make ci            check + test -- everything, run before pushing"
	@echo ""
	@echo "Dependencies:"
	@echo "  make relock        Regenerate uv.lock against public PyPI"
	@echo ""
	@echo "Running:"
	@echo "  make run           Run the game"
	@echo "  make run-debug     Run with a fixed seed (42)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         Remove build artifacts and caches"

# Installation
install:
	uv sync

dev-install:
	uv sync --all-extras

hooks:
	uv run prek install

# Linting and formatting
lint:
	uv run ruff check neural_dive/

format:
	uv run ruff format neural_dive/

check: lint
	uv run ruff format --check neural_dive/
	uv run mypy neural_dive/

typecheck:
	uv run mypy neural_dive/

fix:
	uv run ruff check --fix neural_dive/
	uv run ruff format neural_dive/

# Content validation. Exits non-zero if an NPC references a missing question.
validate:
	uv run validate_questions.py

# Regenerate uv.lock after a dependency change, against public PyPI so the
# lockfile stays shareable. Needs UV_FROZEN cleared to let uv write the file.
relock:
	UV_FROZEN= UV_INDEX_URL=https://pypi.org/simple \
	    UV_DEFAULT_INDEX=https://pypi.org/simple uv lock
	scripts/check-lockfile-index.sh

# Testing. Paths come from `testpaths` in pyproject.toml.
test:
	uv run pytest $(ARGS)

test-verbose:
	uv run pytest -vv $(ARGS)

test-cov:
	uv run pytest --cov=neural_dive --cov-report=html --cov-report=term $(ARGS)

# There is no CI for this repo, so this is the gate. Also what the pre-commit
# hooks run -- see .pre-commit-config.yaml.
ci: check test

# Running the game
run:
	uv run python -m neural_dive

run-debug:
	uv run python -m neural_dive --fixed --seed 42

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
