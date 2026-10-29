# SPDX-FileCopyrightText: Stefan Tatschner
#
# SPDX-License-Identifier: MIT

# Project tasks for oscclip.
# Run `just --list` to see all available tasks.

default: lint typecheck test

# Install the development environment.
sync:
    uv sync

# Update all dependencies.
update:
    uv sync --upgrade

# Run ruff checks.
lint:
    uv run ruff check .
    uv run ruff format --check .

# Fix formatting and linting issues.
fix:
    uv run ruff check --fix .
    uv run ruff format .

# Run the type checkers (mypy --strict and ty).
typecheck:
    uv run mypy
    uv run ty check

# Run the test suite.
test:
    uv run pytest

# Build sdist and wheel into dist/.
build:
    uv build

# Run osc-copy from the working tree.
copy *args:
    uv run osc-copy {{args}}

# Run osc-paste from the working tree.
paste *args:
    uv run osc-paste {{args}}

# Remove build and cache artifacts.
clean:
    rm -rf .venv dist build *.egg-info .pytest_cache .mypy_cache .ruff_cache
