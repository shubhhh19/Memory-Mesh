"""Custom exception handling for consistent responses."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from ai_memory_layer.logging import get_logger

logger = get_logger(component="errors")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(SQLAlchemyError, db_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    logger.warning("http_exception", status_code=exc.status_code, detail=exc.detail)
    return JSONResponse(
        {"detail": exc.detail, "request_id": getattr(request.state, "request_id", None)},
        status_code=exc.status_code,
    )


async def db_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("database_error", error=str(exc))
    return JSONResponse(
        {
            "detail": "Database error",
            "request_id": getattr(request.state, "request_id", None),
        },
        status_code=500,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception")
    return JSONResponse(
        {
            "detail": "Internal server error",
            "request_id": getattr(request.state, "request_id", None),
        },
        status_code=500,
    )
