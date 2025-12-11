"""API routers with versioning support."""

from fastapi import APIRouter

from ai_memory_layer.routes import admin, analytics, auth, conversations, memory, messages, retention, websocket
from ai_memory_layer.versioning import APIVersion, create_versioned_router

# Create versioned routers
v1_router = create_versioned_router(APIVersion.V1)
v1_router.include_router(auth.router, tags=["authentication"])
v1_router.include_router(conversations.router, tags=["conversations"])
v1_router.include_router(messages.router, prefix="/messages", tags=["messages"])
v1_router.include_router(memory.router, prefix="/memory", tags=["memory"])
v1_router.include_router(analytics.router, tags=["analytics"])
v1_router.include_router(retention.router, tags=["retention"])
v1_router.include_router(websocket.router, tags=["websocket"])
v1_router.include_router(admin.router, prefix="/admin", tags=["admin"])

# Main API router that includes all versions
api_router = APIRouter()
api_router.include_router(v1_router)

# Future: Add v2_router when v2 is implemented
# v2_router = create_versioned_router(APIVersion.V2)
# api_router.include_router(v2_router)
