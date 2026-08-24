import uuid
from datetime import datetime
from pydantic import BaseModel
from app.db.models.document import DocumentStatus


class DocumentResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    uploaded_by: uuid.UUID | None
    filename: str
    file_type: str
    file_size_bytes: int
    status: DocumentStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True