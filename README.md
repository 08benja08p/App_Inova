# App_Inova - PoC Backend & Frontend

Este repositorio contiene el backend (FastAPI) para una PoC de lectura de documentos (OCR) y
extracción de información (entidades y keywords) orientado a importación/exportación, junto con una
interfaz web en React + Vite que guía el flujo operativo en cuatro pasos: subir, verificar, editar y
resumir documentos.

## Backend

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

## Frontend

El frontend vive en `frontend/` y está construido con React + Vite usando Yarn como gestor de
dependencias. Cada componente cuenta con su propio HTML y CSS para mantener la maqueta ordenada y
ahora se conecta al backend para consultar metadatos, entidades, keywords y texto OCR.

```bash
cd frontend
yarn install
yarn dev
```

Variables relevantes:

- `VITE_API_BASE_URL`: URL base del backend FastAPI (por defecto `http://localhost:8000`).

Encontrarás una pantalla de inicio de sesión (no funcional, siempre permite el acceso) y un panel
que organiza el flujo documental en secciones dedicadas a subir, verificar, editar y resumir cada
archivo.
