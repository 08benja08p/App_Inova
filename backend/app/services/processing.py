import json
import re
import time
import uuid
import difflib
from collections import Counter
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..models.document import Document, Entity, Keyword, ProcessingLog
from ..services.knowledge import (
    get_document_knowledge,
    get_document_labels,
    get_extraction_schema,
)

# Intentar importaciones opcionales para OCR/PDF -> no fallar si falta la dependencia
try:
    import PyPDF2
except Exception:
    PyPDF2 = None

try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
except Exception:
    pdfminer_extract_text = None

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

EXTRACTION_SCHEMAS = get_extraction_schema()
DOCUMENT_KNOWLEDGE = get_document_knowledge()
DOCUMENT_LABELS = get_document_labels()

CHERRY_HS_CODES = {"080921", "080929", "08092100", "08092900"}
REGULATORY_TERMS = {
    "sag",
    "servicio agr\u00edcola y ganadero",
    "certificado fitosanitario",
    "fumigaci\u00f3n",
    "fumigacion",
    "tratamiento en fr\u00edo",
}
COLD_CHAIN_TERMS = {
    "0\u00b0c",
    "0 c",
    "fr\u00edo",
    "frio",
    "temperatura",
    "cadena de fr\u00edo",
    "precool",
}
PREFERRED_INCOTERMS = {"FOB", "CIF", "CFR"}
PREFERRED_CURRENCIES = {"USD", "EUR"}
SPELLCHECK_TERMS = {
    "cereza": "cereza",
    "cerezas": "cerezas",
    "aduana": "aduana",
    "exportaci\u00f3n": "exportaci\u00f3n",
    "exportacion": "exportaci\u00f3n",
    "importaci\u00f3n": "importaci\u00f3n",
    "importacion": "importaci\u00f3n",
    "sag": "SAG",
    "fumigaci\u00f3n": "fumigaci\u00f3n",
    "fumigacion": "fumigaci\u00f3n",
    "fitosanitario": "fitosanitario",
    "resoluci\u00f3n": "resoluci\u00f3n",
    "resolucion": "resoluci\u00f3n",
    "calibre": "calibre",
    "huerto": "huerto",
    "variedad": "variedad",
    "packing": "packing",
    "pallet": "pallet",
    "temperatura": "temperatura",
    "cadena": "cadena",
    "log\u00edstica": "log\u00edstica",
    "logistica": "log\u00edstica",
    "cosecha": "cosecha",
    "producto": "producto",
    "chile": "Chile",
}

FIELD_HINTS: Dict[str, List[str]] = {
    "numero_factura": ["numero factura", "n\u00b0 factura", "invoice number", "factura no"],
    "exportador": ["exportador", "exporter"],
    "importador": ["importador", "consignee", "importer"],
    "descripcion_mercaderia": ["descripcion", "description", "mercaderia", "goods"],
    "variedad": ["variedad", "variety", "cultivar"],
    "calibre": ["calibre", "caliber", "size"],
    "cantidad_cajas": ["cantidad de cajas", "cajas", "cartons", "boxes"],
    "peso_neto": ["peso neto", "net weight"],
    "peso_bruto": ["peso bruto", "gross weight", "peso total"],
    "hs_code": ["hs code", "codigo hs", "h.s."],
    "incoterm": ["incoterm", "terms", "fob", "cif", "cfr"],
    "valor_total": ["valor total", "total value", "amount due", "fob value"],
    "moneda": ["usd", "eur", "currency", "moneda"],
    "numero_contenedor": ["contenedor", "container", "cntr", "booking"],
    "numero_pallets": ["pallets", "pallet"],
    "numero_cajas": ["cajas", "boxes", "cartons"],
    "codigo_csg": ["csg", "codigo csg"],
    "codigo_csp": ["csp", "codigo csp"],
    "lote": ["lote", "lot"],
    "pais_destino": ["pais destino", "destination country", "destino"],
    "criterio_origen": ["criterio de origen", "origin criterion"],
    "valor_fob": ["valor fob", "fob value"],
    "numero_dus": ["numero dus", "dus", "documento unico salida"],
    "numero_guia": ["guia despacho", "numero guia", "despacho"],
    "especie": ["especie", "species"],
    "cantidad": ["cantidad", "quantity", "qty"],
    "origen": ["origen", "origin"],
    "destino": ["destino", "destination"],
}

DOC_TYPE_KEYWORDS = {
    "factura_comercial": ["factura comercial", "commercial invoice", "invoice"],
    "packing_list": ["packing list", "packing", "lista de empaque", "lista empaque"],
    "bl": ["bill of lading", "bl", "conocimiento de embarque"],
    "certificado_fitosanitario": ["certificado fitosanitario", "phytosanitary certificate", "sag"],
    "certificado_origen": ["certificado de origen", "certificate of origin"],
    "dus": ["dus", "documento unico de salida", "declaracion de exportacion"],
    "guia_despacho": ["guia de despacho", "guia despacho", "despacho sii"],
    "instrucciones_embarque": ["instrucciones de embarque", "shipping instructions"],
}

DOC_TYPE_ALIASES = {
    "invoice": "factura_comercial",
    "factura": "factura_comercial",
    "factura comercial": "factura_comercial",
    "packing": "packing_list",
    "lista de empaque": "packing_list",
    "packing list": "packing_list",
    "bill_of_lading": "bl",
    "bill of lading": "bl",
    "bl": "bl",
    "bill": "bl",
    "co": "certificado_origen",
    "certificado de origen": "certificado_origen",
    "certificado origen": "certificado_origen",
    "certificado fitosanitario": "certificado_fitosanitario",
    "fitosanitario": "certificado_fitosanitario",
    "sag": "certificado_fitosanitario",
    "guia": "guia_despacho",
    "guia despacho": "guia_despacho",
    "dus": "dus",
    "documento unico de salida": "dus",
    "instrucciones de embarque": "instrucciones_embarque",
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

    # Detectar y normalizar tipo de documento
    normalized_doc_type = _normalize_doc_type(getattr(doc, "doc_type", ""))
    if not normalized_doc_type:
        doc_type_guess = _detect_document_type(ocr_text)
        normalized_doc_type = _normalize_doc_type(doc_type_guess)
    if normalized_doc_type:
        doc.doc_type = normalized_doc_type

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
    legacy_missing_issues: List[Dict[str, str]] = []
    if missing:
        _save_log(
            db, doc.id, "warnings", {"missing": missing}, success=True, start=start
        )
        for field in missing:
            legacy_missing_issues.append(
                {
                    "severity": "warning",
                    "title": f"Campo no detectado: {field}",
                    "detail": "Complementa este valor manualmente para completar la revisión.",
                    "field": field,
                }
            )

    schema_issues = _evaluate_schema_requirements(ocr_text, normalized_doc_type)
    compliance_issues = _evaluate_cherry_compliance(ocr_text, entity_payloads, doc)
    combined_compliance = schema_issues + legacy_missing_issues + compliance_issues
    spellcheck_issues = _detect_spelling_issues(ocr_text)
    recommendations = _generate_recommendations(
        combined_compliance, spellcheck_issues, entity_payloads, doc
    )
    recommendations.extend(_knowledge_recommendations(normalized_doc_type))
    recommendations = _deduplicate_strings(recommendations)

    insights_payload = {
        "compliance": combined_compliance,
        "spellcheck": spellcheck_issues,
        "recommendations": recommendations,
    }
    _save_log(
        db,
        doc.id,
        "insights",
        insights_payload,
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


def _evaluate_cherry_compliance(
    text: str, entities: Sequence[Dict[str, object]], doc: Document
) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    normalized = text.casefold()
    hs_code = _first_entity_value(entities, "hs_code")
    if not hs_code:
        issues.append(
            {
                "severity": "warning",
                "title": "HS Code faltante",
                "detail": "Agrega el HS Code 08092900 correspondiente a cerezas frescas.",
                "field": "hs_code",
            }
        )
    elif not any(hs_code.startswith(code) for code in CHERRY_HS_CODES):
        issues.append(
            {
                "severity": "error",
                "title": "HS Code no corresponde a cerezas",
                "detail": f"Se detect\u00f3 el c\u00f3digo {hs_code}, revisa que sea 08092900.",
                "field": "hs_code",
            }
        )

    if "cereza" not in normalized and "cerezas" not in normalized:
        issues.append(
            {
                "severity": "warning",
                "title": "Producto no identificado",
                "detail": "El texto no menciona la palabra 'cerezas', agr\u00e9gala en la descripci\u00f3n.",
                "field": "product",
            }
        )

    if not _contains_keywords(normalized, REGULATORY_TERMS):
        issues.append(
            {
                "severity": "warning",
                "title": "Referencia SAG ausente",
                "detail": "Incluye la referencia al certificado SAG o tratamiento fitosanitario.",
                "field": "sag",
            }
        )

    if not _contains_keywords(normalized, COLD_CHAIN_TERMS):
        issues.append(
            {
                "severity": "warning",
                "title": "Cadena de fr\u00edo no descrita",
                "detail": "Describe temperatura objetivo o tratamiento en fr\u00edo en el documento.",
                "field": "temperature",
            }
        )

    incoterm_value = _first_entity_value(entities, "incoterm").upper()
    if incoterm_value and incoterm_value not in PREFERRED_INCOTERMS:
        issues.append(
            {
                "severity": "warning",
                "title": "Incoterm poco habitual",
                "detail": f"El incoterm {incoterm_value} no es el m\u00e1s usado en fruta fresca (FOB/CIF/CFR).",
                "field": "incoterm",
            }
        )
    elif not incoterm_value:
        issues.append(
            {
                "severity": "warning",
                "title": "Incoterm no detectado",
                "detail": "Confirma el incoterm negociado para la operaci\u00f3n.",
                "field": "incoterm",
            }
        )

    container_value = _first_entity_value(entities, "container")
    if doc and getattr(doc, "doc_type", "") in {"packing_list", "bl"}:
        if not container_value:
            issues.append(
                {
                    "severity": "warning",
                    "title": "N\u00famero de contenedor faltante",
                    "detail": "El packing list debe informar el contenedor o booking asociado.",
                    "field": "container",
                }
            )

    bl_value = _first_entity_value(entities, "bl_number")
    if doc and getattr(doc, "doc_type", "") == "bl" and not bl_value:
        issues.append(
            {
                "severity": "warning",
                "title": "BL sin n\u00famero",
                "detail": "Completa el Bill of Lading con el identificador oficial.",
                "field": "bl_number",
            }
        )

    currency_value = _first_entity_value(entities, "currency").upper()
    if not currency_value:
        issues.append(
            {
                "severity": "warning",
                "title": "Moneda no indicada",
                "detail": "Especifica la moneda (USD/EUR) en el documento comercial.",
                "field": "currency",
            }
        )
    elif currency_value not in PREFERRED_CURRENCIES:
        issues.append(
            {
                "severity": "warning",
                "title": "Moneda poco frecuente",
                "detail": f"La moneda {currency_value} no es la habitual para cerezas chilenas.",
                "field": "currency",
            }
        )

    return issues


def _evaluate_schema_requirements(text: str, doc_type: str) -> List[Dict[str, str]]:
    if not doc_type:
        return []
    schema = EXTRACTION_SCHEMAS.get(doc_type)
    if not schema:
        return []
    normalized_text = text.casefold()
    issues: List[Dict[str, str]] = []
    for field in schema.get("fields", []):
        if not field.get("required"):
            continue
        field_name = field.get("name", "")
        if not field_name or _field_in_text(normalized_text, field_name):
            continue
        label = field_name.replace("_", " ")
        issues.append(
            {
                "severity": "warning",
                "title": f"Campo esperado: {label}",
                "detail": f"No se encontró referencia al campo \"{label}\" en el documento.",
                "field": field_name,
            }
        )
    return issues


def _field_in_text(normalized_text: str, field_name: str) -> bool:
    if not normalized_text or not field_name:
        return False
    hints = FIELD_HINTS.get(field_name, [])
    if not hints:
        hints = [field_name.replace("_", " ")]
    for hint in hints:
        if not hint:
            continue
        if hint.casefold() in normalized_text:
            return True
    return False


def _contains_keywords(normalized_text: str, keywords: Sequence[str]) -> bool:
    return any(keyword.casefold() in normalized_text for keyword in keywords)


def _first_entity_value(
    entities: Sequence[Dict[str, object]], entity_type: str
) -> str:
    for entity in entities:
        if entity.get("type") == entity_type:
            value = entity.get("value")
            if value is None:
                continue
            return str(value)
    return ""


def _detect_spelling_issues(text: str) -> List[Dict[str, str]]:
    matches = re.findall(r"[A-Za-z\u00c0-\u017f]{4,}", text or "")
    dictionary = {key.casefold(): value for key, value in SPELLCHECK_TERMS.items()}
    dictionary_keys = list(dictionary.keys())
    seen: set[str] = set()
    issues: List[Dict[str, str]] = []
    for token in matches:
        lowered = token.casefold()
        if lowered in seen or lowered in dictionary:
            continue
        suggestion = difflib.get_close_matches(lowered, dictionary_keys, n=1, cutoff=0.86)
        if suggestion:
            canonical = dictionary[suggestion[0]]
            issues.append(
                {
                    "severity": "warning",
                    "title": "Posible falta ortogr\u00e1fica",
                    "detail": f'"{token}" podr\u00eda ser "{canonical}".',
                    "field": "texto",
                }
            )
            seen.add(lowered)
        if len(issues) >= 8:
            break
    return issues


def _generate_recommendations(
    compliance: Sequence[Dict[str, str]],
    spelling: Sequence[Dict[str, str]],
    entities: Sequence[Dict[str, object]],
    doc: Document,
) -> List[str]:
    recommendations: List[str] = []
    indexed = {issue.get("field"): issue for issue in compliance if issue.get("field")}

    if "hs_code" in indexed:
        recommendations.append(
            "Ajusta el HS Code a 08092900 en factura, DUS y packing list."
        )
    if "product" in indexed:
        recommendations.append(
            "Incluye la descripci\u00f3n \"cerezas frescas\" en el producto principal."
        )
    if "sag" in indexed:
        recommendations.append(
            "Agrega la referencia al certificado SAG o n\u00famero de resoluci\u00f3n fitosanitaria."
        )
    if "temperature" in indexed:
        recommendations.append(
            "Documenta la temperatura objetivo (0\u00b0C) o el tratamiento en fr\u00edo indicado por SAG."
        )
    if "incoterm" in indexed:
        recommendations.append(
            "Confirma el incoterm (FOB/CIF/CFR) en cabecera y pie del documento."
        )
    if "container" in indexed:
        recommendations.append(
            "Relaciona el n\u00famero de contenedor con el lote de cerezas en el packing list."
        )
    if "currency" in indexed:
        recommendations.append(
            "Expresa los valores en USD o EUR, como exige la mayor\u00eda de los contratos."
        )

    if spelling:
        recommendations.append(
            "Corrige los t\u00e9rminos marcados para evitar observaciones por ortograf\u00eda."
        )

    amount_value = _first_entity_value(entities, "amount")
    if amount_value and "currency" not in indexed:
        recommendations.append(
            "Incluye el tipo de moneda junto al monto declarado para facilitar auditor\u00eda."
        )

    if not recommendations:
        doc_label = getattr(doc, "doc_type", "") or "documento"
        recommendations.append(
            f"Valida que el {doc_label} incluya certificados, lotes y datos log\u00edsticos antes del env\u00edo."
        )
    return recommendations[:8]


def _knowledge_recommendations(doc_type: str) -> List[str]:
    info = DOCUMENT_KNOWLEDGE.get(doc_type)
    if not info:
        return []
    recs: List[str] = []
    for cross in info.get("cross_checks", []) or []:
        target = cross.get("against")
        fields = cross.get("fields") or []
        if not target or not fields:
            continue
        label = DOCUMENT_LABELS.get(target, target.replace("_", " "))
        recs.append(
            f"Verifica {', '.join(fields)} contra {label} para asegurar consistencia."
        )
    for error in info.get("common_errors", [])[:3]:
        recs.append(f"Revisa: {error}.")
    return recs


def _normalize_doc_type(doc_type: str) -> str:
    value = (doc_type or "").strip().lower()
    if not value:
        return ""
    if value in DOC_TYPE_ALIASES:
        return DOC_TYPE_ALIASES[value]
    if value in EXTRACTION_SCHEMAS or value in DOC_TYPE_KEYWORDS:
        return value
    return ""


def _deduplicate_strings(items: Sequence[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in items:
        if not item:
            continue
        normalized = item.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(item)
    return result


def _extract_pdf_text(path: Path) -> str:
    """Obtiene texto de un PDF usando PyPDF2 o pdfminer (si están disponibles)."""
    if PyPDF2 is not None:
        try:
            text_parts = []
            with open(path, "rb") as fh:
                reader = PyPDF2.PdfReader(fh)
                for page in reader.pages:
                    try:
                        text_parts.append(page.extract_text() or "")
                    except Exception:
                        continue
            joined = "\n".join(text_parts).strip()
            if joined:
                return joined
        except Exception:
            pass
    if pdfminer_extract_text is not None:
        try:
            text = pdfminer_extract_text(str(path))
            if text and text.strip():
                return text.strip()
        except Exception:
            pass
    return ""


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

        # Si es PDF, intentar extraer texto con los motores disponibles
        if doc.mime == "application/pdf" or path.suffix.lower() == ".pdf":
            pdf_text = _extract_pdf_text(path)
            if pdf_text:
                return pdf_text
            # Si no hay texto directo recurrimos a rasterizar y OCR
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
    for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return doc_type
    if "invoice" in lowered or "factura" in lowered:
        return "factura_comercial"
    if "bill of lading" in lowered:
        return "bl"
    if "packing list" in lowered or "packing" in lowered:
        return "packing_list"
    return ""
