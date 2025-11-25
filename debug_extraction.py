import re
import logging
from typing import List, Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _detect_entities(text: str) -> List[Dict[str, object]]:
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
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
            break # Found a good one!
        
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

if __name__ == "__main__":
    try:
        with open("demo_invoice_reconstructed.html", "r", encoding="utf-8") as f:
            text = f.read()
        
        print(f"Read {len(text)} chars from file.")
        results = _detect_entities(text)
        print("Results:")
        for r in results:
            print(r)
    except Exception as e:
        print(f"Error: {e}")
