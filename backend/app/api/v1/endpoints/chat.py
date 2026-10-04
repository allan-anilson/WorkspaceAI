import uuid
import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.ws_manager import ws_manager
from app.db.models.chat_message import WorkspaceMessage
from app.db.models.organization import Workspace
from app.db.models.user import User
from app.db.session import async_session_maker
from app.repositories.organization_repo import OrganizationRepository
from app.schemas.chat_message import MessageSyncResponse, WorkspaceMessageResponse

router = APIRouter(prefix="/workspaces", tags=["Workspace Chat"])


async def authenticate_ws_token(token: str, db: AsyncSession) -> User:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


@router.websocket("/{workspace_id}/chat/ws")
async def workspace_chat_ws(
    websocket: WebSocket,
    workspace_id: uuid.UUID,
    token: str = Query(...),
):
    # 1. Authenticate & Authorize during handshake
    async with async_session_maker() as db:
        try:
            current_user = await authenticate_ws_token(token, db)

            ws_result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
            ws = ws_result.scalar_one_or_none()
            if not ws:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

            org_repo = OrganizationRepository(db)
            member = await org_repo.get_member(org_id=ws.organization_id, user_id=current_user.id)
            if not member:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
        except HTTPException:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    # 2. Join workspace room
    await ws_manager.connect(workspace_id, websocket)

    # 3. Message loop
    try:
        while True:
            text_data = await websocket.receive_text()
            if not text_data.strip():
                continue

            async with async_session_maker() as db:
                msg = WorkspaceMessage(
                    workspace_id=workspace_id,
                    sender_id=current_user.id,
                    content=text_data.strip(),
                )
                db.add(msg)
                await db.commit()
                await db.refresh(msg)

                payload = {
                    "id": str(msg.id),
                    "seq_id": msg.seq_id,
                    "workspace_id": str(msg.workspace_id),
                    "sender_id": str(msg.sender_id),
                    "sender_name": current_user.full_name or current_user.email,
                    "sender_email": current_user.email,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                }
                await ws_manager.broadcast_to_workspace(workspace_id, payload)

    except WebSocketDisconnect:
        ws_manager.disconnect(workspace_id, websocket)


@router.get(
    "/{workspace_id}/messages/sync",
    response_model=MessageSyncResponse,
    summary="Synchronize messages using sequential cursor",
)
async def sync_workspace_messages(
    workspace_id: uuid.UUID,
    after_seq_id: int = Query(
        0, description="Fetch messages strictly greater than this seq_id (0 = initial load)"
    ),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws_result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ws = ws_result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    org_repo = OrganizationRepository(db)
    member = await org_repo.get_member(org_id=ws.organization_id, user_id=current_user.id)
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    stmt = (
        select(WorkspaceMessage)
        .options(selectinload(WorkspaceMessage.sender))
        .where(
            WorkspaceMessage.workspace_id == workspace_id,
            WorkspaceMessage.seq_id > after_seq_id,
        )
        .order_by(WorkspaceMessage.seq_id.asc())
        .limit(limit + 1)
    )
    result = await db.execute(stmt)
    records = list(result.scalars().all())

    has_more = len(records) > limit
    messages_to_return = records[:limit]

    formatted = [
        WorkspaceMessageResponse(
            id=m.id,
            seq_id=m.seq_id,
            workspace_id=m.workspace_id,
            sender_id=m.sender_id,
            sender_name=m.sender.full_name if m.sender else None,
            sender_email=m.sender.email if m.sender else None,
            content=m.content,
            created_at=m.created_at,
        )
        for m in messages_to_return
    ]

    latest_seq = messages_to_return[-1].seq_id if messages_to_return else after_seq_id

    return MessageSyncResponse(
        messages=formatted,
        has_more=has_more,
        latest_seq_id=latest_seq,
    )