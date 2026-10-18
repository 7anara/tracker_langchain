# AI Personal Assistant Agent

Step 1 initializes FastAPI and SQLite on Python 3.12. Authentication and AI
features are not implemented yet.

## Run locally

From the repository root, with Python 3.12 and `uv` installed:

```bash
uv sync --locked
# Optional: copy .env.example to .env to customize DATABASE_URL.
uv run --locked uvicorn main:app --reload
```

In the prepared cloud environment, use the existing virtual environment:

```bash
cd /workspace/tracker_langchain
/workspace/.venvs/tracker_langchain/bin/python -m uvicorn main:app --reload
```

Run from the repository root so `.env` and the default `assistant.db` resolve
consistently. SQLite creates the database on the first connection; no application
tables are needed yet. Local databases and `.env` are ignored by Git.

## Verify

```bash
curl --fail http://127.0.0.1:8000/health
```

Expected HTTP 200 response: `{"status":"ok"}`.
The endpoint executes `SELECT 1` through the shared session dependency. A database
connection failure returns HTTP 503 with `{"detail":"Database unavailable"}`.
FastAPI also provides interactive documentation at `/docs`.

## Files

- `main.py`: application and health endpoint. `Depends` injects a database session;
  SQLAlchemy's `text` wraps the connectivity query.
- `mysite/config.py`: Pydantic settings loaded from environment variables or `.env`.
- `mysite/database/db.py`: one engine, one session factory, the shared model base,
  and `get_db`, which closes each request's session using a context manager.
- `pyproject.toml`: dependency declarations; `uv.lock` records exact resolved versions.
- `.env.example`: non-secret configuration example.

Step 2, after approval, adds the user model, registration, login, password hashing,
and the reusable `get_current_user` dependency. It will reuse `get_db` and `Base`.
