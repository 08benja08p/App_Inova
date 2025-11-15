# Inova Docs – demo de control documental

Prototipo extremo a extremo (FastAPI + React) para demostrar cómo subir documentos de exportación
frutícola, aplicar OCR/heurísticas específicas del rubro de las cerezas chilenas y presentar
hallazgos guiados en una interfaz operativa de cuatro pasos.

---

## Estructura del repositorio

```
backend/   → API FastAPI, servicios de OCR/NLP y acceso a guías del dominio
frontend/  → App React + Vite (panel demo)
guides/    → Conocimiento experto: esquemas, reglas y KB para exportación de cerezas
tests/     → Carpeta reservada para suites automatizadas (vacía por ahora)
```

Todas las dependencias Python viven en `backend/requirements.txt`. El frontend administra las suyas
con Yarn 1.x dentro de `frontend/`.

---

## Arranque rápido

### Backend (FastAPI)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Endpoints visibles en <http://localhost:8000/docs>. Los principales son:

- `POST /documents` – ingesta de PDF/JPG/PNG (o captura desde cámara en el frontend).
- `GET /documents/{id}` – metadatos y estado.
- `GET /documents/{id}/text | /entities | /keywords | /insights` – resultados de OCR, extracción y
  reglas específicas del dominio.

El backend persiste en SQLite (`backend/data/app.sqlite3`) y guarda archivos en
`backend/storage/`. Para más detalles, revisa `backend/README.md`.

### Frontend (React + Vite)

```bash
cd frontend
yarn install
yarn dev
```

- URL por defecto: <http://localhost:5173>.
- Configura `VITE_API_BASE_URL` si el backend corre en otra dirección.
- `frontend/README.md` describe los scripts y notas de UI.

---

## Dependencias del sistema para OCR real

El backend intenta primero leer PDFs con PyPDF2/pdfminer; si no hay texto vectorial, rasteriza y
aplica OCR con `pdf2image + pytesseract`. Instala en el sistema:

1. **Tesseract OCR** – <https://tesseract-ocr.github.io/tessdoc/Installation.html>
2. **Poppler** – binarios disponibles en
   <https://github.com/oschwartz10612/poppler-windows/releases/> (agrega la carpeta `bin` al PATH).

Sin estas herramientas, el servicio seguirá funcionando pero usará el texto de demostración y las
heurísticas internas.

---

## Guías del dominio (carpeta `guides/`)

Los archivos JSON/MD describen documentos, campos y reglas cruzadas para el proceso exportador:

- `exportacion_cerezas_extraction_schema.json`: campos mínimos por tipo documental.
- `exportacion_cerezas_kb.json`: errores típicos, consistencias obligatorias y contexto operativo.
- `exportacion_cerezas_documentacion.md` y `exportacion_cerezas_validation_rules.md`: material
  narrativo de referencia.

`backend/app/services/knowledge.py` carga estas guías al iniciar, así que puedes ajustar
comportamientos (reglas, textos, recomendaciones) modificando los archivos sin tocar código.

---

## Documentación adicional

- `backend/README.md`: instalación, notas de almacenamiento y explicación de servicios.
- `frontend/README.md`: scripts y tips para la app React.
- `guides/`: referencia funcional y ejemplos que alimentan las heurísticas.

Utiliza este README como índice y dirígete a la sección correspondiente según necesites profundizar
en backend, frontend o conocimiento de negocio.
