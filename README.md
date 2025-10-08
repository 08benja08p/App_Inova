# App_Inova - PoC Backend

Este repositorio contiene el backend (FastAPI) para una PoC de lectura de documentos (OCR) y extracción de información (entidades y keywords) orientado a importación/exportación.

- Documentación y uso: ver `backend/README.md`.
- Endpoints principales: carga de documentos y consulta de resultados.

Arranque rápido (Windows/PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Luego abre <http://localhost:8000/docs> para probar.
