import uuid
from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.schemas.document import DocumentResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.post("/{workspace_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED, summary="Upload a document to a workspace",)
async def upload_document(
    workspace_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    return await service.upload_document(
        workspace_id=workspace_id, file=file, current_user=current_user
    )


@router.get("/{workspace_id}/documents", response_model=List[DocumentResponse], summary="List all documents in a workspace",)
async def list_workspace_documents(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    return await service.list_workspace_documents(
        workspace_id=workspace_id, current_user=current_user
    )