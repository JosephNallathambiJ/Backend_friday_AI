# FRIDAY AI Backend

Production-minded, local-first backend for the personal AI work assistant **FRIDAY AI**.

## Overview
- **Local-first AI**: Integrates with local Ollama instances (with optional cloud provider routing).
- **FastAPI Core**: Modular async architecture with Pydantic v2 validation.
- **SQLite + FTS5**: Local persistence and full-text document retrieval.
- **Security-First Tooling**: Strict filesystem path validation, command allowlists, persistent human-in-the-loop approval workflows, and audit logging.
- **Backend Only**: Exposes pure REST and SSE streaming endpoints.

## Quickstart

### Prerequisites
- Python 3.12+ (or managed via `uv`)
- Ollama running locally (e.g. `ollama run gemma4:12b`)

### Setup & Run
```bash
# Install dependencies
uv sync --extra dev

# Run database migrations
uv run alembic upgrade head

# Run tests
uv run pytest

# Start backend server
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
