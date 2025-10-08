import os
import uuid
from fastapi import UploadFile
from ..core.config import get_settings


async def save_upload(file: UploadFile):
    settings = get_settings()
    os.makedirs(settings.storage_dir, exist_ok=True)
    ext = os.path.splitext(file.filename)[1].lower()
    name = f"{uuid.uuid4()}{ext}"
    path = os.path.join(settings.storage_dir, name)

    size = 0
    with open(path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            f.write(chunk)
    await file.close()
    return path, size
