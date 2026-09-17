.PHONY: up down dev logs migrate makemigration test shell pull-models

up:
	docker compose up -d

down:
	docker compose down

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

logs:
	docker compose logs -f

migrate:
	docker compose exec aria-backend alembic upgrade head

makemigration:
	docker compose exec aria-backend alembic revision --autogenerate -m "$(msg)"

test:
	docker compose exec aria-backend pytest -v

shell:
	docker compose exec aria-backend bash

pull-models:
	ollama pull qwen3:8b
	ollama pull bge-m3
