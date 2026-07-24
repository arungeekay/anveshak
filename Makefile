# ANVESHAK — dev tasks. Works from WSL/Git Bash (Windows) or Linux.
VENV := .venv
PY := $(VENV)/bin/python
ifeq ($(OS),Windows_NT)
  PY := $(VENV)/Scripts/python.exe
endif

.PHONY: help install dev test lint fmt data build-frontend deploy

help:
	@echo "install       - create venv deps"
	@echo "dev           - run FastAPI (uvicorn --reload) on :8000"
	@echo "test          - run pytest"
	@echo "lint          - ruff check"
	@echo "fmt           - ruff format"
	@echo "data          - build synthetic DuckDB + CSV exports"
	@echo "build-frontend- vite production build"
	@echo "deploy        - deploy to Catalyst (see deploy.md)"

install:
	$(PY) -m pip install -r requirements-dev.txt

dev:
	$(PY) -m uvicorn backend.main:app --reload --port 8000

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check .

fmt:
	$(PY) -m ruff format .

data:
	$(PY) -m data_engine.build

build-frontend:
	cd frontend && npm install && npm run build

deploy:
	bash scripts/deploy.sh
