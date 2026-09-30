.PHONY: api-dev web-dev test lint typecheck format check

api-dev:
	.venv/Scripts/python -m uvicorn renzai.main:app --app-dir apps/api/src --reload

web-dev:
	pnpm --dir apps/web dev

test:
	.venv/Scripts/python -m pytest
	pnpm --dir apps/web test

lint:
	.venv/Scripts/python -m ruff check .
	pnpm --dir apps/web lint

typecheck:
	.venv/Scripts/python -m mypy
	pnpm --dir apps/web typecheck

format:
	.venv/Scripts/python -m ruff format .
	pnpm --dir apps/web format

check: lint typecheck test
