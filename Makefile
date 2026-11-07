.PHONY: install media demo backend frontend mcp

PYTHON ?= $(shell command -v python3.13 || command -v python3.12 || command -v python3.11 || command -v python3)

install:
	cd backend && $(PYTHON) -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
	cd frontend && npm install

media:
	cd backend && . .venv/bin/activate && python generate_demo_media.py

demo:
	cd backend && . .venv/bin/activate && python prepare_demo.py

backend:
	cd backend && . .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	cd frontend && npm run dev -- --host 0.0.0.0 --port 5173

mcp:
	cd backend && . .venv/bin/activate && python mcp_server.py
