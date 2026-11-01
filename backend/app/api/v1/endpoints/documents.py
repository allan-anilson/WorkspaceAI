import uuid
from pathlib import Path
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.storage import storage_service
from app.db.models.document import Document, DocumentStatus
from app.db.models.organization import Workspace
from app.db.models.user import User
from app.repositories.organization_repo import OrganizationRepository
from app.schemas.document import (
    DocumentResponse,
    PresignedDownloadResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
)
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse
from app.services.document_service import DocumentService, process_document_background

router = APIRouter(prefix="/workspaces", tags=["Documents & RAG"])

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".md"}


async def verify_workspace_access(
    workspace_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> Workspace:
    ws_result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ws = ws_result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    org_repo = OrganizationRepository(db)
    member = await org_repo.get_member(org_id=ws.organization_id, user_id=user_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return ws


@router.post(
    "/{workspace_id}/documents/upload-intent",
    response_model=PresignedUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate pre-signed S3 upload URL",
)
async def create_upload_intent(
    workspace_id: uuid.UUID,
    payload: PresignedUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, current_user.id, db)

    file_ext = Path(payload.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    storage_path = f"workspaces/{workspace_id}/{uuid.uuid4()}{file_ext}"

    # Create document record in PENDING state
    doc = Document(
        workspace_id=workspace_id,
        uploaded_by=current_user.id,
        filename=payload.filename,
        file_path=storage_path,
        file_type=payload.file_type,
        file_size_bytes=payload.file_size_bytes,
        status=DocumentStatus.PENDING,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    upload_url = await storage_service.generate_presigned_upload_url(
        storage_path=storage_path,
        content_type=payload.file_type,
    )

    return PresignedUploadResponse(
        document_id=doc.id,
        upload_url=upload_url,
        storage_path=storage_path,
    )


@router.post(
    "/{workspace_id}/documents/{document_id}/confirm",
    response_model=DocumentResponse,
    summary="Confirm client upload completed and trigger RAG ingestion",
)
async def confirm_document_upload(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, current_user.id, db)

    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id,
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    file_ext = Path(doc.filename).suffix.lower()

    # Trigger background text extraction, embedding, and indexing
    background_tasks.add_task(
        process_document_background,
        document_id=doc.id,
        storage_path=doc.file_path,
        file_ext=file_ext,
        workspace_id=workspace_id,
    )

    return doc


@router.get(
    "/{workspace_id}/documents/{document_id}/download-url",
    response_model=PresignedDownloadResponse,
    summary="Get temporary pre-signed S3 download URL",
)
async def get_document_download_url(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, current_user.id, db)

    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id,
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    download_url = await storage_service.generate_presigned_download_url(doc.file_path)

    return PresignedDownloadResponse(
        download_url=download_url,
        filename=doc.filename,
    )


@router.get(
    "/{workspace_id}/documents",
    response_model=List[DocumentResponse],
    summary="List all indexed documents for a workspace",
)
async def list_workspace_documents(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    return await service.list_workspace_documents(
        workspace_id=workspace_id, current_user=current_user
    )


@router.delete(
    "/{workspace_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete document from S3 and database",
)
async def delete_document(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, current_user.id, db)

    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id,
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        await storage_service.delete_file(doc.file_path)
    except Exception:
        pass

    await db.delete(doc)
    await db.commit()


@router.post(
    "/{workspace_id}/rag/query",
    response_model=RAGQueryResponse,
    summary="Query workspace RAG system",
)
async def query_workspace_rag(
    workspace_id: uuid.UUID,
    body: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    return await service.query_workspace_rag(
        workspace_id=workspace_id, query=body.query, current_user=current_user
    )