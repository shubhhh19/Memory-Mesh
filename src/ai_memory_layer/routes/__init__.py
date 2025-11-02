"""API routers."""

from fastapi import APIRouter

from ai_memory_layer.routes import admin, memory, messages

api_router = APIRouter(prefix="/v1")
api_router.include_router(messages.router, prefix="/messages", tags=["messages"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
