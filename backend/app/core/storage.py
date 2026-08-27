import os
import uuid
from pathlib import Path
import aiofiles
from fastapi import UploadFile

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class LocalStorageService:
    @staticmethod
    async def save_file(workspace_id: uuid.UUID, file: UploadFile) -> tuple[str, int]:
        """
        Saves an uploaded file to a workspace-specific folder on disk.
        Returns: (saved_relative_path, total_file_size_in_bytes)
        """
        ws_folder = UPLOAD_DIR / str(workspace_id)
        ws_folder.mkdir(parents=True, exist_ok=True)

        # Unique file name to prevent accidental overwrites
        file_ext = Path(file.filename or "").suffix
        unique_name = f"{uuid.uuid4()}{file_ext}"
        target_path = ws_folder / unique_name

        total_bytes = 0
        async with aiofiles.open(target_path, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                total_bytes += len(chunk)
                await out_file.write(chunk)

        # Reset pointer for downstream readers if needed
        await file.seek(0)

        return str(target_path), total_bytes