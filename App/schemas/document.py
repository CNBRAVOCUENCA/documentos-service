"""Schemas (DTOs) de entrada/salida de la API."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    """Representación de un documento devuelta por la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    file_path: str
    checksum: str
    file_size: int
    extracted_text: Optional[str] = None
    is_processed: bool
