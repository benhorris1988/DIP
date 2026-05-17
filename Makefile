.PHONY: install backend frontend dev clean

install:
	cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt
	cd frontend && npm install

backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

dev:
	@echo "Run 'make backend' and 'make frontend' in two terminals, or use docker compose up"

clean:
	rm -rf backend/.venv backend/dip.db frontend/node_modules frontend/dist
