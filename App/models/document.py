"""Modelo de dominio para un Documento."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Document(BaseModel):
    """Representa un documento PDF procesado por el servicio."""

    id: int | None = None
    name: str
    original_filename: str = ""
    file_path: str
    checksum: str
    file_size: int
    file_content: bytes | None = None
    extracted_text: str | None = None
    is_processed: bool = False
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
