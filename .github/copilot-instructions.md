# Copilot Instructions for App_Inova (Backend PoC)

This repo is a FastAPI backend PoC to ingest document images/PDFs, run OCR/NLP (currently stubbed), and expose extracted text/entities/keywords.

## Big picture

- Tech: Python 3.13, FastAPI, SQLAlchemy (SQLite), Pydantic.
- Flow (happy path):
  1. POST /documents uploads a file → `services/storage.save_upload` writes it to `backend/storage/`.
  2. A DB `Document` is created; processing runs synchronously via `services/processing.process_document_sync`.
  3. Processing writes `ProcessingLog` (JSON string in `payload`), plus `Entity` and `Keyword` records.
  4. GET endpoints return status, text (from logs), entities, and keywords.
- No Celery/Redis yet; processing is inline to keep the PoC simple.

## Key files and directories

- `backend/app/main.py`: App wiring. Adds CORS, `/health`, includes documents router, auto-creates tables on startup.
- `backend/app/api/routes_documents.py`: REST endpoints for upload and retrieval.
- `backend/app/core/config.py`: Settings (SQLite path, storage dir). Uses `pydantic-settings`.
- `backend/app/core/db.py`: SQLAlchemy engine/session and `init_db()`.
- `backend/app/models/document.py`: ORM models: `Document`, `Entity`, `Keyword`, `ProcessingLog`.
- `backend/app/schemas/documents.py`: Pydantic response models.
- `backend/app/services/storage.py`: File persistence for uploads.
- `backend/app/services/processing.py`: Processing pipeline (currently a deterministic stub with fake OCR/entities/keywords).

## Data model notes

- IDs are UUID v4 as strings.
- `ProcessingLog.payload` is a JSON-serialized text field. Always `json.loads()` before use.
- `Document.status` moves from `processing` → `done` or `failed` in `POST /documents`.

## API surface (PoC)

- `GET /health` → `{ status: "ok" }`.
- `POST /documents` (multipart file; accepts image/jpeg, image/png, application/pdf) → `{ id, status, createdAt }`.
- `GET /documents/{id}` → document meta/status.
- `GET /documents/{id}/text` → [{ page, text, bbox?, confidence }]; text comes from the last `ProcessingLog(step="ocr")`.
- `GET /documents/{id}/entities` → list of `{ id, type, value, confidence, page? }`.
- `GET /documents/{id}/keywords` → list of `{ keyword, score }`.

## Run and debug (Windows/PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger: http://localhost:8000/docs
- DB: `backend/data/app.sqlite3` (created on startup).
- Storage: `backend/storage/`.

## Coding patterns to follow

- DB sessions via `Depends(get_db)` (see `core/db.py`). Commit is explicit in endpoints/services.
- When adding processing logic, extend `process_document_sync` and write:
  - an `ocr` log with `{ text, confidence }` in `ProcessingLog`.
  - any extracted `Entity`/`Keyword` rows.
- Validate content types on upload; keep file I/O in `services/storage.py`.
- Use existing Pydantic schemas in `schemas/documents.py` for response shape.

## Minimal testing pattern (needs httpx)

```python
from fastapi.testclient import TestClient
from backend.app.main import app
client = TestClient(app)
assert client.get('/health').status_code == 200
```

## Questions for maintainers

- Confirm target doc types and priority entities (e.g., HS code, Incoterms, BL, containers, amounts/dates).
- Any constraints for file sizes/mime types beyond the current defaults?
- Are we adding real OCR/NLP (PaddleOCR/spaCy/YAKE) next, or keep stub for the demo?
