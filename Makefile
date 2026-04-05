.PHONY: help install bootstrap migrate upgrade db-shell redis-shell test lint fmt run-ui run-scheduler

help:
	@echo "ATOS — AI Trading Operating System"
	@echo ""
	@echo "  make install       Install dependencies"
	@echo "  make bootstrap     Spin up infra + create DB schema"
	@echo "  make migrate       Generate new Alembic migration"
	@echo "  make upgrade       Apply pending migrations"
	@echo "  make db-shell      Open psql shell"
	@echo "  make redis-shell   Open Redis CLI"
	@echo "  make test          Run unit tests"
	@echo "  make lint          Run ruff + mypy"
	@echo "  make fmt           Auto-format with black + ruff --fix"
	@echo "  make run-ui        Launch Streamlit dashboard"
	@echo "  make run-scheduler Launch APScheduler daemon"

install:
	pip install -r requirements-dev.txt
	pip install -e .

bootstrap:
	docker compose up -d postgres redis
	@echo "Waiting for Postgres..."
	@sleep 3
	python scripts/bootstrap_db.py

migrate:
	alembic revision --autogenerate -m "$(MSG)"

upgrade:
	alembic upgrade head

db-shell:
	docker compose exec postgres psql -U atos -d atos_db

redis-shell:
	docker compose exec redis redis-cli

test:
	pytest tests/unit/ -v --cov=atos --cov-report=term-missing

test-all:
	pytest tests/ -v --cov=atos --cov-report=term-missing

lint:
	ruff check atos/ config/ scripts/ tests/
	mypy atos/ config/

fmt:
	black atos/ config/ scripts/ tests/
	ruff check --fix atos/ config/ scripts/ tests/

run-ui:
	PYTHONPATH=/home/xinhangyuan/Documents/mycode/Chetan streamlit run atos/ui/app.py

run-scheduler:
	PYTHONPATH=/home/xinhangyuan/Documents/mycode/Chetan python -m atos.scheduler.jobs
