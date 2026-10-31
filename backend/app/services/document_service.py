import io
import uuid
from pathlib import Path
from typing import Sequence
from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rag import (
    extract_text_from_file,
    generate_rag_answer,
    get_embeddings,
    split_text_into_chunks,
)
from app.core.storage import storage_service
from app.db.models.document import Document, DocumentStatus
from app.db.models.document_chunk import DocumentChunk
from app.db.models.organization import Workspace
from app.db.models.user import User
from app.db.session import async_session_maker
from app.repositories.document_chunk_repo import DocumentChunkRepository
from app.repositories.document_repo import DocumentRepository
from app.repositories.organization_repo import OrganizationRepository

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".md"}


async def process_document_background(
    document_id: uuid.UUID,
    storage_path: str,
    file_ext: str,
    workspace_id: uuid.UUID,
):
    """Background worker task: streams bytes from S3, extracts text, embeds, and indexes."""
    async with async_session_maker() as db:
        doc_repo = DocumentRepository(db)
        chunk_repo = DocumentChunkRepository(db)

        doc = await doc_repo.get_by_id(document_id)
        if not doc:
            return

        try:
            doc.status = DocumentStatus.PROCESSING
            await db.commit()

            # 1. Download file bytes directly from S3/MinIO
            file_bytes = await storage_service.download_bytes(storage_path)

            # 2. Extract text (supports file-like object or bytes decoding)
            if file_ext in (".txt", ".md"):
                raw_text = file_bytes.decode("utf-8", errors="ignore")
            else:
                # Passes in-memory BytesIO stream for PDF/DOCX parsers
                raw_text = extract_text_from_file(io.BytesIO(file_bytes), file_ext)

            chunks_text = split_text_into_chunks(raw_text)

            if not chunks_text:
                doc.status = DocumentStatus.COMPLETED
                await db.commit()
                return

            # 3. Embed text chunks
            embeddings = await get_embeddings(chunks_text)

            # 4. Store Chunks in pgvector
            chunk_models = [
                DocumentChunk(
                    document_id=doc.id,
                    workspace_id=workspace_id,
                    chunk_index=i,
                    content=chunk_text,
                    embedding=emb,
                )
                for i, (chunk_text, emb) in enumerate(zip(chunks_text, embeddings))
            ]
            await chunk_repo.create_chunks(chunk_models)

            doc.status = DocumentStatus.COMPLETED
            await db.commit()

        except Exception as e:
            await db.rollback()
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)
            await db.commit()


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DocumentRepository(db)
        self.chunk_repo = DocumentChunkRepository(db)
        self.org_repo = OrganizationRepository(db)

    async def _verify_workspace_access(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> Workspace:
        result = await self.db.execute(select(Workspace).where(Workspace.id == workspace_id))
        ws = result.scalar_one_or_none()
        if not ws:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

        member = await self.org_repo.get_member(org_id=ws.organization_id, user_id=user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return ws

    async def upload_document(
        self,
        workspace_id: uuid.UUID,
        file: UploadFile,
        current_user: User,
        background_tasks: BackgroundTasks,
    ) -> Document:
        await self._verify_workspace_access(workspace_id, current_user.id)

        filename = file.filename or "uploaded_file"
        file_ext = Path(filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file format")

        # Determine file size
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)

        # Generate unique s3 storage key
        unique_name = f"{uuid.uuid4()}{file_ext}"
        storage_path = f"workspaces/{workspace_id}/{unique_name}"

        # 1. Stream upload to S3 / MinIO
        await storage_service.upload_file(
            file_obj=file,
            storage_path=storage_path,
            content_type=file.content_type or "application/octet-stream",
        )

        # 2. Persist Document record with S3 key as file_path
        doc = await self.repo.create_document(
            workspace_id=workspace_id,
            uploaded_by=current_user.id,
            filename=filename,
            file_path=storage_path,
            file_type=file.content_type or "application/octet-stream",
            file_size_bytes=file_size,
        )
        await self.db.commit()
        await self.db.refresh(doc)

        # 3. Schedule asynchronous ingestion worker
        background_tasks.add_task(
            process_document_background,
            document_id=doc.id,
            storage_path=storage_path,
            file_ext=file_ext,
            workspace_id=workspace_id,
        )

        return doc

    async def query_workspace_rag(
        self, workspace_id: uuid.UUID, query: str, current_user: User
    ) -> dict:
        await self._verify_workspace_access(workspace_id, current_user.id)

        query_embeddings = await get_embeddings([query])
        if not query_embeddings:
            raise HTTPException(status_code=500, detail="Failed to embed query")

        chunks = await self.chunk_repo.similarity_search(workspace_id, query_embeddings[0], limit=4)
        context_texts = [c.content for c in chunks]

        answer = await generate_rag_answer(query, context_texts)
        return {
            "query": query,
            "answer": answer,
            "sources": [{"chunk_id": c.id, "document_id": c.document_id, "content": c.content} for c in chunks],
        }

    async def list_workspace_documents(self, workspace_id: uuid.UUID, current_user: User) -> Sequence[Document]:
        await self._verify_workspace_access(workspace_id, current_user.id)
        return await self.repo.list_by_workspace(workspace_id)