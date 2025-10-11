import json
import re
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..models.document import Document, Entity, Keyword, ProcessingLog

# Intentar importaciones opcionales para OCR/PDF -> no fallar si falta la dependencia
try:
    import PyPDF2
except Exception:
    PyPDF2 = None

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    # pdf2image puede ayudar a rasterizar PDFs cuando PyPDF2 no consigue texto
    from pdf2image import convert_from_path
except Exception:
    convert_from_path = None

import shutil
import logging

logger = logging.getLogger(__name__)

# Detectar si los comandos de sistema están disponibles (Tesseract y Poppler)
TESSERACT_CMD = shutil.which("tesseract")
POPPLER_CMD = shutil.which("pdftoppm") or shutil.which("pdfinfo")
TESSERACT_AVAILABLE = pytesseract is not None and TESSERACT_CMD is not None
POPPLER_AVAILABLE = convert_from_path is not None and POPPLER_CMD is not None


def check_system_dependencies() -> dict:
    """Retorna un dict con la disponibilidad de herramientas de sistema.

    Useful for health checks or for developer diagnostics.
    """
    return {
        "pytesseract_installed": pytesseract is not None,
        "tesseract_cmd": TESSERACT_CMD,
        "tesseract_available": TESSERACT_AVAILABLE,
        "pdf2image_installed": convert_from_path is not None,
        "poppler_cmd": POPPLER_CMD,
        "poppler_available": POPPLER_AVAILABLE,
        "PyPDF2_installed": PyPDF2 is not None,
    }


# PoC: OCR/NLP stub reemplazado con heurísticas simples basadas en texto.

DEFAULT_OCR_TEXT = (
    "Demostración de OCR. Documento de importación/exportación con INCOTERM FOB, HS CODE 847130, "
    "contenedor ABCD1234567 y BL BL123456789. Monto 12,345.67 USD."
)

SPANISH_STOPWORDS = {
    "de",
    "la",
    "el",
    "los",
    "las",
    "y",
    "en",
    "del",
    "para",
    "con",
    "por",
    "una",
    "un",
    "es",
    "al",
    "lo",
    "se",
    "como",
    "más",
    "o",
    "su",
    "sus",
    "ya",
    "sin",
    "sobre",
    "entre",
    "esta",
    "este",
    "son",
    "pero",
    "también",
}

ENGLISH_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "from",
    "this",
    "are",
    "was",
    "have",
    "not",
    "you",
    "your",
    "our",
    "about",
    "into",
    "after",
}

STOPWORDS = SPANISH_STOPWORDS | ENGLISH_STOPWORDS

ENTITY_KEYWORD_LABELS: Dict[str, str] = {
    "incoterm": "INCOTERM",
    "hs_code": "HS CODE",
    "container": "CONTENEDOR",
    "bl_number": "BL",
    "amount": "MONTO",
    "currency": "MONEDA",
}


def process_document_sync(db: Session, doc: Document) -> None:
    start = time.time()

    # 1) OCR (heurística básica/lectura de texto almacenado)
    ocr_text = _read_text_from_storage(doc)
    if not ocr_text.strip():
        ocr_text = DEFAULT_OCR_TEXT
        ocr_conf = 0.82
    else:
        ocr_conf = _estimate_confidence(ocr_text)

    doc.language_detected = _detect_language(ocr_text)

    # Detectar tipo de documento básico si no viene asignado
    if not getattr(doc, "doc_type", None):
        doc_type_guess = _detect_document_type(ocr_text)
        if doc_type_guess:
            doc.doc_type = doc_type_guess

    _save_log(
        db,
        doc.id,
        "ocr",
        {"text": ocr_text, "confidence": ocr_conf},
        success=True,
        start=start,
    )

    # Limpieza de entidades/keywords previas en caso de reprocesar
    db.execute(delete(Entity).where(Entity.document_id == doc.id))
    db.execute(delete(Keyword).where(Keyword.document_id == doc.id))
    db.commit()

    # 2) NLP/Extracción (reglas simples)
    entity_payloads = _detect_entities(ocr_text)
    for payload in entity_payloads:
        db.add(
            Entity(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                type=payload["type"],
                value=payload["value"],
                confidence=payload["confidence"],
                page=payload.get("page", 1),
            )
        )

    # 3) Keywords dinámicas basadas en texto
    keyword_payloads = _extract_keywords(ocr_text, entity_payloads)
    for keyword, score in keyword_payloads:
        db.add(
            Keyword(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                keyword=keyword,
                score=score,
            )
        )

    doc.status = "done"
    db.commit()

    _save_log(
        db,
        doc.id,
        "nlp",
        {
            "entities": len(entity_payloads),
            "keywords": [kw for kw, _ in keyword_payloads],
        },
        success=True,
        start=start,
    )

    # Registrar advertencias sobre campos faltantes que el frontend deberá mostrar
    required = ["incoterm", "hs_code", "container", "doc_type"]
    present = {e["type"] for e in entity_payloads}
    missing = [
        r
        for r in required
        if r not in present and not (r == "doc_type" and getattr(doc, "doc_type", None))
    ]
    if missing:
        _save_log(
            db, doc.id, "warnings", {"missing": missing}, success=True, start=start
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


def _read_text_from_storage(doc: Document) -> str:
    path = Path(doc.storage_path or "")
    if not path.exists() or path.is_dir():
        return ""
    try:
        # Lectura directa de archivos de texto
        if doc.mime and doc.mime.startswith("text/"):
            return path.read_text(encoding="utf-8", errors="ignore")
        if doc.mime in {"application/json", "application/xml"}:
            return path.read_text(encoding="utf-8", errors="ignore")

        # Si es PDF, intentar extraer texto con PyPDF2 (si está disponible)
        if doc.mime == "application/pdf" or path.suffix.lower() == ".pdf":
            if PyPDF2 is not None:
                try:
                    text_parts = []
                    with open(path, "rb") as fh:
                        reader = PyPDF2.PdfReader(fh)
                        for p in reader.pages:
                            try:
                                text_parts.append(p.extract_text() or "")
                            except Exception:
                                # salto si la página no tiene texto extraíble
                                continue
                    joined = "\n".join(text_parts).strip()
                    if joined:
                        return joined
                except Exception:
                    pass

            # Si no hay texto directo o PyPDF2 no está, intentar rasterizar y OCR
            if (
                convert_from_path is not None
                and Image is not None
                and pytesseract is not None
            ):
                try:
                    images = convert_from_path(str(path), dpi=200)
                    page_texts = []
                    for img in images:
                        page_texts.append(
                            pytesseract.image_to_string(img, lang="spa+eng")
                        )
                    joined = "\n".join(page_texts).strip()
                    if joined:
                        return joined
                except Exception:
                    pass
    except OSError:
        return ""
    # Si es imagen, intentar OCR con Pillow + pytesseract
    try:
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}:
            if Image is not None and pytesseract is not None:
                try:
                    img = Image.open(path)
                    text = pytesseract.image_to_string(img, lang="spa+eng")
                    return text or ""
                except Exception:
                    return ""
    except Exception:
        return ""

    return ""


def _detect_language(text: str) -> str:
    lowered = text.lower()
    spanish_pattern = r"\b(el|la|de|los|para)\b"
    english_pattern = r"\b(the|and|of|for|with)\b"
    spanish_hits = len(re.findall(spanish_pattern, lowered))
    english_hits = len(re.findall(english_pattern, lowered))
    if spanish_hits == english_hits == 0:
        return "und"
    return "es" if spanish_hits >= english_hits else "en"


def _estimate_confidence(text: str) -> float:
    tokens = re.findall(r"\w+", text)
    if not tokens:
        return 0.5
    long_tokens = [token for token in tokens if len(token) > 3]
    ratio = len(long_tokens) / len(tokens)
    return max(0.6, min(0.95, 0.7 + ratio * 0.2))


def _detect_entities(text: str) -> List[Dict[str, object]]:
    results: List[Dict[str, object]] = []
    lowered = text.lower()
    # Detectar Incoterm (con tolerancia a errores OCR comunes)
    incoterms = [
        "fob",
        "cif",
        "cfr",
        "exw",
        "ddp",
        "dap",
        "dpu",
        "fca",
        "fas",
        "dat",
        "cip",
    ]
    incoterm_match = None
    # 1) búsqueda directa
    incoterm_pattern = r"\b(" + "|".join(incoterms) + r")\b"
    incoterm_match = re.search(incoterm_pattern, lowered)
    # 2) label-based: 'incoterm: FOB'
    if not incoterm_match:
        m = re.search(r"incoterm[s]?[:\s]*([A-Za-z0-9]{3,4})\b", text, re.IGNORECASE)
        if m:
            candidate = m.group(1).upper()
            # normalizar errores comunes (0 -> O, 1 -> I)
            candidate_norm = candidate.replace("0", "O").replace("1", "I")
            if candidate_norm.lower() in incoterms:
                incoterm_match = True
                results.append(
                    {"type": "incoterm", "value": candidate_norm, "confidence": 0.9}
                )
    if incoterm_match and not any(r["type"] == "incoterm" for r in results):
        # si incoterm encontrada por patrón directo
        if hasattr(incoterm_match, "group"):
            results.append(
                {
                    "type": "incoterm",
                    "value": incoterm_match.group(1).upper(),
                    "confidence": 0.92,
                }
            )

    # HS code: prefer label-based, fallback a números largos
    hs_match = re.search(r"(?:hs\s*code|c[oó]digo\s*hs)[^0-9]*(\d{4,10})", lowered)
    if hs_match:
        results.append(
            {"type": "hs_code", "value": hs_match.group(1), "confidence": 0.9}
        )
    else:
        # fallback: buscar el primer número de 6 a 10 dígitos (más probable HS)
        hs_fallback = re.search(r"\b(\d{6,10})\b", text)
        if hs_fallback:
            results.append(
                {"type": "hs_code", "value": hs_fallback.group(1), "confidence": 0.6}
            )

    # Contenedor ISO: 4 letras + 7 dígitos
    container_match = re.search(r"\b([A-Za-z]{4}\d{7})\b", text)
    if container_match:
        results.append(
            {
                "type": "container",
                "value": container_match.group(1).upper(),
                "confidence": 0.88,
            }
        )

    bl_match = re.search(r"\b(?:bl|bill\s+of\s+lading)[:\-\s]*([a-z0-9-]+)\b", lowered)
    if bl_match:
        results.append(
            {
                "type": "bl_number",
                "value": bl_match.group(1).upper(),
                "confidence": 0.86,
            }
        )

    currency_match = re.search(r"\b(usd|eur|mxn|cop|clp|pen|ars|brl)\b", lowered)
    if currency_match:
        results.append(
            {
                "type": "currency",
                "value": currency_match.group(1).upper(),
                "confidence": 0.8,
            }
        )

    # Try US/international format: 1,234.56
    amount_match_us = re.search(
        r"\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b",
        text,
    )
    # Try European format: 1.234,56
    amount_match_eu = re.search(
        r"\b\d{1,3}(?:\.\d{3})*(?:,\d{2})?\b",
        text,
    )
    if amount_match_us:
        amount_raw = amount_match_us.group(0)
        # Remove thousands separators, convert decimal point to dot
        normalized_amount = amount_raw.replace(",", "").replace(" ", "")
        results.append(
            {
                "type": "amount",
                "value": normalized_amount,
                "confidence": 0.78,
            }
        )
    elif amount_match_eu:
        amount_raw = amount_match_eu.group(0)
        # Remove thousands separators, convert decimal comma to dot
        normalized_amount = (
            amount_raw.replace(".", "").replace(",", ".").replace(" ", "")
        )
        results.append(
            {
                "type": "amount",
                "value": normalized_amount,
                "confidence": 0.78,
            }
        )

    return results


def _extract_keywords(
    text: str, entities: Sequence[Dict[str, object]], max_keywords: int = 8
) -> List[Tuple[str, float]]:
    cleaned = re.sub(r"[\n\r]+", " ", text)
    words = re.findall(r"\b\w+\b", cleaned.lower())
    single_terms = [
        word
        for word in words
        if len(word) > 2 and word not in STOPWORDS and not word.isdigit()
    ]
    single_counter = Counter(single_terms)

    bigrams: List[str] = []
    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i + 1]
        if (
            len(w1) > 2
            and len(w2) > 2
            and w1 not in STOPWORDS
            and w2 not in STOPWORDS
            and not w1.isdigit()
            and not w2.isdigit()
        ):
            bigrams.append(f"{w1} {w2}")
    bigram_counter = Counter(bigrams)

    keywords: List[Tuple[str, float]] = []
    seen = set()

    # Priorizar entidades detectadas como keywords directas
    for entity in entities:
        label_key = ENTITY_KEYWORD_LABELS.get(entity["type"], entity["type"].upper())
        keyword_text = f"{label_key} {entity['value']}".strip()
        norm = keyword_text.lower()
        if keyword_text and norm not in seen:
            keywords.append((keyword_text, 1.0))
            seen.add(norm)
            if len(keywords) >= max_keywords:
                return keywords

    if bigram_counter:
        max_bigram = max(bigram_counter.values())
        for phrase, count in bigram_counter.most_common(max_keywords):
            normalized = phrase.lower()
            if normalized in seen:
                continue
            score = max(0.4, min(0.95, count / max_bigram))
            keywords.append((phrase.title(), score))
            seen.add(normalized)
            if len(keywords) >= max_keywords:
                return keywords

    if single_counter:
        max_single = max(single_counter.values())
        for term, count in single_counter.most_common(max_keywords):
            normalized = term.lower()
            if normalized in seen:
                continue
            score = max(0.3, min(0.9, count / max_single))
            keywords.append((term.capitalize(), score))
            seen.add(normalized)
            if len(keywords) >= max_keywords:
                break

    return keywords


def _detect_document_type(text: str) -> str:
    """Heurística mínima para detectar tipo de documento por palabras clave."""
    lowered = text.lower()
    if "invoice" in lowered or "factura" in lowered:
        return "invoice"
    if "bill of lading" in lowered or "bill of lading" in lowered:
        return "bill_of_lading"
    if "packing list" in lowered or "packing" in lowered:
        return "packing_list"
    return ""
