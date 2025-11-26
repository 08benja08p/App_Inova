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
    "numero_factura": [
        "numero factura",
        "n\u00b0 factura",
        "invoice number",
        "factura no",
    ],
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
    "certificado_fitosanitario": [
        "certificado fitosanitario",
        "phytosanitary certificate",
        "sag",
    ],
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

# Mapeo de archivos demo a sus templates HTML para la PoC
# Los archivos "*_real.html" usan datos reales de Exportadora San Andrés SpA
# Los archivos "*_error.html" incluyen discrepancias detectables para demostrar validación
DEMO_HTML_MAPPING = {
    # ===== ESCENARIO 1: Embarque SA1690CZ (Hong Kong, marítimo, 7080 cajas) =====
    # NOTA: La factura apunta a la versión con errores para demostrar detección
    # El resto de documentos (BL, DUS) son correctos para validación cruzada
    "FACTURA TRIBUTARIA N°5873 SA1690CZ.pdf": "demo_factura_5873_error.html",
    "BL ONEYSCLE33614900.pdf": "demo_bl_sa1690_real.html",
    "DUS 12497436-4.pdf": "demo_dus_sa1690_real.html",
    # Fitosanitario del embarque SA1690CZ (cert 2629954 - no tenemos HTML aún)
    # ===== ESCENARIO 2: Embarque SA1704CZ (Curazao, aéreo, 120 cajas) =====
    "FITO 2630187.pdf": "demo_fito_2630187_real.html",
    "FACTURA TRIBUTARIA N°5861 SA1704CZ.pdf": "demo_invoice_reconstructed.html",  # Legacy
    # ===== DEMOS CON ERRORES (para demostrar detección de discrepancias) =====
    "demo_factura_error.pdf": "demo_factura_5873_error.html",
    "demo_fito_error.pdf": "demo_fito_2630187_error.html",
    # Legacy error demos
    "demo_error_fito.pdf": "demo_fito_error_reconstructed.html",
    "demo_error_bl.pdf": "demo_bl_error_reconstructed.html",
    "demo_error_dus.pdf": "demo_dus_error_reconstructed.html",
    # ===== HTML FILES DIRECTLY (when uploading .html files) =====
    "demo_factura_5873_error.html": "demo_factura_5873_error.html",
    "demo_factura_5873_real.html": "demo_factura_5873_real.html",
    "demo_bl_sa1690_real.html": "demo_bl_sa1690_real.html",
    "demo_bl_error_reconstructed.html": "demo_bl_error_reconstructed.html",
    "demo_dus_sa1690_real.html": "demo_dus_sa1690_real.html",
    "demo_dus_error_reconstructed.html": "demo_dus_error_reconstructed.html",
    "demo_fito_2630187_real.html": "demo_fito_2630187_real.html",
    "demo_fito_2630187_error.html": "demo_fito_2630187_error.html",
    "demo_fito_error_reconstructed.html": "demo_fito_error_reconstructed.html",
    "demo_invoice_reconstructed.html": "demo_invoice_reconstructed.html",
    "demo_packing_list_reconstructed.html": "demo_packing_list_reconstructed.html",
    "demo_bl_real_reconstructed.html": "demo_bl_real_reconstructed.html",
    "demo_dus_real_reconstructed.html": "demo_dus_real_reconstructed.html",
    "demo_fito_real_reconstructed.html": "demo_fito_real_reconstructed.html",
}

# Entidades hardcodeadas para demos - datos reales de Exportadora San Andrés SpA
DEMO_ENTITIES = {
    # Factura 5873 - Embarque SA1690CZ a Hong Kong
    "demo_factura_5873_real.html": [
        {"type": "shipper", "value": "Exportadora San Andrés SpA", "confidence": 0.99},
        {
            "type": "consignee",
            "value": "Jumbo Top Trading Shenzhen Company Limited",
            "confidence": 0.98,
        },
        {"type": "incoterm", "value": "CFR", "confidence": 0.95},
        {"type": "amount", "value": "177,000.00", "confidence": 0.99},
        {"type": "currency", "value": "USD", "confidence": 0.99},
        {"type": "net_weight", "value": "21,240.00 kg", "confidence": 0.95},
        {"type": "gross_weight", "value": "22,132.80 kg", "confidence": 0.95},
        {"type": "container", "value": "ONEU9254131", "confidence": 0.98},
        {"type": "hs_code", "value": "08092000", "confidence": 0.95},
    ],
    "demo_factura_5873_error.html": [
        {"type": "shipper", "value": "Exportadora San Andrés SpA", "confidence": 0.99},
        {
            "type": "consignee",
            "value": "Jumbo Top Trading Shenzhen Company Limited",
            "confidence": 0.98,
        },
        {"type": "incoterm", "value": "CFR", "confidence": 0.95},
        {"type": "amount", "value": "177,000.00", "confidence": 0.99},
        {"type": "currency", "value": "USD", "confidence": 0.99},
        {
            "type": "net_weight",
            "value": "21,100.00 kg",
            "confidence": 0.95,
        },  # Error: distinto al BL
        {
            "type": "gross_weight",
            "value": "22,000.00 kg",
            "confidence": 0.95,
        },  # Error: distinto al BL
        {"type": "container", "value": "ONEU9254131", "confidence": 0.98},
        {"type": "hs_code", "value": "08092000", "confidence": 0.95},
    ],
    # BL ONEYSCLE33614900 - Embarque SA1690CZ
    "demo_bl_sa1690_real.html": [
        {"type": "shipper", "value": "Exportadora San Andrés SpA", "confidence": 0.99},
        {
            "type": "consignee",
            "value": "Jumbo Top Trading Shenzhen Company Limited",
            "confidence": 0.98,
        },
        {"type": "bl_number", "value": "ONEYSCLE33614900", "confidence": 0.99},
        {"type": "container", "value": "ONEU9254131", "confidence": 0.98},
        {"type": "vessel", "value": "ONE STORK", "confidence": 0.95},
        {"type": "port_loading", "value": "Valparaíso", "confidence": 0.95},
        {"type": "port_discharge", "value": "Hong Kong", "confidence": 0.95},
        {"type": "gross_weight", "value": "22,132.80 kg", "confidence": 0.95},
        {"type": "net_weight", "value": "21,240.00 kg", "confidence": 0.95},
    ],
    # DUS 12497436-4 - Embarque SA1690CZ
    "demo_dus_sa1690_real.html": [
        {"type": "shipper", "value": "Exportadora San Andrés SpA", "confidence": 0.99},
        {"type": "dus_number", "value": "12497436-4", "confidence": 0.99},
        {"type": "hs_code", "value": "08092000", "confidence": 0.95},
        {"type": "gross_weight", "value": "22,132.80 kg", "confidence": 0.95},
        {"type": "incoterm", "value": "CFR", "confidence": 0.95},
        {"type": "amount", "value": "177,000.00", "confidence": 0.99},
        {"type": "currency", "value": "USD", "confidence": 0.99},
        {"type": "destination", "value": "Hong Kong", "confidence": 0.95},
    ],
    # Fito 2630187 - Embarque SA1704CZ a Curazao
    "demo_fito_2630187_real.html": [
        {"type": "shipper", "value": "Exportadora San Andrés SpA", "confidence": 0.99},
        {"type": "consignee", "value": "Centrum Supermarket", "confidence": 0.98},
        {"type": "phyto_cert", "value": "2630187", "confidence": 0.99},
        {"type": "species", "value": "PRUNUS AVIUM", "confidence": 0.98},
        {"type": "net_weight", "value": "360.00 kg", "confidence": 0.95},
        {"type": "destination", "value": "Curazao", "confidence": 0.95},
    ],
    "demo_fito_2630187_error.html": [
        {"type": "shipper", "value": "Exportadora San Andrés SpA", "confidence": 0.99},
        {"type": "consignee", "value": "Centrum Supermarket", "confidence": 0.98},
        {"type": "phyto_cert", "value": "2630187", "confidence": 0.99},
        {"type": "species", "value": "PRUNUS AVIUM", "confidence": 0.98},
        {
            "type": "net_weight",
            "value": "350.00 kg",
            "confidence": 0.95,
        },  # Discrepancia
        {"type": "destination", "value": "Curazao", "confidence": 0.95},
    ],
}

# Escenarios de validación hardcodeados para la demo
# Datos reales de Exportadora San Andrés SpA
DEMO_SCENARIOS = {
    # ========== ESCENARIOS "LIMPIOS" (Sin errores - Real) ==========
    # Embarque SA1690CZ: Hong Kong, marítimo, 7080 cajas cerezas
    # NOTA: La factura PDF ahora muestra errores para demo de detección
    "FACTURA TRIBUTARIA N°5873 SA1690CZ.pdf": {
        "compliance": [
            {
                "severity": "error",
                "title": "Discrepancia en cantidad de cajas",
                "detail": "Factura indica 7,000 cajas pero BL registra 7,080 cajas.",
                "field": "quantity",
            },
            {
                "severity": "error",
                "title": "Peso bruto no coincide",
                "detail": "Factura: 21,500 KG vs BL/DUS: 22,132.80 KG.",
                "field": "weight",
            },
            {
                "severity": "warning",
                "title": "Valor FOB requiere verificación",
                "detail": "El valor declarado USD 75,600 difiere del calculado USD 76,320.",
                "field": "amount",
            },
        ],
        "recommendations": [
            "Corregir cantidad de cajas a 7,080 para coincidir con BL.",
            "Actualizar peso bruto a 22,132.80 KG.",
            "Verificar cálculo del valor FOB.",
        ],
    },
    "BL ONEYSCLE33614900.pdf": {
        "compliance": [],
        "recommendations": [
            "Bill of Lading verificado.",
            "Contenedor ONEU9254131 coincide con factura y packing list.",
        ],
    },
    "DUS 12497436-4.pdf": {
        "compliance": [],
        "recommendations": [
            "DUS validado contra factura comercial.",
            "Peso bruto 22,132.80 KG coincide con documentos de embarque.",
        ],
    },
    # Embarque SA1704CZ: Curazao, aéreo, 120 cajas cerezas
    "FITO 2630187.pdf": {
        "compliance": [],
        "recommendations": [
            "Certificado fitosanitario válido para exportación a Curazao.",
            "Especie PRUNUS AVIUM (cerezas) correctamente declarada.",
        ],
    },
    "FACTURA TRIBUTARIA N°5861 SA1704CZ.pdf": {
        "compliance": [],
        "recommendations": [],
    },
    # Archivos HTML directos (Clean)
    "demo_invoice_reconstructed.html": {"compliance": [], "recommendations": []},
    "demo_packing_list_reconstructed.html": {"compliance": [], "recommendations": []},
    "demo_factura_5873_real.html": {"compliance": [], "recommendations": []},
    "demo_bl_sa1690_real.html": {"compliance": [], "recommendations": []},
    "demo_dus_sa1690_real.html": {"compliance": [], "recommendations": []},
    "demo_fito_2630187_real.html": {"compliance": [], "recommendations": []},
    # ========== ESCENARIOS "ERROR" (Con discrepancias detectadas) ==========
    # NOTA: severity="suggestion" indica que se debe verificar contra otro documento
    # Si el documento de referencia está subido, el frontend lo cambiará a "error"
    # Factura con discrepancias vs BL/DUS
    "demo_factura_error.pdf": {
        "compliance": [
            {
                "severity": "suggestion",
                "title": "Verificar cantidad de cajas",
                "detail": "Sugerencia: verificar cantidad de cajas contra BL.",
                "field": "quantity",
                "verify_against": "BL",
            },
            {
                "severity": "suggestion",
                "title": "Verificar peso bruto",
                "detail": "Sugerencia: verificar peso bruto contra BL/DUS.",
                "field": "weight",
                "verify_against": "BL,DUS",
            },
            {
                "severity": "suggestion",
                "title": "Verificar valor FOB",
                "detail": "Sugerencia: verificar cálculo del valor FOB.",
                "field": "amount",
                "verify_against": "calculado",
            },
        ],
        "recommendations": [
            "Subir BL para validación cruzada de cantidad de cajas.",
            "Subir DUS para verificar peso bruto.",
        ],
    },
    "demo_factura_5873_error.html": {
        "compliance": [
            {
                "severity": "suggestion",
                "title": "Verificar cantidad de cajas",
                "detail": "Sugerencia: verificar cantidad de cajas contra BL.",
                "field": "quantity",
                "verify_against": "BL",
            },
            {
                "severity": "suggestion",
                "title": "Verificar peso bruto",
                "detail": "Sugerencia: verificar peso bruto contra BL/DUS.",
                "field": "weight",
                "verify_against": "BL,DUS",
            },
            {
                "severity": "suggestion",
                "title": "Verificar valor FOB",
                "detail": "Sugerencia: verificar cálculo del valor FOB.",
                "field": "amount",
                "verify_against": "calculado",
            },
        ],
        "recommendations": [
            "Subir BL para validación cruzada de cantidad de cajas.",
            "Subir DUS para verificar peso bruto.",
        ],
    },
    # Fitosanitario con discrepancias
    "demo_fito_error.pdf": {
        "compliance": [
            {
                "severity": "suggestion",
                "title": "Verificar especie botánica",
                "detail": "Sugerencia: verificar que la especie sea PRUNUS AVIUM (cerezas).",
                "field": "species",
                "verify_against": "SAG",
            },
            {
                "severity": "suggestion",
                "title": "Verificar peso neto",
                "detail": "Sugerencia: verificar peso neto contra Factura.",
                "field": "weight",
                "verify_against": "Factura",
            },
        ],
        "recommendations": [
            "Verificar especie botánica contra normativa SAG.",
            "Subir Factura para validación cruzada de peso.",
        ],
    },
    "demo_fito_2630187_error.html": {
        "compliance": [
            {
                "severity": "suggestion",
                "title": "Verificar especie botánica",
                "detail": "Sugerencia: verificar que la especie sea PRUNUS AVIUM (cerezas).",
                "field": "species",
                "verify_against": "SAG",
            },
            {
                "severity": "suggestion",
                "title": "Verificar peso neto",
                "detail": "Sugerencia: verificar peso neto contra Factura.",
                "field": "weight",
                "verify_against": "Factura",
            },
        ],
        "recommendations": [
            "Verificar especie botánica contra normativa SAG.",
            "Subir Factura para validación cruzada de peso.",
        ],
    },
    # Legacy error demos (mantener compatibilidad - usando cross-validation)
    "demo_error_fito.pdf": {
        "compliance": [
            {
                "severity": "suggestion",
                "title": "Verificar producto declarado",
                "detail": "Sugerencia: verificar que el producto sea 'Cerezas Frescas'.",
                "field": "product",
                "verify_against": "Factura",
            },
            {
                "severity": "suggestion",
                "title": "Verificar referencia SAG",
                "detail": "Sugerencia: confirmar número de resolución fitosanitaria.",
                "field": "sag",
                "verify_against": "SAG",
            },
        ],
        "recommendations": [
            "Corregir descripción del producto a 'Cerezas Frescas'.",
            "Incluir referencia a resolución SAG.",
        ],
    },
    "demo_fito_error_reconstructed.html": {
        "compliance": [
            {
                "severity": "suggestion",
                "title": "Verificar producto declarado",
                "detail": "Sugerencia: verificar que el producto sea 'Cerezas Frescas'.",
                "field": "product",
                "verify_against": "Factura",
            },
            {
                "severity": "suggestion",
                "title": "Verificar referencia SAG",
                "detail": "Sugerencia: confirmar número de resolución fitosanitaria.",
                "field": "sag",
                "verify_against": "SAG",
            },
        ],
        "recommendations": [],
    },
    "demo_error_bl.pdf": {
        "compliance": [
            {
                "severity": "suggestion",
                "title": "Verificar número de contenedor",
                "detail": "Sugerencia: validar contenedor contra Packing List.",
                "field": "container",
                "verify_against": "packing_list",
            },
            {
                "severity": "suggestion",
                "title": "Verificar puerto de descarga",
                "detail": "Sugerencia: confirmar puerto de destino (Shanghai/Hong Kong).",
                "field": "port",
                "verify_against": "Factura,DUS",
            },
        ],
        "recommendations": [
            "Validar número de contenedor contra Booking.",
            "Confirmar puerto de destino final.",
        ],
    },
    "demo_bl_error_reconstructed.html": {
        "compliance": [
            {
                "severity": "suggestion",
                "title": "Verificar número de contenedor",
                "detail": "Sugerencia: validar contenedor contra Packing List.",
                "field": "container",
                "verify_against": "packing_list",
            },
            {
                "severity": "suggestion",
                "title": "Verificar puerto de descarga",
                "detail": "Sugerencia: confirmar puerto de destino.",
                "field": "port",
                "verify_against": "Factura,DUS",
            },
        ],
        "recommendations": [],
    },
    "demo_error_dus.pdf": {
        "compliance": [
            {
                "severity": "suggestion",
                "title": "Verificar Incoterm",
                "detail": "Sugerencia: verificar que el Incoterm coincida con la Factura.",
                "field": "incoterm",
                "verify_against": "Factura",
            },
            {
                "severity": "suggestion",
                "title": "Verificar peso bruto",
                "detail": "Sugerencia: validar peso bruto contra guía de despacho.",
                "field": "weight",
                "verify_against": "guia_despacho,BL",
            },
        ],
        "recommendations": [
            "Alinear Incoterm con Factura Comercial.",
            "Revisar pesaje de báscula.",
        ],
    },
    "demo_dus_error_reconstructed.html": {
        "compliance": [
            {
                "severity": "suggestion",
                "title": "Verificar Incoterm",
                "detail": "Sugerencia: verificar que el Incoterm coincida con la Factura.",
                "field": "incoterm",
                "verify_against": "Factura",
            },
            {
                "severity": "suggestion",
                "title": "Verificar peso bruto",
                "detail": "Sugerencia: validar peso bruto contra BL.",
                "field": "weight",
                "verify_against": "BL",
            },
        ],
        "recommendations": [],
    },
    # ========== DOCUMENTOS LIMPIOS (Reconstructed) ==========
    "demo_bl_real_reconstructed.html": {"compliance": [], "recommendations": []},
    "demo_dus_real_reconstructed.html": {"compliance": [], "recommendations": []},
    "demo_fito_real_reconstructed.html": {"compliance": [], "recommendations": []},
}


def process_document_sync(db: Session, doc: Document) -> None:
    start = time.time()

    # 0) Inyectar HTML Preview si es un archivo demo conocido
    if doc.filename in DEMO_HTML_MAPPING:
        html_filename = DEMO_HTML_MAPPING[doc.filename]
        # Asumimos que los HTML están en la raíz del workspace
        # Desde donde se ejecuta uvicorn (root), el path es directo
        html_path = Path(html_filename)
        if html_path.exists():
            try:
                doc.html_preview = html_path.read_text(encoding="utf-8")
                logger.info(f"Inyectado HTML preview para {doc.filename}")
            except Exception as e:
                logger.warning(f"No se pudo leer el HTML preview {html_filename}: {e}")

    # 0.1) Si el archivo subido es HTML, usarlo como preview
    elif doc.mime == "text/html" or doc.filename.lower().endswith(".html"):
        try:
            path = Path(doc.storage_path)
            if path.exists():
                doc.html_preview = path.read_text(encoding="utf-8", errors="ignore")
                logger.info(
                    f"Usando contenido HTML subido como preview para {doc.filename}"
                )
        except Exception as e:
            logger.warning(f"No se pudo leer el archivo HTML subido: {e}")

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

    # 2) NLP/Extracción (reglas simples o entidades demo hardcodeadas)
    # Verificar si es un archivo demo con entidades predefinidas
    demo_filename = doc.filename
    # Si viene de PDF, mapear a HTML para buscar entidades
    if demo_filename in DEMO_HTML_MAPPING:
        demo_filename = DEMO_HTML_MAPPING[demo_filename]

    if demo_filename in DEMO_ENTITIES:
        entity_payloads = DEMO_ENTITIES[demo_filename]
        logger.info(f"Usando entidades demo hardcodeadas para {demo_filename}")
    else:
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

    # OVERRIDE FOR DEMO: Si el archivo está en los escenarios demo, usar validaciones fijas
    print(f"[DEMO DEBUG] Checking filename: '{doc.filename}' in DEMO_SCENARIOS")
    print(f"[DEMO DEBUG] Available scenarios: {list(DEMO_SCENARIOS.keys())[:10]}...")

    if doc.filename in DEMO_SCENARIOS:
        scenario = DEMO_SCENARIOS[doc.filename]
        combined_compliance = scenario.get("compliance", [])
        recommendations = scenario.get("recommendations", [])
        spellcheck_issues = []  # Limpiar spellcheck para demos
        print(f"[DEMO] Aplicando escenario demo para {doc.filename}")
        print(f"[DEMO] Compliance items: {len(combined_compliance)}")
        if combined_compliance:
            print(f"[DEMO] First compliance item: {combined_compliance[0]}")
    else:
        print(f"[DEMO] No scenario found for: '{doc.filename}'")

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
    doc_type = getattr(doc, "doc_type", "")

    # 1. HS Code (Factura, DUS, Packing List)
    if doc_type in {"factura_comercial", "dus", "packing_list"}:
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

    # 2. Producto (Casi todos los documentos comerciales/técnicos)
    if doc_type in {
        "factura_comercial",
        "packing_list",
        "certificado_fitosanitario",
        "certificado_origen",
        "dus",
        "guia_despacho",
    }:
        if "cereza" not in normalized and "cerezas" not in normalized:
            issues.append(
                {
                    "severity": "warning",
                    "title": "Producto no identificado",
                    "detail": "El texto no menciona la palabra 'cerezas', agr\u00e9gala en la descripci\u00f3n.",
                    "field": "product",
                }
            )

    # 3. Referencia SAG (Certificado Fitosanitario)
    if doc_type == "certificado_fitosanitario":
        if not _contains_keywords(normalized, REGULATORY_TERMS):
            issues.append(
                {
                    "severity": "warning",
                    "title": "Referencia SAG ausente",
                    "detail": "Incluye la referencia al certificado SAG o tratamiento fitosanitario.",
                    "field": "sag",
                }
            )

    # 4. Cadena de frío (Packing List, Fitosanitario, Instrucciones)
    if doc_type in {
        "packing_list",
        "certificado_fitosanitario",
        "instrucciones_embarque",
    }:
        if not _contains_keywords(normalized, COLD_CHAIN_TERMS):
            issues.append(
                {
                    "severity": "warning",
                    "title": "Cadena de fr\u00edo no descrita",
                    "detail": "Describe temperatura objetivo o tratamiento en fr\u00edo en el documento.",
                    "field": "temperature",
                }
            )

    # 5. Incoterm (Factura, DUS)
    if doc_type in {"factura_comercial", "dus"}:
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

    # 6. Contenedor (Packing List, BL, DUS)
    container_value = _first_entity_value(entities, "container")
    if doc_type in {"packing_list", "bl", "dus"}:
        if not container_value:
            issues.append(
                {
                    "severity": "warning",
                    "title": "N\u00famero de contenedor faltante",
                    "detail": "El documento debe informar el contenedor o booking asociado.",
                    "field": "container",
                }
            )

    # 7. BL Number (BL)
    bl_value = _first_entity_value(entities, "bl_number")
    if doc_type == "bl" and not bl_value:
        issues.append(
            {
                "severity": "warning",
                "title": "BL sin n\u00famero",
                "detail": "Completa el Bill of Lading con el identificador oficial.",
                "field": "bl_number",
            }
        )

    # 8. Moneda (Factura, DUS)
    if doc_type in {"factura_comercial", "dus"}:
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
                "detail": f'No se encontró referencia al campo "{label}" en el documento.',
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


def _first_entity_value(entities: Sequence[Dict[str, object]], entity_type: str) -> str:
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
        suggestion = difflib.get_close_matches(
            lowered, dictionary_keys, n=1, cutoff=0.86
        )
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
            'Incluye la descripci\u00f3n "cerezas frescas" en el producto principal.'
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


def extract_text_from_pdf(path: Path) -> str:
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
            content = path.read_text(encoding="utf-8", errors="ignore")
            # Si es HTML, limpiar etiquetas para facilitar regex
            if doc.mime == "text/html" or path.suffix.lower() == ".html":
                # Eliminar scripts y estilos primero
                content = re.sub(
                    r"<(script|style)[^>]*>.*?</\1>",
                    "",
                    content,
                    flags=re.IGNORECASE | re.DOTALL,
                )

                # Reemplazar tags de bloque por saltos de línea para preservar estructura
                content = re.sub(
                    r"<(div|p|br|tr|li|h\d)[^>]*>", "\n", content, flags=re.IGNORECASE
                )
                # Reemplazar otros tags por espacios
                content = re.sub(r"<[^>]+>", " ", content)
                # Normalizar espacios pero preservar saltos de línea
                # Primero colapsar espacios horizontales
                content = re.sub(r"[ \t]+", " ", content)
                # Luego colapsar múltiples saltos de línea en uno solo
                content = re.sub(r"\n\s*\n", "\n", content)
            return content
        if doc.mime in {"application/json", "application/xml"}:
            return path.read_text(encoding="utf-8", errors="ignore")

        # Si es PDF, intentar extraer texto con los motores disponibles
        if doc.mime == "application/pdf" or path.suffix.lower() == ".pdf":
            pdf_text = extract_text_from_pdf(path)
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

    # DUS Number
    dus_match = re.search(
        r"\b(?:dus|documento\s+unico\s+de\s+salida)[:\-\s]*(\d{7,9}-[\dkK])\b", lowered
    )
    if dus_match:
        results.append(
            {
                "type": "dus_number",
                "value": dus_match.group(1).upper(),
                "confidence": 0.9,
            }
        )

    # Booking Number
    booking_match = re.search(r"\b(?:booking|reserva)[:\-\s]*([a-z0-9]+)\b", lowered)
    if booking_match:
        results.append(
            {
                "type": "booking_number",
                "value": booking_match.group(1).upper(),
                "confidence": 0.85,
            }
        )

    # Shipper / Exporter
    shipper_match = re.search(
        r"(?:shipper|exporter|exportador)[:\s\n]+([^\n]+)", text, re.IGNORECASE
    )
    if shipper_match:
        results.append(
            {
                "type": "shipper",
                "value": shipper_match.group(1).strip(),
                "confidence": 0.8,
            }
        )

    # Consignee
    consignee_match = re.search(
        r"(?:consignee|consignatario)[:\s\n]+([^\n]+)", text, re.IGNORECASE
    )
    if consignee_match:
        results.append(
            {
                "type": "consignee",
                "value": consignee_match.group(1).strip(),
                "confidence": 0.8,
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

    # Amount / Total extraction with context priority
    # Look for "Total", "Amount", "Importe", "Saldo" followed by a number
    # Added negative lookahead to ensure we don't pick up weights or package counts

    logger.info(f"DEBUG: Extracting entities from text length {len(lowered)}")
    # logger.info(f"DEBUG: Text snippet: {lowered[:500]}")

    # Updated regex to capture currency codes (USD, EUR, CLP, etc.)
    total_matches = re.finditer(
        r"(?:total|amount|importe|saldo|valor\s*total)[:\s]*([$€£]?\s*[\d,.]+\s*(?:[$€£]|usd|eur|clp|peso|uf|cl)?)(?!\s*(?:kg|kgs|kilos|kgm|lb|lbs|gr|g|bultos|cajas|pallets|unidades|units|packages|cartons\b))",
        lowered,
    )

    best_amount = None
    for match in total_matches:
        logger.info(f"DEBUG: Found total_match candidate: {match.group(0)}")
        val_str = match.group(1)
        # Clean up currency symbols and spaces for the value
        clean_val = re.sub(r"[$€£]|usd|eur|clp|peso|uf|cl", "", val_str).strip()

        # Check if the match actually contains a currency indicator
        has_currency = bool(re.search(r"[$€£]|usd|eur|clp|peso|uf|cl", val_str))
        has_decimal_structure = bool(re.search(r"[,.]\d", clean_val))

        # Heuristic: Prefer matches with currency
        if has_currency:
            best_amount = clean_val
            logger.info(f"DEBUG: Selected best amount (has currency): {best_amount}")
            break  # Found a good one!

        # If no currency, but looks like a valid amount (decimal), keep it as candidate if we don't have one yet
        if has_decimal_structure and len(clean_val) >= 3:
            if best_amount is None:
                best_amount = clean_val
                logger.info(f"DEBUG: Set candidate amount (no currency): {best_amount}")

    if best_amount:
        results.append(
            {
                "type": "amount",
                "value": best_amount,
                "confidence": 0.9,
            }
        )
    else:
        logger.info("DEBUG: No total_match found, trying fallback")
        # Fallback: Try to find currency formatted numbers if no label is found
        # But be stricter: require at least a decimal part or thousands separator to avoid picking up single digits like "8"
        # US: 1,234.56 or 1234.56
        # Added negative lookahead for weight units here too
        amount_match_strict = re.search(
            r"(?:\b\d{1,3}(?:,\d{3})+(?:\.\d{2})?\b|\b\d+\.\d{2}\b)(?!\s*(?:kg|kgs|kilos|kgm|lb|lbs|gr|g|bultos|cajas|pallets|unidades|units|packages|cartons\b))",
            text,
        )
        if amount_match_strict:
            logger.info(f"DEBUG: Found fallback amount: {amount_match_strict.group(0)}")
            results.append(
                {
                    "type": "amount",
                    "value": amount_match_strict.group(0),
                    "confidence": 0.6,
                }
            )

    # Net Weight
    net_weight_match = re.search(
        r"(?:net\s*weight|peso\s*neto)[:\s]*([\d,.]+)\s*(kg|kgs|kilos|kgm)",
        lowered,
    )
    if net_weight_match:
        results.append(
            {
                "type": "net_weight",
                "value": f"{net_weight_match.group(1)} {net_weight_match.group(2)}",
                "confidence": 0.85,
            }
        )

    # Gross Weight
    gross_weight_match = re.search(
        r"(?:gross\s*weight|peso\s*bruto)[:\s]*([\d,.]+)\s*(kg|kgs|kilos|kgm)",
        lowered,
    )
    if gross_weight_match:
        results.append(
            {
                "type": "gross_weight",
                "value": f"{gross_weight_match.group(1)} {gross_weight_match.group(2)}",
                "confidence": 0.85,
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

    keywords: List[Tuple[str, float]] = []
    seen = set()

    # Removed entity-to-keyword logic to avoid redundancy and display issues

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
