import uuid
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document, DocumentStatus


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_document(
        self,
        workspace_id: uuid.UUID,
        uploaded_by: uuid.UUID,
        filename: str,
        file_path: str,
        file_type: str,
        file_size_bytes: int,
    ) -> Document:
        doc = Document(
            workspace_id=workspace_id,
            uploaded_by=uploaded_by,
            filename=filename,
            file_path=file_path,
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            status=DocumentStatus.PENDING,
        )
        self.db.add(doc)
        await self.db.flush()
        return doc

    async def get_by_id(self, doc_id: uuid.UUID) -> Document | None:
        result = await self.db.execute(
            select(Document).where(Document.id == doc_id)
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: uuid.UUID) -> Sequence[Document]:
        result = await self.db.execute(
            select(Document)
            .where(Document.workspace_id == workspace_id)
            .order_by(Document.created_at.desc())
        )
        return result.scalars().all()