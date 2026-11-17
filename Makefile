.PHONY: up down logs test lint seed
up:
	docker compose up --build
down:
	docker compose down
logs:
	docker compose logs -f --tail=200
seed:
	docker compose exec api python -m app.scripts.seed_demo
test:
	cd backend && pytest
lint:
	cd backend && ruff check app tests
