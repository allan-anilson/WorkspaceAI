import uuid
from typing import Sequence
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import LocalStorageService
from app.db.models.document import Document
from app.db.models.organization import OrgMember, Workspace
from app.db.models.user import User
from app.repositories.document_repo import DocumentRepository
from app.repositories.organization_repo import OrganizationRepository


ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".md"}


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DocumentRepository(db)
        self.org_repo = OrganizationRepository(db)

    async def _verify_workspace_access(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> Workspace:
        # Check workspace exists
        result = await self.db.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        ws = result.scalar_one_or_none()
        if not ws:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        # Check user is member of parent organization
        member = await self.org_repo.get_member(
            org_id=ws.organization_id, user_id=user_id
        )
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this workspace.",
            )
        return ws

    async def upload_document(
        self, workspace_id: uuid.UUID, file: UploadFile, current_user: User
    ) -> Document:
        await self._verify_workspace_access(workspace_id, current_user.id)

        filename = file.filename or "uploaded_file"
        file_ext = "." + filename.split(".")[-1].lower() if "." in filename else ""

        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{file_ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        # Save to storage
        file_path, file_size = await LocalStorageService.save_file(workspace_id, file)

        # Create document record
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
        return doc

    async def list_workspace_documents(
        self, workspace_id: uuid.UUID, current_user: User
    ) -> Sequence[Document]:
        await self._verify_workspace_access(workspace_id, current_user.id)
        return await self.repo.list_by_workspace(workspace_id)