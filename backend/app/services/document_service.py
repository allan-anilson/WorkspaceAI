import uuid
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
from app.core.storage import LocalStorageService
from app.db.models.document import Document, DocumentStatus
from app.db.models.document_chunk import DocumentChunk
from app.db.models.organization import Workspace
from app.db.models.user import User
from app.db.session import async_session_maker
from app.repositories.document_chunk_repo import DocumentChunkRepository
from app.repositories.document_repo import DocumentRepository
from app.repositories.organization_repo import OrganizationRepository

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".md"}


async def process_document_background(document_id: uuid.UUID, file_path: str, workspace_id: uuid.UUID):
    """Background worker task to extract, chunk, embed, and store vectors."""
    async with async_session_maker() as db:
        doc_repo = DocumentRepository(db)
        chunk_repo = DocumentChunkRepository(db)

        doc = await doc_repo.get_by_id(document_id)
        if not doc:
            return

        try:
            doc.status = DocumentStatus.PROCESSING
            await db.commit()

            # 1. Extract & Chunk
            raw_text = extract_text_from_file(file_path)
            chunks_text = split_text_into_chunks(raw_text)

            if not chunks_text:
                doc.status = DocumentStatus.COMPLETED
                await db.commit()
                return

            # 2. Embed
            embeddings = await get_embeddings(chunks_text)

            # 3. Store Chunks
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
        file_ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file format")

        file_path, file_size = await LocalStorageService.save_file(workspace_id, file)

        doc = await self.repo.create_document(
            workspace_id=workspace_id,
            uploaded_by=current_user.id,
            filename=filename,
            file_path=file_path,
            file_type=file.content_type or "application/octet-stream",
            file_size_bytes=file_size,
        )
        await self.db.commit()
        await self.db.refresh(doc)

        # Trigger background processing
        background_tasks.add_task(
            process_document_background,
            document_id=doc.id,
            file_path=file_path,
            workspace_id=workspace_id,
        )

        return doc

    async def query_workspace_rag(
        self, workspace_id: uuid.UUID, query: str, current_user: User
    ) -> dict:
        await self._verify_workspace_access(workspace_id, current_user.id)

        # 1. Embed user query
        query_embeddings = await get_embeddings([query])
        if not query_embeddings:
            raise HTTPException(status_code=500, detail="Failed to embed query")

        # 2. Vector search in pgvector
        chunks = await self.chunk_repo.similarity_search(workspace_id, query_embeddings[0], limit=4)
        context_texts = [c.content for c in chunks]

        # 3. Synthesize answer
        answer = await generate_rag_answer(query, context_texts)
        return {
            "query": query,
            "answer": answer,
            "sources": [{"chunk_id": c.id, "document_id": c.document_id, "content": c.content} for c in chunks],
        }

    async def list_workspace_documents(self, workspace_id: uuid.UUID, current_user: User) -> Sequence[Document]:
        await self._verify_workspace_access(workspace_id, current_user.id)
        return await self.repo.list_by_workspace(workspace_id)