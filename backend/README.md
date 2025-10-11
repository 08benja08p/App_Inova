# Inova Docs API (PoC)

Backend mínimo en FastAPI para ingesta de documentos, OCR/NLP simplificados y exposición de resultados vía API.

## Endpoints

- `GET /health`
- `POST /documents` (multipart file)
- `GET /documents/{id}`
- `GET /documents/{id}/text`
- `GET /documents/{id}/entities`
- `GET /documents/{id}/keywords`

## Ejecutar local (sin Docker)

1) Crear entorno e instalar dependencias mínimas:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

2) Iniciar API:

```powershell
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

3) Probar en Swagger: <http://localhost:8000/docs>

## Notas

- Persistencia SQLite en `backend/data/app.sqlite3`.
- Archivos se guardan en `backend/storage/`.
- OCR/NLP están simulados por defecto, pero `app/services/processing.py` intentará usar herramientas opcionales si están instaladas.