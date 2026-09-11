import uuid
from datetime import datetime
from pydantic import BaseModel


class WorkspaceMessageResponse(BaseModel):
    id: uuid.UUID
    seq_id: int
    workspace_id: uuid.UUID
    sender_id: uuid.UUID
    sender_name: str | None = None
    sender_email: str | None = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageSyncResponse(BaseModel):
    messages: list[WorkspaceMessageResponse]
    has_more: bool
    latest_seq_id: int | None