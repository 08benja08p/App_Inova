# Backend – Inova Docs API

Servicio FastAPI responsable de recibir documentos, ejecutar extracción/OCR con heurísticas
inspiradas en el proceso exportador de cerezas en Chile y exponer los resultados al frontend.

---

## Requisitos previos

- Python 3.11+
- Dependencias Python listadas en `backend/requirements.txt`.
- (Opcional, pero recomendado) Herramientas del sistema:
  - **Tesseract OCR** – se usa a través de `pytesseract` cuando no hay texto vectorial.
  - **Poppler** – requerido por `pdf2image` para rasterizar PDFs escaneados.
- Las guías del dominio están en `../guides/` y se cargan automáticamente mediante
  `app/services/knowledge.py`. No necesitas ejecutar pasos adicionales, pero puedes modificar esos
  archivos para ajustar reglas o nomenclaturas sin tocar código.

---

## Instalación y ejecución

```powershell
cd backend
python -m venv ..\.venv
..\ .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

El API estará disponible en <http://localhost:8000>. Documentación automática en `/docs` o `/redoc`.

---

## Endpoints principales

- `GET /health` – estado básico.
- `POST /documents` – recibe archivos (PDF/JPG/PNG). Almacena el binario, crea registros en SQLite y
  dispara el pipeline de procesamiento.
- `GET /documents/{id}` – devuelve metadatos (estado, tipo, idioma, timestamps).
- `GET /documents/{id}/text` – texto reconocido (OCR o PDF vectorial).
- `GET /documents/{id}/entities` – entidades detectadas (incoterms, HS Code, contenedores, etc.).
- `GET /documents/{id}/keywords` – keywords y scores asociados al texto.
- `GET /documents/{id}/insights` – reglas y recomendaciones generadas a partir de las guías del
  dominio.

La base se crea automáticamente en `backend/data/app.sqlite3` y los archivos se guardan en
`backend/storage/`.

---

## Arquitectura rápida

- `app/main.py` – configuración de FastAPI y CORS.
- `app/api/routes_documents.py` – endpoints para ingesta/consulta.
- `app/services/processing.py` – pipeline de OCR, extracción, validaciones y generación de insights.
- `app/services/knowledge.py` – carga los archivos de `guides/` para exponer esquemas y reglas.
- `app/models/` – modelos SQLAlchemy (Document, Entity, Keyword, ProcessingLog).
- `app/schemas/` – modelos Pydantic para las respuestas.

---

## Notas operativas

- El pipeline intenta extraer texto en este orden:
  1. PyPDF2 → pdfminer (`pdfminer.six`) para PDFs con texto seleccionable.
  2. `pdf2image + pytesseract` si el PDF es un escaneo o si el archivo es una imagen.
  3. Texto de demostración cuando no se pudo extraer nada (por ejemplo, si no están instaladas las
     dependencias opcionales).
- Las recomendaciones e insights se generan cruzando entidades detectadas con las reglas descritas
  en `guides/`. Ajusta esas guías para adaptar la demo a otros productos o flujos.
- El almacenamiento (SQLite / carpeta `storage/`) se puede limpiar con seguridad durante el
  desarrollo; la aplicación volverá a crear la estructura al iniciarse.

Con esto tienes todo lo necesario para operar o extender la API sin revisar otros archivos.
