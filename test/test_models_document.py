"""Pruebas unitarias para el modelo de dominio Document."""

from App.models.document import Document


def test_document_has_expected_fields_with_defaults():
    doc = Document(name="Contrato", file_path="memory://x.pdf", checksum="abc123", file_size=10)

    assert doc.id is None
    assert doc.name == "Contrato"
    assert doc.file_path == "memory://x.pdf"
    assert doc.checksum == "abc123"
    assert doc.file_size == 10
    assert doc.extracted_text is None
    assert doc.is_processed is False


def test_document_accepts_explicit_id():
    doc = Document(id=42, name="Contrato", file_path="p", checksum="c", file_size=1)
    assert doc.id == 42
