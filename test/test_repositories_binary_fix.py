"""Test de regresión: el binario del PDF debe preservarse exacto al pasar por
MongoDB (que lo devuelve como bson.Binary), no corromperse."""

from bson import Binary

from App.repositories.document_repository import DocumentRepository


def test_deserialize_preserva_bytes_desde_bson_binary(fake_db):
    """Cuando Mongo devuelve file_content como bson.Binary, el repositorio
    debe reconstruirlo como bytes idénticos al original."""
    repo = DocumentRepository(fake_db)
    original = b"%PDF-1.4 binario con bytes raros \x00\x01\xff\xfe"

    fake_db._cols["documents"].find_one.return_value = {
        "id": 1, "name": "Test", "original_filename": "t.pdf",
        "file_path": "memory://x", "checksum": "abc", "file_size": len(original),
        "file_content": Binary(original), "extracted_text": None,
        "is_processed": False,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }

    doc = repo.get_by_id(1)
    assert doc is not None
    assert doc.file_content == original
    assert type(doc.file_content) is bytes
