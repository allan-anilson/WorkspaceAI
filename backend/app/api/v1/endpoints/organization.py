import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    WorkspaceCreate,
    WorkspaceResponse,
)
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED, summary="Create a new organization",)
async def create_organization(
    data: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = OrganizationService(db)
    return await service.create_organization(data=data, current_user=current_user)


@router.get("", response_model=List[OrganizationResponse], summary="List all organizations the current user belongs to",)
async def list_user_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = OrganizationService(db)
    return await service.get_user_organizations(user_id=current_user.id)


@router.post("/{org_id}/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED, summary="Create a workspace inside an organization",)
async def create_workspace(
    org_id: uuid.UUID,
    data: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = OrganizationService(db)
    return await service.create_workspace(
        org_id=org_id, data=data, current_user=current_user
    )


@router.get("/{org_id}/workspaces", response_model=List[WorkspaceResponse], summary="List all workspaces in an organization",)
async def list_org_workspaces(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = OrganizationService(db)
    return await service.get_org_workspaces(org_id=org_id, current_user=current_user)