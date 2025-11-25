import re
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _clean_html(content: str) -> str:
    # Current implementation in processing.py
    # Eliminar scripts y estilos primero
    content = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", content, flags=re.IGNORECASE | re.DOTALL)
    
    # Reemplazar tags de bloque por saltos de línea para preservar estructura
    content = re.sub(r"<(div|p|br|tr|li|h\d)[^>]*>", "\n", content, flags=re.IGNORECASE)
    # Reemplazar otros tags por espacios
    content = re.sub(r"<[^>]+>", " ", content)
    # Normalizar espacios pero preservar saltos de línea
    # Primero colapsar espacios horizontales
    content = re.sub(r"[ \t]+", " ", content)
    # Luego colapsar múltiples saltos de línea en uno solo
    content = re.sub(r"\n\s*\n", "\n", content)
    return content

if __name__ == "__main__":
    try:
        with open("demo_packing_list_reconstructed.html", "r", encoding="utf-8") as f:
            raw_html = f.read()
        
        cleaned_text = _clean_html(raw_html)
        
        print(f"Cleaned text length: {len(cleaned_text)}")
        print("--- START SNIPPET ---")
        print(cleaned_text[:1000]) # Print first 1000 chars to see if CSS is there
        print("--- END SNIPPET ---")
        
        if "detail-table" in cleaned_text or "border:" in cleaned_text:
            print("\nFAIL: CSS content found in extracted text!")
        else:
            print("\nSUCCESS: No CSS content found.")
            
    except Exception as e:
        print(f"Error: {e}")
