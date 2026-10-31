import io
import uuid
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.storage import storage_service
from app.db.models.document import Document
from app.db.models.organization import Workspace
from app.db.models.user import User
from app.repositories.organization_repo import OrganizationRepository
from app.schemas.document import DocumentResponse
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/workspaces", tags=["Documents & RAG"])


@router.post("/{workspace_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload document to S3 and trigger asynchronous RAG ingestion",
)
async def upload_document(
    workspace_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    return await service.upload_document(
        workspace_id=workspace_id,
        file=file,
        current_user=current_user,
        background_tasks=background_tasks,
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


@router.get(
    "/{workspace_id}/documents/{document_id}/download",
    summary="Stream raw document bytes from S3/MinIO",
)
async def download_document(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 1. Verify workspace access
    ws_result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ws = ws_result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    org_repo = OrganizationRepository(db)
    member = await org_repo.get_member(org_id=ws.organization_id, user_id=current_user.id)
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # 2. Fetch document record
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id,
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # 3. Stream bytes from S3
    try:
        file_bytes = await storage_service.download_bytes(doc.file_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not retrieve file from storage: {exc}",
        )

    media_type = doc.file_type or "application/octet-stream"
    headers = {"Content-Disposition": f'attachment; filename="{doc.filename}"'}
    return StreamingResponse(io.BytesIO(file_bytes), media_type=media_type, headers=headers)


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
    # 1. Verify workspace access
    ws_result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ws = ws_result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    org_repo = OrganizationRepository(db)
    member = await org_repo.get_member(org_id=ws.organization_id, user_id=current_user.id)
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # 2. Fetch document
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id,
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # 3. Delete file object from S3
    try:
        await storage_service.delete_file(doc.file_path)
    except Exception:
        pass

    # 4. Remove record from database (document chunks cascade via FK)
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