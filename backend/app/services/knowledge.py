import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[3]
GUIDES_DIR = PROJECT_ROOT / "guides"

EXTRACTION_SCHEMA_FILE = "exportacion_cerezas_extraction_schema.json"
KB_FILE = "exportacion_cerezas_kb.json"


def _load_json_file(filename: str) -> Dict[str, Any]:
    path = GUIDES_DIR / filename
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


@lru_cache()
def get_extraction_schema() -> Dict[str, Any]:
    data = _load_json_file(EXTRACTION_SCHEMA_FILE)
    return data.get("schemas", {}) if isinstance(data, dict) else {}


@lru_cache()
def get_document_knowledge() -> Dict[str, Dict[str, Any]]:
    data = _load_json_file(KB_FILE)
    items: List[Dict[str, Any]] = data.get("document_types", []) if isinstance(data, dict) else []
    return {item.get("id"): item for item in items if item.get("id")}


def get_document_labels() -> Dict[str, str]:
    knowledge = get_document_knowledge()
    return {key: value.get("name", key.replace("_", " ").title()) for key, value in knowledge.items()}
