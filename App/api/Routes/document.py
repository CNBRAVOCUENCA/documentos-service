"""Rutas REST del microservicio de Documentos."""

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from fastapi.responses import Response
from pymongo.database import Database

from App.config.settings import settings
from App.repositories.document_repository import DocumentRepository
from App.schemas.document import DocumentResponse, DocumentUpdate, ExtractionResultUpdate
from App.services.document_service import DocumentService
from App.utils.database import get_db
from App.utils.validators import PdfValidator

router = APIRouter(prefix="/documents", tags=["documents"])


def _get_service(db: Database = Depends(get_db)) -> DocumentService:
    return DocumentService(DocumentRepository(db))


def _get_extraction_service(
    api_key: Annotated[str | None, Header(alias="X-Internal-API-Key")] = None,
    db: Database = Depends(get_db),
) -> DocumentService:
    expected_api_key = settings.extraction_service_api_key
    if not expected_api_key:
        raise HTTPException(status_code=503, detail="Autenticación interna no configurada")
    if api_key is None or not secrets.compare_digest(
        api_key.encode("utf-8"), expected_api_key.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Credenciales internas inválidas")
    return DocumentService(DocumentRepository(db))


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    name: str = Form(...),
    file: UploadFile = File(...),
    service: DocumentService = Depends(_get_service),
) -> DocumentResponse:
    """Sube y valida un PDF, y da de alta el documento (sin extraer texto todavía)."""
    try:
        payload = await PdfValidator.read_upload(file)
        document = service.create_document(name, file.filename, payload)
        return DocumentResponse.model_validate(document)
    finally:
        await file.close()


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    skip: int = 0, limit: int = 10, service: DocumentService = Depends(_get_service)
) -> list[DocumentResponse]:
    documents = service.get_all_documents(skip, limit)
    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: int, service: DocumentService = Depends(_get_service)) -> DocumentResponse:
    document = service.get_document(doc_id)
    return DocumentResponse.model_validate(document)


@router.get("/{doc_id}/file")
async def get_document_file(doc_id: int, service: DocumentService = Depends(_get_service)) -> Response:
    """Devuelve el contenido binario del PDF, para que otros microservicios
    (ej. Extracción de texto) puedan consumirlo."""
    document = service.get_document(doc_id)
    return Response(content=document.file_content, media_type="application/pdf")


@router.put("/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: int,
    payload: DocumentUpdate,
    service: DocumentService = Depends(_get_service),
) -> DocumentResponse:
    document = service.update_document(doc_id, payload.name)
    return DocumentResponse.model_validate(document)


@router.put("/{doc_id}/extraction", response_model=DocumentResponse)
async def update_extraction_result(
    doc_id: int,
    payload: ExtractionResultUpdate,
    service: DocumentService = Depends(_get_extraction_service),
) -> DocumentResponse:
    """Persiste el texto extraído; solo Extracción puede invocar este contrato."""
    document = service.update_extraction_result(doc_id, payload.extracted_text)
    return DocumentResponse.model_validate(document)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(doc_id: int, service: DocumentService = Depends(_get_service)) -> None:
    service.delete_document(doc_id)
