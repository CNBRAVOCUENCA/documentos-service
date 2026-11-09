"""Repositorio de documentos: acceso a datos en MongoDB (o mongomock en tests)."""

from typing import Any

from pymongo.errors import DuplicateKeyError

from App.exceptions import DuplicateDocumentError
from App.models.document import Document

# El binario del PDF puede pesar varios MB: el listado no lo necesita.
_SIN_BINARIO = {"file_content": 0}


class DocumentRepository:
    """Encapsula el acceso a la colección `documents`."""

    def __init__(self, db: Any):
        self.collection = db["documents"]
        self.counters = db["counters"]

    def _next_id(self) -> int:
        """Genera el siguiente ID incremental usando la colección `counters`."""
        result = self.counters.find_one_and_update(
            {"_id": "document_id"},
            {"$inc": {"value": 1}},
            upsert=True,
            return_document=True,
        )
        return result["value"]

    def create(self, document: Document) -> Document:
        """Persiste un nuevo documento, asignándole un ID incremental."""
        document.id = self._next_id()
        try:
            self.collection.insert_one(self._serialize(document))
        except DuplicateKeyError as exc:
            # Dos subidas simultáneas del mismo PDF: el índice único de checksum
            # frena la segunda. Se informa igual que el duplicado detectado antes.
            raise DuplicateDocumentError("Ya existe un documento con el mismo checksum") from exc
        return document

    def get_by_id(self, document_id: int) -> Document | None:
        """Busca un documento por su ID."""
        payload = self.collection.find_one({"id": document_id})
        return self._deserialize(payload)

    def get_by_checksum(self, checksum: str) -> Document | None:
        """Busca un documento por su checksum (para detectar duplicados)."""
        payload = self.collection.find_one({"checksum": checksum})
        return self._deserialize(payload)

    def get_all(self, skip: int = 0, limit: int = 10) -> list[Document]:
        """Devuelve una página de documentos (sin el binario del PDF)."""
        cursor = self.collection.find({}, _SIN_BINARIO).skip(skip).limit(limit)
        return [self._deserialize(payload) for payload in cursor]

    def update(self, document_id: int, data: dict) -> Document | None:
        """Actualiza campos de un documento existente y devuelve el resultado."""
        self.collection.update_one({"id": document_id}, {"$set": data})
        return self.get_by_id(document_id)

    def delete(self, document_id: int) -> bool:
        """Elimina un documento por ID. Devuelve True si existía."""
        result = self.collection.delete_one({"id": document_id})
        return result.deleted_count > 0

    def _serialize(self, document: Document) -> dict:
        return document.model_dump()

    def _deserialize(self, payload: dict | None) -> Document | None:
        if payload is None:
            return None
        payload = {k: v for k, v in payload.items() if k != "_id"}
        # MongoDB devuelve los bytes como bson.Binary; convertir a bytes puros
        # para que el contenido del PDF se preserve exacto al reconstruir el modelo
        # y al enviarlo por HTTP a otros microservicios (ej. extraccion-service).
        if payload.get("file_content") is not None:
            payload["file_content"] = bytes(payload["file_content"])
        return Document(**payload)
