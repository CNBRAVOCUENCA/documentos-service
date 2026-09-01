"""Modelo de dominio para un Documento."""

from typing import Optional

from pydantic import BaseModel


class Document(BaseModel):
    """Representa un documento PDF procesado por el servicio."""

    id: Optional[int] = None
    name: str
    file_path: str
    checksum: str
    file_size: int
    file_content: Optional[bytes] = None
    extracted_text: Optional[str] = None
    is_processed: bool = False
