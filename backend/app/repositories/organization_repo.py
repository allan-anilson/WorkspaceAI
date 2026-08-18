import uuid
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.organization import Organization, OrgMember, OrgRole, Workspace


class OrganizationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, org_id: uuid.UUID) -> Organization | None:
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self.db.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()

    async def create_organization(
        self, name: str, slug: str, owner_id: uuid.UUID
    ) -> Organization:
        org = Organization(name=name, slug=slug, owner_id=owner_id)
        self.db.add(org)
        await self.db.flush()
        return org

    async def add_member(
        self, org_id: uuid.UUID, user_id: uuid.UUID, role: OrgRole = OrgRole.MEMBER
    ) -> OrgMember:
        member = OrgMember(organization_id=org_id, user_id=user_id, role=role)
        self.db.add(member)
        await self.db.flush()
        return member

    async def get_member(
        self, org_id: uuid.UUID, user_id: uuid.UUID
    ) -> OrgMember | None:
        result = await self.db.execute(
            select(OrgMember).where(
                OrgMember.organization_id == org_id,
                OrgMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_organizations(self, user_id: uuid.UUID) -> Sequence[Organization]:
        stmt = (
            select(Organization)
            .join(OrgMember, OrgMember.organization_id == Organization.id)
            .where(OrgMember.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # Workspace operations
    async def create_workspace(
        self, name: str, slug: str, organization_id: uuid.UUID
    ) -> Workspace:
        workspace = Workspace(name=name, slug=slug, organization_id=organization_id)
        self.db.add(workspace)
        await self.db.flush()
        return workspace

    async def get_workspaces_by_org(
        self, organization_id: uuid.UUID
    ) -> Sequence[Workspace]:
        result = await self.db.execute(
            select(Workspace).where(Workspace.organization_id == organization_id)
        )
        return result.scalars().all()