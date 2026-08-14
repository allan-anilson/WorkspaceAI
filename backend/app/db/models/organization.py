import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Enum, ForeignKey, String, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrgRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships 
    members: Mapped[list["OrgMember"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    workspaces: Mapped[list["Workspace"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class OrgMember(Base):
    __tablename__ = "org_members"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_user_org"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[OrgRole] = mapped_column(
        Enum(OrgRole), default=OrgRole.MEMBER, nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="members")


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="workspaces")