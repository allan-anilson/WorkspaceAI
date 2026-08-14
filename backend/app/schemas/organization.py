import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from app.db.models.organization import OrgRole


# Organization Schemas
class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str | None = Field(default=None, min_length=2, max_length=255, description="Optional custom URL slug. Auto-generated from name if omitted.",)


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    owner_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


# Workspace Schemas
class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str | None = Field(default=None, min_length=2, max_length=255, description="Optional custom URL slug. Auto-generated from name if omitted.",)


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    organization_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True