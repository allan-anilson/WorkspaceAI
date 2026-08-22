import uuid
from typing import Sequence
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import slugify
from app.db.models.organization import Organization, OrgRole, Workspace
from app.db.models.user import User
from app.repositories.organization_repo import OrganizationRepository
from app.schemas.organization import OrganizationCreate, WorkspaceCreate


class OrganizationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = OrganizationRepository(db)

    async def _generate_unique_org_slug(self, name: str, custom_slug: str | None = None) -> str:
        base_slug = slugify(custom_slug or name)
        slug = base_slug
        counter = 1

        while await self.repo.get_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    async def create_organization(
        self, data: OrganizationCreate, current_user: User
    ) -> Organization:
        slug = await self._generate_unique_org_slug(data.name, data.slug)

        # 1. Create Organization
        org = await self.repo.create_organization(
            name=data.name, slug=slug, owner_id=current_user.id
        )

        # 2. Add creator as OWNER
        await self.repo.add_member(
            org_id=org.id, user_id=current_user.id, role=OrgRole.OWNER
        )

        # 3. Create a default workspace
        ws_slug = slugify("General")
        await self.repo.create_workspace(
            name="General", slug=ws_slug, organization_id=org.id
        )

        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def get_user_organizations(self, user_id: uuid.UUID) -> Sequence[Organization]:
        return await self.repo.get_user_organizations(user_id)

    async def create_workspace(
        self, org_id: uuid.UUID, data: WorkspaceCreate, current_user: User
    ) -> Workspace:
        member = await self.repo.get_member(org_id=org_id, user_id=current_user.id)
        if not member or member.role not in (OrgRole.OWNER, OrgRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Organization Owners and Admins can create workspaces.",
            )

        ws_slug = slugify(data.slug or data.name)
        workspace = await self.repo.create_workspace(
            name=data.name, slug=ws_slug, organization_id=org_id
        )
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace

    async def get_org_workspaces(
        self, org_id: uuid.UUID, current_user: User
    ) -> Sequence[Workspace]:
        member = await self.repo.get_member(org_id=org_id, user_id=current_user.id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this organization.",
            )
        return await self.repo.get_workspaces_by_org(org_id)