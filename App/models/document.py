"""Modelo de dominio para un Documento."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Document(BaseModel):
    """Representa un documento PDF procesado por el servicio."""

    id: Optional[int] = None
    name: str
    original_filename: str = ""
    file_path: str
    checksum: str
    file_size: int
    file_content: Optional[bytes] = None
    extracted_text: Optional[str] = None
    is_processed: bool = False
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
