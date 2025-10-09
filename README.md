# App_Inova - PoC Backend & Frontend

Este repositorio contiene el backend (FastAPI) para una PoC de lectura de documentos (OCR) y
extracción de información (entidades y keywords) orientado a importación/exportación, junto con una
interfaz web en React + Vite que replica el storyboard de la experiencia de usuario.

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
dependencias. Cada componente cuenta con su propio HTML y CSS para mantener la maqueta ordenada.

```bash
cd frontend
yarn install
yarn dev
```

Encontrarás una pantalla de inicio de sesión (no funcional, siempre permite el acceso) y un panel
visual que replica las escenas del storyboard compartido. Ajusta los textos o conecta los endpoints
cuando lo necesites.
