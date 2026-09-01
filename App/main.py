"""Entrypoint del microservicio de Documentos."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from App.api import document_router
from App.api.exception_handlers import register_exception_handlers
from App.config.settings import settings
from App.utils.database import ensure_indexes


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_indexes()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

register_exception_handlers(app)
app.include_router(document_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health() -> dict:
    """Health check para orquestadores (Docker/Traefik)."""
    return {"status": "ok", "service": settings.app_name}
