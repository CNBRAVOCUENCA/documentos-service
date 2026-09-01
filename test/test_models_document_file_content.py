"""Pruebas para el campo file_content (contenido binario real del PDF)."""

from App.models.document import Document


def test_document_stores_raw_file_content():
    doc = Document(
        name="Contrato",
        file_path="memory://x.pdf",
        checksum="abc",
        file_size=10,
        file_content=b"%PDF-1.4...",
    )
    assert doc.file_content == b"%PDF-1.4..."
