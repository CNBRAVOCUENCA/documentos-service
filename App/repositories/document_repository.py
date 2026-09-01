"""Repositorio de documentos: acceso a datos en MongoDB (o mongomock en tests)."""

from typing import Any, Optional

from App.models.document import Document


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
        self.collection.insert_one(self._serialize(document))
        return document

    def get_by_id(self, document_id: int) -> Optional[Document]:
        """Busca un documento por su ID."""
        payload = self.collection.find_one({"id": document_id})
        return self._deserialize(payload)

    def get_by_checksum(self, checksum: str) -> Optional[Document]:
        """Busca un documento por su checksum (para detectar duplicados)."""
        payload = self.collection.find_one({"checksum": checksum})
        return self._deserialize(payload)

    def get_all(self, skip: int = 0, limit: int = 10) -> list[Document]:
        """Devuelve una página de documentos."""
        cursor = self.collection.find().skip(skip).limit(limit)
        return [self._deserialize(payload) for payload in cursor]

    def update(self, document_id: int, data: dict) -> Optional[Document]:
        """Actualiza campos de un documento existente y devuelve el resultado."""
        self.collection.update_one({"id": document_id}, {"$set": data})
        return self.get_by_id(document_id)

    def delete(self, document_id: int) -> bool:
        """Elimina un documento por ID. Devuelve True si existía."""
        result = self.collection.delete_one({"id": document_id})
        return result.deleted_count > 0

    def _serialize(self, document: Document) -> dict:
        return document.model_dump()

    def _deserialize(self, payload: Optional[dict]) -> Optional[Document]:
        if payload is None:
            return None
        payload = {k: v for k, v in payload.items() if k != "_id"}
        return Document(**payload)
