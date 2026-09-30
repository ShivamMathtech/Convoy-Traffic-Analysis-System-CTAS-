.PHONY: backend frontend dev test docker clean

backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

dev:
	python scripts/start_dev.py

test:
	cd backend && pytest app/tests -q

docker:
	docker compose up --build

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	rm -rf backend/.pytest_cache frontend/dist
