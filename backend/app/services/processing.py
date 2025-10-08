import time
import uuid
import json
from sqlalchemy.orm import Session
from ..models.document import Document, Entity, Keyword, ProcessingLog


# PoC: OCR/NLP stub. Reemplazar por integración real (PaddleOCR, spaCy, YAKE...)


def process_document_sync(db: Session, doc: Document) -> None:
    start = time.time()

    # 1) OCR (stub)
    ocr_text = (
        "Demostración de OCR. Documento de importación/exportación con INCOTERM FOB, HS CODE 847130, "
        "contenedor ABCD1234567 y BL BL123456789. Monto 12,345.67 USD."
    )
    ocr_conf = 0.88
    _save_log(
        db,
        doc.id,
        "ocr",
        {"text": ocr_text, "confidence": ocr_conf},
        success=True,
        start=start,
    )

    # 2) NLP/Extracción (reglas mínimas)
    entities = [
        ("incoterm", "FOB", 0.95),
        ("hs_code", "847130", 0.9),
        ("container", "ABCD1234567", 0.92),
        ("bl_number", "BL123456789", 0.9),
        ("currency", "USD", 0.85),
        ("amount", "12345.67", 0.8),
    ]
    for etype, value, score in entities:
        e = Entity(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            type=etype,
            value=value,
            confidence=score,
            page=1,
        )
        db.add(e)

    # 3) Keywords (stub)
    kws = [
        ("incoterm FOB", 0.8),
        ("HS CODE 847130", 0.75),
        ("Bill of Lading", 0.7),
    ]
    for kw, score in kws:
        db.add(
            Keyword(id=str(uuid.uuid4()), document_id=doc.id, keyword=kw, score=score)
        )

    db.commit()

    _save_log(
        db,
        doc.id,
        "nlp",
        {"entities": len(entities), "keywords": len(kws)},
        success=True,
        start=start,
    )


def _save_log(
    db: Session, doc_id: str, step: str, payload: dict, success: bool, start: float
):
    log = ProcessingLog(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        step=step,
        payload=json.dumps(payload),
        success=1 if success else 0,
        duration_ms=int((time.time() - start) * 1000),
    )
    db.add(log)
    db.commit()
