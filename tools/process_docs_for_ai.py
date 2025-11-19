import sys
import os
import json
import glob
from pathlib import Path

# Add backend to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.services.processing import (
    extract_text_from_pdf,
    _detect_document_type,
    _detect_entities,
)

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "dataset.jsonl")


def process_docs():
    print(f"Processing documents in {DOCS_DIR}...")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f_out:
        # Process PDFs
        pdf_files = glob.glob(os.path.join(DOCS_DIR, "*.pdf"))
        print(f"Found {len(pdf_files)} PDF files.")

        for pdf_path in pdf_files:
            try:
                print(f"Processing {os.path.basename(pdf_path)}...")
                text = extract_text_from_pdf(Path(pdf_path))

                if not text:
                    print(
                        f"  Warning: No text extracted from {os.path.basename(pdf_path)}"
                    )
                    continue

                doc_type = _detect_document_type(text)
                entities = _detect_entities(text)

                # Create a training example
                # Prompt: Extract information from this document
                # Completion: JSON with extracted data

                example = {
                    "prompt": f"Extract information from the following document text:\n\n{text[:4000]}",  # Truncate for safety
                    "completion": json.dumps(
                        {"doc_type": doc_type, "entities": entities}, ensure_ascii=False
                    ),
                }

                f_out.write(json.dumps(example, ensure_ascii=False) + "\n")

            except Exception as e:
                print(f"  Error processing {os.path.basename(pdf_path)}: {e}")

    print(f"Done. Dataset saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    process_docs()
