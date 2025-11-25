import re
import logging
from typing import List, Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _detect_entities(text: str) -> List[Dict[str, object]]:
    # New HTML cleaning logic (preserving newlines)
    # Reemplazar tags de bloque por saltos de línea para preservar estructura
    text = re.sub(r"<(div|p|br|tr|li|h\d)[^>]*>", "\n", text, flags=re.IGNORECASE)
    # Reemplazar otros tags por espacios
    text = re.sub(r"<[^>]+>", " ", text)
    # Normalizar espacios pero preservar saltos de línea
    # Primero colapsar espacios horizontales
    text = re.sub(r"[ \t]+", " ", text)
    # Luego colapsar múltiples saltos de línea en uno solo
    text = re.sub(r"\n\s*\n", "\n", text)
    
    results: List[Dict[str, object]] = []
    lowered = text.lower()
    
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
    return results

if __name__ == "__main__":
    try:
        with open("demo_packing_list_reconstructed.html", "r", encoding="utf-8") as f:
            text = f.read()
        
        print(f"Read {len(text)} chars from file.")
        results = _detect_entities(text)
        print("Results:")
        for r in results:
            print(r)
    except Exception as e:
        print(f"Error: {e}")
