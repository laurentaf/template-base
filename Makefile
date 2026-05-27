.PHONY: lint test format docker pipeline health check init clean

lint:
	uv run ruff check src/ tests/ data/ cli/
	uv run ruff format --check src/ tests/ data/ cli/

format:
	uv run ruff check --fix src/ tests/ data/ cli/
	uv run ruff format src/ tests/ data/ cli/

test:
	uv run pytest tests/ -v

docker:
	docker compose up -d

docker-down:
	docker compose down

pipeline:
	uv run python -m src.main pipeline

health:
	uv run python -m src.main health

check: lint test

init:
	uv run python -m src.main init --yes

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
