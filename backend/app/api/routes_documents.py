import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..models.document import Document, Entity, Keyword, ProcessingLog
from ..schemas.documents import (
    DocumentCreateResponse,
    DocumentDetailResponse,
    DocumentInsightsResponse,
    EntityResponse,
    KeywordResponse,
    TextBlock,
)
from ..services.storage import save_upload
from ..services.processing import process_document_sync

router = APIRouter()


@router.post("/", response_model=DocumentCreateResponse)
async def create_document(
    file: UploadFile = File(...),
    doc_type: Optional[str] = None,
    language_hint: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if file.content_type not in {"image/jpeg", "image/png", "application/pdf", "text/html"}:
        raise HTTPException(status_code=415, detail="Tipo de archivo no soportado")

    storage_path, size = await save_upload(file)

    doc = Document(
        id=str(uuid.uuid4()),
        filename=file.filename,
        mime=file.content_type,
        size=size,
        doc_type=doc_type,
        status="processing",
        storage_path=storage_path,
        language_detected=language_hint,
    )
    db.add(doc)
    db.commit()

    # Para la PoC inicial, procesamos en línea (sin Celery)
    try:
        process_document_sync(db, doc)
        status = "done"
    except Exception as e:
        status = "failed"
        doc.status = status
        db.commit()
        raise HTTPException(status_code=500, detail=f"Error de procesamiento: {e}")

    doc.status = status
    db.commit()

    return DocumentCreateResponse(
        id=doc.id, status=doc.status, createdAt=doc.created_at
    )


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
async def get_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return DocumentDetailResponse(
        id=doc.id,
        status=doc.status,
        docType=doc.doc_type,
        languageDetected=doc.language_detected,
        createdAt=doc.created_at,
        updatedAt=doc.updated_at,
    )


@router.get("/{doc_id}/entities", response_model=List[EntityResponse])
async def list_entities(doc_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    entities = (
        db.query(Entity)
        .filter(Entity.document_id == doc_id)
        .order_by(Entity.type)
        .all()
    )
    return [
        EntityResponse(
            id=e.id,
            type=e.type,
            value=e.value,
            confidence=e.confidence,
            page=e.page,
        )
        for e in entities
    ]


@router.get("/{doc_id}/keywords", response_model=List[KeywordResponse])
async def list_keywords(doc_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    kws = db.query(Keyword).filter(Keyword.document_id == doc_id).all()
    return [KeywordResponse(keyword=k.keyword, score=k.score) for k in kws]


@router.get("/{doc_id}/text", response_model=List[TextBlock])
async def get_text(doc_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    # Para PoC: devolvemos un único bloque de texto plano si existe en logs
    from ..models.document import ProcessingLog

    log = (
        db.query(ProcessingLog)
        .filter(ProcessingLog.document_id == doc_id, ProcessingLog.step == "ocr")
        .order_by(ProcessingLog.created_at.desc())
        .first()
    )
    text = ""
    conf = 0.0
    if log and log.payload:
        try:
            data = __import__("json").loads(log.payload)
            text = data.get("text", "")
            conf = data.get("confidence", 0.0)
        except Exception:
            text = ""
            conf = 0.0
    return [TextBlock(page=1, text=text, bbox=None, confidence=conf)]


@router.get("/{doc_id}/insights", response_model=DocumentInsightsResponse)
async def get_insights(doc_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    log = (
        db.query(ProcessingLog)
        .filter(ProcessingLog.document_id == doc_id, ProcessingLog.step == "insights")
        .order_by(ProcessingLog.created_at.desc())
        .first()
    )
    if not log or not log.payload:
        return DocumentInsightsResponse()

    try:
        payload = json.loads(log.payload)
    except ValueError:
        payload = {}

    return DocumentInsightsResponse(
        compliance=payload.get("compliance") or [],
        spellcheck=payload.get("spellcheck") or [],
        recommendations=payload.get("recommendations") or [],
    )
