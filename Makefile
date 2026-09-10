PYTHON ?= py
VENV_WIN := .venv/Scripts/python.exe
VENV_UNIX := .venv/bin/python
PY :=

ifneq ($(wildcard $(VENV_WIN)),)
	PY := $(VENV_WIN)
endif
ifeq ($(PY),)
	ifneq ($(wildcard $(VENV_UNIX)),)
		PY := $(VENV_UNIX)
	endif
endif
ifeq ($(PY),)
	PY := $(PYTHON)
endif

HOST ?= 0.0.0.0
PORT ?= 8000
BACKUP_DIR := backups
TS := $(shell date +%Y%m%d_%H%M%S)

.PHONY: setup run test quality format migrate backup restore verify up down container-check docker-build docker-clean

setup:
	$(PYTHON) -m venv .venv
ifeq ($(OS),Windows_NT)
	$(VENV_WIN) -m pip install --upgrade pip
	$(VENV_WIN) -m pip install -r requirements-dev.txt
else
	$(VENV_UNIX) -m pip install --upgrade pip
	$(VENV_UNIX) -m pip install -r requirements-dev.txt
endif
	@test -f .env || cp .env.example .env
	@mkdir -p data

run:
	$(PY) -m uvicorn app.main:app --reload --host $(HOST) --port $(PORT)

test:
	$(PY) -m pytest -q tests/

quality:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

format:
	$(PY) -m ruff format .

migrate:
	$(PY) -m app.init_db

backup:
	@mkdir -p $(BACKUP_DIR)
	@test -f data/alpine.db || (echo "No database file. Run make migrate first." && exit 1)
	cp data/alpine.db $(BACKUP_DIR)/alpine_$(TS).db
	@echo "Backup saved to $(BACKUP_DIR)/alpine_$(TS).db"

restore:
	@test -n "$(FILE)" || (echo "Usage: make restore FILE=backups/alpine_YYYY.db" && exit 1)
	@test -f "$(FILE)" || (echo "Backup file not found: $(FILE)" && exit 1)
	cp $(FILE) data/alpine.db

# ЭТА ЦЕЛЬ БЫЛА В README, НО ОТСУТСТВОВАЛА ЗДЕСЬ!
verify: test quality

# Docker команды
docker-build:
	docker compose build

up: docker-build
	docker compose up -d

down:
	docker compose down

docker-clean: down
	docker compose down -v --rmi local
	rm -rf data/*

container-check:
	docker compose exec app python -m ruff check .
	docker compose exec app python -m pytest -q tests/
