.PHONY: backend frontend test

backend: ## Run FastAPI backend (http://127.0.0.1:8000, docs at /docs)
	./backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend

frontend: ## Run Vite frontend (http://localhost:5173)
	cd frontend && npm run dev

test: ## Run fast backend tests (skip slow e2e)
	cd backend && ./.venv/bin/python -m pytest tests/test_agents.py tests/test_orchestrator.py tests/test_routing.py tests/test_state.py tests/test_websocket.py tests/test_connection_manager.py -q
