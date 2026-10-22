# FRIDAY AI Operational Guide

## 1. Prerequisites

- **Python**: 3.12+ (or managed via `uv`)
- **Package Manager**: `uv` recommended for deterministic, fast dependency management.
- **Local Model Provider**: Ollama (Optional, required for live LLM inference).
  - Install Ollama: `brew install ollama` (macOS)
  - Run Ollama service: `ollama serve`
  - Pull recommended model: `ollama pull gemma4:12b` (or `ollama pull llama3.2`)

---

## 2. Configuration & Environment Variables

All settings are strongly typed via Pydantic Settings in `app/core/config.py`.
Copy `.env.example` to `.env` to customize settings:

```ini
APP_NAME=friday-ai-backend
ENVIRONMENT=development
DEBUG=false
HOST=127.0.0.1
PORT=8000
DATABASE_URL=sqlite+aiosqlite:///friday.db
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_DEFAULT_MODEL=gemma4:12b
CLOUD_AI_ENABLED=false
SCHEDULER_ENABLED=true
```

---

## 3. Database Initialization & Migrations

FRIDAY AI uses SQLAlchemy 2.x and Alembic with asynchronous SQLite (`aiosqlite`).

```bash
# Apply migrations to head
uv run alembic upgrade head

# Initialize tables and seed default tools
uv run python -c "import asyncio; from app.db.init_db import init_database, seed_default_tools; asyncio.run(init_database()); asyncio.run(seed_default_tools())"
```

---

## 4. Running the Server

Start the FastAPI application with Uvicorn:

```bash
# Development mode with hot-reloading
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Production mode
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Once running:
- API Root: `http://127.0.0.1:8000/`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`
- Health Liveness: `http://127.0.0.1:8000/health/live`
- Health Readiness: `http://127.0.0.1:8000/health/ready`
- System Status: `http://127.0.0.1:8000/api/v1/status`

---

## 5. Verification & Testing

Run all unit, integration, and security tests:

```bash
# Execute automated test suite
uv run pytest

# Execute end-to-end live workflow verification
uv run python scripts/verify_workflow.py

# Linting and formatting checks
uv run ruff check .
uv run ruff format --check .
```
