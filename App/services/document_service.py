"""Servicio de documentos: orquesta validación, checksum y persistencia.

Nota de arquitectura: este microservicio es dueño del ciclo de vida del
documento (alta/lectura/actualización/borrado + deduplicación por checksum).
La extracción de texto y el resumen con IA son responsabilidad de otros
microservicios; por eso `extracted_text`/`is_processed` quedan sin completar
al crear el documento y se actualizan más adelante vía comunicación entre
servicios (Saga).
"""

from typing import List, Optional

from App.exceptions import DocumentNotFoundError, DuplicateDocumentError
from App.models.document import Document
from App.repositories.document_repository import DocumentRepository
from App.utils.validators import ChecksumCalculator, PdfValidator, StringValidator


class DocumentService:
    """Lógica de negocio de documentos, con el repositorio inyectado (DIP)."""

    def __init__(self, repository: DocumentRepository):
        self.repository = repository

    def create_document(self, name: str, filename: Optional[str], file_content: bytes) -> Document:
        """Valida, deduplica y persiste un nuevo documento."""
        normalized_name = StringValidator.validate_required_string(name, "nombre del documento")
        normalized_filename = PdfValidator.validate_filename(filename)
        PdfValidator.validate_bytes(file_content)

        checksum = ChecksumCalculator.from_bytes(file_content)
        if self.repository.get_by_checksum(checksum):
            raise DuplicateDocumentError("Ya existe un documento con el mismo checksum")

        document = Document(
            name=normalized_name,
            file_path=f"memory://documents/{checksum}.pdf",
            checksum=checksum,
            file_size=len(file_content),
        )
        return self.repository.create(document)

    def get_document(self, document_id: int) -> Document:
        return self._get_or_raise(document_id)

    def get_all_documents(self, skip: int = 0, limit: int = 10) -> List[Document]:
        return self.repository.get_all(skip, limit)

    def delete_document(self, document_id: int) -> None:
        self._get_or_raise(document_id)
        self.repository.delete(document_id)

    def _get_or_raise(self, document_id: int) -> Document:
        document = self.repository.get_by_id(document_id)
        if not document:
            raise DocumentNotFoundError(f"Documento {document_id} no encontrado")
        return document
