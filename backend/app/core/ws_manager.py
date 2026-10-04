import uuid
from fastapi import WebSocket


class WorkspaceConnectionManager:
    def __init__(self):
        # Maps workspace_id -> set of active WebSockets
        self.active_rooms: dict[uuid.UUID, set[WebSocket]] = {}

    async def connect(self, workspace_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        if workspace_id not in self.active_rooms:
            self.active_rooms[workspace_id] = set()
        self.active_rooms[workspace_id].add(websocket)

    def disconnect(self, workspace_id: uuid.UUID, websocket: WebSocket) -> None:
        if workspace_id in self.active_rooms:
            self.active_rooms[workspace_id].discard(websocket)
            if not self.active_rooms[workspace_id]:
                del self.active_rooms[workspace_id]

    async def broadcast_to_workspace(
        self, workspace_id: uuid.UUID, message_data: dict
    ) -> None:
        if workspace_id not in self.active_rooms:
            return

        dead_connections = set()
        for connection in self.active_rooms[workspace_id]:
            try:
                await connection.send_json(message_data)
            except Exception:
                dead_connections.add(connection)

        for dead_socket in dead_connections:
            self.active_rooms[workspace_id].discard(dead_socket)


ws_manager = WorkspaceConnectionManager()