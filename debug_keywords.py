import re
import logging
from collections import Counter
from typing import List, Dict, Sequence, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STOPWORDS = {
    "de", "la", "el", "los", "las", "y", "en", "del", "para", "con", "por", "una", "un", "es", "al", "lo", "se", "como",
    "the", "and", "for", "with", "that", "from", "this", "are", "was", "have", "not", "you", "your", "our", "about", "into", "after"
}

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
    
    # Combine counts
    combined = single_counter + bigram_counter
    
    # Return top N
    return combined.most_common(max_keywords)

if __name__ == "__main__":
    try:
        with open("demo_packing_list_reconstructed.html", "r", encoding="utf-8") as f:
            raw_html = f.read()
        
        cleaned_text = _clean_html(raw_html)
        print(f"Cleaned text length: {len(cleaned_text)}")
        
        keywords = _extract_keywords(cleaned_text, [])
        print("\nExtracted Keywords:")
        for kw, count in keywords:
            print(f"{kw}: {count}")
            
    except Exception as e:
        print(f"Error: {e}")
