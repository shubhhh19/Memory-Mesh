"""WebSocket routes for real-time features."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory_layer.database import get_session
from ai_memory_layer.models.user import User
from ai_memory_layer.security import get_current_user_from_token
from ai_memory_layer.services.message_service import MessageService

router = APIRouter(prefix="/ws", tags=["websocket"])


async def authenticate_websocket_user(
    websocket: WebSocket,
    token: str | None,
    tenant_id: str,
) -> User | None:
    """
    Authenticate WebSocket connection and verify tenant access.
    
    Returns:
        User object if authenticated and authorized, None otherwise.
        Closes the WebSocket connection if authentication fails.
    """
    # Validate tenant_id format to prevent injection
    if not tenant_id or len(tenant_id) > 64 or not all(c.isalnum() or c in ('-', '_') for c in tenant_id):
        await websocket.close(code=1008, reason="Invalid tenant ID format")
        return None
    
    # Require authentication for tenant-specific endpoints
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return None
    
    # Verify token and tenant access
    user = None
    try:
        async for session in get_session():
            try:
                user = await get_current_user_from_token(
                    HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
                    session,
                )
                if user:
                    # Verify tenant access
                    if user.tenant_id and user.tenant_id != tenant_id:
                        await websocket.close(code=1008, reason="Access denied to this tenant")
                        return None
                    break
            except Exception:
                pass
            break
    except Exception:
        pass
    
    if not user:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return None
    
    return user


from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass
class ConnectionMetadata:
    """Metadata associated with a WebSocket connection."""
    websocket: WebSocket
    user_id: UUID
    conversation_id: str | None = None


# Simple connection manager
class ConnectionManager:
    """Manages WebSocket connections with user-level filtering."""

    def __init__(self):
        # Stores connections by tenant_id -> list of ConnectionMetadata
        self.active_connections: dict[str, list[ConnectionMetadata]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        tenant_id: str,
        user_id: UUID,
        conversation_id: str | None = None,
    ):
        """Connect a WebSocket for a tenant with user metadata."""
        await websocket.accept()
        if tenant_id not in self.active_connections:
            self.active_connections[tenant_id] = []
        metadata = ConnectionMetadata(
            websocket=websocket,
            user_id=user_id,
            conversation_id=conversation_id,
        )
        self.active_connections[tenant_id].append(metadata)

    def disconnect(self, websocket: WebSocket, tenant_id: str):
        """Disconnect a WebSocket."""
        if tenant_id in self.active_connections:
            self.active_connections[tenant_id] = [
                conn for conn in self.active_connections[tenant_id]
                if conn.websocket != websocket
            ]
            if not self.active_connections[tenant_id]:
                del self.active_connections[tenant_id]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket."""
        await websocket.send_json(message)

    async def broadcast_to_tenant(self, message: dict, tenant_id: str):
        """Broadcast a message to all connections for a tenant."""
        if tenant_id not in self.active_connections:
            return
        
        # Rebuild list to handle disconnections efficiently
        active = []
        for conn in self.active_connections[tenant_id]:
            try:
                await conn.websocket.send_json(message)
                active.append(conn)
            except Exception:
                # Connection is dead, don't add to active list
                pass
        
        # Update active connections list
        self.active_connections[tenant_id] = active

    async def broadcast_to_user(
        self,
        message: dict[str, Any],
        tenant_id: str,
        user_id: UUID,
    ):
        """Broadcast a message only to a specific user's connections."""
        if tenant_id not in self.active_connections:
            return
        
        active = []
        for conn in self.active_connections[tenant_id]:
            try:
                if conn.user_id == user_id:
                    await conn.websocket.send_json(message)
                active.append(conn)
            except Exception:
                # Connection is dead, don't add to active list
                pass
        
        self.active_connections[tenant_id] = active

    async def broadcast_to_conversation(
        self,
        message: dict[str, Any],
        tenant_id: str,
        conversation_id: str,
        allowed_user_ids: set[UUID] | None = None,
    ):
        """
        Broadcast a message to users subscribed to a specific conversation.
        
        If allowed_user_ids is provided, only those users will receive the message.
        """
        if tenant_id not in self.active_connections:
            return
        
        active = []
        for conn in self.active_connections[tenant_id]:
            try:
                # Only send to connections subscribed to this conversation
                if conn.conversation_id == conversation_id:
                    # If allowed_user_ids is set, filter by user
                    if allowed_user_ids is None or conn.user_id in allowed_user_ids:
                        await conn.websocket.send_json(message)
                active.append(conn)
            except Exception:
                # Connection is dead, don't add to active list
                pass
        
        self.active_connections[tenant_id] = active


manager = ConnectionManager()
message_service = MessageService()


@router.websocket("/messages/{tenant_id}")
async def websocket_messages(
    websocket: WebSocket,
    tenant_id: str,
    token: str | None = None,
):
    """WebSocket endpoint for real-time message updates."""
    # Authenticate and verify tenant access
    user = await authenticate_websocket_user(websocket, token, tenant_id)
    if not user:
        return  # Connection already closed by authenticate_websocket_user
    
    await manager.connect(websocket, tenant_id, user_id=user.id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                action = message_data.get("action")
                
                if action == "subscribe":
                    # Client wants to subscribe to updates
                    await manager.send_personal_message(
                        {"type": "subscribed", "tenant_id": tenant_id},
                        websocket,
                    )
                elif action == "ping":
                    # Heartbeat
                    await manager.send_personal_message(
                        {"type": "pong"},
                        websocket,
                    )
                else:
                    await manager.send_personal_message(
                        {"type": "error", "message": f"Unknown action: {action}"},
                        websocket,
                    )
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {"type": "error", "message": "Invalid JSON"},
                    websocket,
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket, tenant_id)


@router.websocket("/stream/{tenant_id}")
async def websocket_stream(
    websocket: WebSocket,
    tenant_id: str,
    token: str | None = None,
    conversation_id: str | None = None,
):
    """WebSocket endpoint for streaming message search results."""
    # Authenticate and verify tenant access
    user = await authenticate_websocket_user(websocket, token, tenant_id)
    if not user:
        return  # Connection already closed by authenticate_websocket_user
    
    await manager.connect(websocket, tenant_id, user_id=user.id, conversation_id=conversation_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                query = message_data.get("query")
                
                if not query:
                    await manager.send_personal_message(
                        {"type": "error", "message": "Query is required"},
                        websocket,
                    )
                    continue
                
                # Perform search
                from ai_memory_layer.database import get_read_session
                from ai_memory_layer.schemas.memory import MemorySearchParams
                
                async for session in get_read_session():
                    params = MemorySearchParams(
                        tenant_id=tenant_id,
                        conversation_id=conversation_id,
                        query=query,
                        top_k=message_data.get("top_k", 5),
                    )
                    
                    results = await message_service.retrieve(session, params)
                    
                    # Stream results
                    await manager.send_personal_message(
                        {
                            "type": "search_results",
                            "query": query,
                            "results": [
                                {
                                    "message_id": str(item.message_id),
                                    "content": item.content,
                                    "role": item.role,
                                    "score": item.score,
                                    "importance": item.importance,
                                }
                                for item in results.items
                            ],
                        },
                        websocket,
                    )
                    break
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {"type": "error", "message": "Invalid JSON"},
                    websocket,
                )
            except Exception as e:
                await manager.send_personal_message(
                    {"type": "error", "message": str(e)},
                    websocket,
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket, tenant_id)


# Helper function to broadcast message events
async def broadcast_message_event(
    tenant_id: str,
    event_type: str,
    data: dict,
    user_id: UUID | None = None,
    conversation_id: str | None = None,
):
    """
    Broadcast a message event to connected clients for a tenant.
    
    If user_id is provided, only that user's connections receive the message.
    If conversation_id is provided, only users subscribed to that conversation receive it.
    """
    message = {
        "type": "message_event",
        "event": event_type,
        "data": data,
    }
    
    if user_id:
        # Send only to specific user
        await manager.broadcast_to_user(message, tenant_id, user_id)
    elif conversation_id:
        # Send to users subscribed to this conversation
        await manager.broadcast_to_conversation(message, tenant_id, conversation_id)
    else:
        # Broadcast to all tenant connections (use sparingly)
        await manager.broadcast_to_tenant(message, tenant_id)

