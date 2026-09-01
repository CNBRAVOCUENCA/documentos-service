"""Rutas REST del microservicio de Documentos."""

from typing import List

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import Response
from pymongo.database import Database

from App.repositories.document_repository import DocumentRepository
from App.schemas.document import DocumentResponse
from App.services.document_service import DocumentService
from App.utils.database import get_db

router = APIRouter(prefix="/documents", tags=["documents"])


def _get_service(db: Database = Depends(get_db)) -> DocumentService:
    return DocumentService(DocumentRepository(db))


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    name: str = Form(...),
    file: UploadFile = File(...),
    service: DocumentService = Depends(_get_service),
) -> DocumentResponse:
    """Sube y valida un PDF, y da de alta el documento (sin extraer texto todavía)."""
    try:
        payload = await file.read()
        document = service.create_document(name, file.filename, payload)
        return DocumentResponse.model_validate(document)
    finally:
        await file.close()


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = 0, limit: int = 10, service: DocumentService = Depends(_get_service)
) -> List[DocumentResponse]:
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


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(doc_id: int, service: DocumentService = Depends(_get_service)) -> None:
    service.delete_document(doc_id)
