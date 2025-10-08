from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes_documents import router as documents_router
from .core.db import init_db

app = FastAPI(title="Inova Docs API", version="0.1.0")

# CORS básico para la demo; ajusta orígenes según tu frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(documents_router, prefix="/documents", tags=["documents"])


@app.on_event("startup")
def on_startup():
    # Crear tablas si no existen (SQLite)
    init_db()
