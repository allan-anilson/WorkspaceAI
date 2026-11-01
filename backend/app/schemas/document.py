import uuid
from datetime import datetime
from pydantic import BaseModel
from app.db.models.document import DocumentStatus


class PresignedUploadRequest(BaseModel):
    filename: str
    file_type: str
    file_size_bytes: int


class PresignedUploadResponse(BaseModel):
    document_id: uuid.UUID
    upload_url: str
    storage_path: str


class PresignedDownloadResponse(BaseModel):
    download_url: str
    filename: str


class DocumentResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    uploaded_by: uuid.UUID
    filename: str
    file_path: str
    file_type: str
    file_size_bytes: int
    status: DocumentStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True