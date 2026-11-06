.PHONY: install media backend frontend

install:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
	cd frontend && npm install

media:
	cd backend && . .venv/bin/activate && python3 generate_demo_media.py

backend:
	cd backend && . .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	cd frontend && npm run dev -- --host 0.0.0.0 --port 5173
