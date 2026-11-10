"""Schemas (DTOs) de entrada/salida de la API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    """Representación de un documento devuelta por la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    original_filename: str
    file_path: str
    checksum: str
    file_size: int
    extracted_text: str | None = None
    is_processed: bool
    created_at: datetime
    updated_at: datetime


class DocumentUpdate(BaseModel):
    """Campos modificables por el dueño del documento."""

    name: str


class ExtractionResultUpdate(BaseModel):
    """Resultado enviado por el servicio autenticado de Extracción."""

    extracted_text: str
