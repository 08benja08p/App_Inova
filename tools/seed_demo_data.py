import os
import shutil
import sys
import uuid
from pathlib import Path

# Add backend to path so we can import app modules
sys.path.append(str(Path(__file__).parent.parent))

from backend.app.core.db import SessionLocal, init_db
from backend.app.models.document import Document
from backend.app.services.processing import process_document_sync

# Files to seed from docs/ folder
DEMO_FILES = [
    {
        "filename": "FACTURA TRIBUTARIA N°5861 SA1704CZ.pdf",
        "mime": "application/pdf",
        "target_type": "factura_comercial",
        "html_preview": "demo_invoice_reconstructed.html",
    },
    {
        "filename": "BL ONEYSCLE33614900.pdf",
        "mime": "application/pdf",
        "target_type": "bl",
        "html_preview": "demo_bl_real_reconstructed.html",
    },
    {
        "filename": "FITO 2630187.pdf",
        "mime": "application/pdf",
        "target_type": "certificado_fitosanitario",
        "html_preview": "demo_fito_real_reconstructed.html",
    },
    {
        "filename": "DUS 12497436-4.pdf",
        "mime": "application/pdf",
        "target_type": "dus",
        "html_preview": "demo_dus_real_reconstructed.html",
    },
]


def seed_data():
    print("Initializing DB...")
    init_db()
    db = SessionLocal()

    base_path = Path(__file__).parent.parent
    docs_path = base_path / "docs"
    storage_path = base_path / "backend" / "storage"

    # Path where HTML demos are located (root of workspace)
    html_demos_path = base_path

    storage_path.mkdir(parents=True, exist_ok=True)

    print(f"Looking for files in {docs_path}...")

    for item in DEMO_FILES:
        src_file = docs_path / item["filename"]
        if not src_file.exists():
            print(f"Warning: File {item['filename']} not found in docs/. Skipping.")
            continue

        # Create a unique ID for the document
        doc_id = str(uuid.uuid4())
        # Extension
        ext = src_file.suffix
        # New filename in storage
        storage_filename = f"{doc_id}{ext}"
        dst_file = storage_path / storage_filename

        print(f"Processing {item['filename']} -> {doc_id}...")

        # Copy file
        shutil.copy2(src_file, dst_file)

        # Read HTML preview if available
        html_content = None
        if "html_preview" in item:
            html_file = html_demos_path / item["html_preview"]
            if html_file.exists():
                try:
                    html_content = html_file.read_text(encoding="utf-8")
                    print(f"  [INFO] Loaded HTML preview from {item['html_preview']}")
                except Exception as e:
                    print(f"  [WARN] Failed to read HTML preview: {e}")
            else:
                print(f"  [WARN] HTML preview file not found: {item['html_preview']}")

        # Create DB record
        doc = Document(
            id=doc_id,
            filename=item["filename"],
            mime=item["mime"],
            size=src_file.stat().st_size,
            storage_path=str(dst_file),
            status="processing",
            html_preview=html_content,
            # We let the processor detect the type, or we could hint it if we wanted
            # doc_type=item["target_type"]
        )
        db.add(doc)
        db.commit()

        # Run processing
        try:
            process_document_sync(db, doc)
            print(
                f"  [OK] Processed. Detected Type: {doc.doc_type}. Status: {doc.status}"
            )
        except Exception as e:
            print(f"  [ERROR] Failed to process: {e}")
            doc.status = "failed"
            db.commit()

    db.close()
    print("Seeding complete.")


if __name__ == "__main__":
    seed_data()
