.PHONY: help setup seed test lint typecheck clean docker-up docker-down

help:
	@echo "NETRA-X Makefile Commands:"
	@echo "  make setup       Install Python dependencies & setup venv"
	@echo "  make seed        Run deterministic synthetic seed pipeline"
	@echo "  make test        Run unit, integration & E2E acceptance tests"
	@echo "  make lint        Run Python flake8 and ESLint"
	@echo "  make typecheck   Run mypy and TypeScript type check"
	@echo "  make docker-up   Start all Docker Compose services"
	@echo "  make docker-down Stop all Docker Compose services"

setup:
	python -m pip install -e .[dev]

seed:
	python -m seed.generator

test:
	pytest tests/ -v

lint:
	flake8 apps/ workers/ packages/ seed/ tests/

typecheck:
	mypy apps/ workers/ packages/ seed/ tests/

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down -v

clean:
	rm -rf .pytest_cache .mypy_cache __pycache__ *.egg-info build dist
