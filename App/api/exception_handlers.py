"""Traduce excepciones de dominio a respuestas HTTP, en un solo lugar (DRY)."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from App.exceptions import (
    DocumentNotFoundError,
    DuplicateDocumentError,
    FileSizeExceededError,
    InvalidFilenameError,
    InvalidPdfError,
)

_STATUS_MAP = {
    InvalidFilenameError: 400,
    InvalidPdfError: 400,
    FileSizeExceededError: 413,
    DuplicateDocumentError: 409,
    DocumentNotFoundError: 404,
}


def register_exception_handlers(app: FastAPI) -> None:
    """Registra un handler por cada excepción de dominio y uno para ValueError."""

    for exc_class, status_code in _STATUS_MAP.items():
        app.add_exception_handler(exc_class, _make_handler(status_code))

    app.add_exception_handler(ValueError, _make_handler(400))


def _make_handler(status_code: int):
    async def handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return handler
