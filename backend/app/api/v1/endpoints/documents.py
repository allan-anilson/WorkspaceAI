import uuid
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.schemas.document import DocumentResponse
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/workspaces", tags=["Documents & RAG"])


@router.post("/{workspace_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
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


@router.get("/{workspace_id}/documents", response_model=List[DocumentResponse])
async def list_workspace_documents(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    return await service.list_workspace_documents(workspace_id=workspace_id, current_user=current_user)


@router.post("/{workspace_id}/rag/query", response_model=RAGQueryResponse)
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