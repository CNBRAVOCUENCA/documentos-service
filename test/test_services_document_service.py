"""Pruebas unitarias para DocumentService: orquestación con repositorio mockeado."""

import pytest

from App.exceptions import DocumentNotFoundError, DuplicateDocumentError, InvalidFilenameError, InvalidPdfError
from App.repositories.document_repository import DocumentRepository
from App.services.document_service import DocumentService

VALID_PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


@pytest.fixture
def repo(fake_db):
    return DocumentRepository(fake_db)


@pytest.fixture
def service(repo):
    return DocumentService(repo)


def test_create_document_success(service, fake_db):
    fake_db._cols["counters"].find_one_and_update.return_value = {"value": 1}
    fake_db._cols["documents"].find_one.return_value = None  # sin duplicado

    result = service.create_document("Contrato", "contrato.pdf", VALID_PDF)

    assert result.id == 1
    assert result.name == "Contrato"
    assert result.is_processed is False
    assert result.extracted_text is None
    fake_db._cols["documents"].insert_one.assert_called_once()


def test_create_document_requires_name(service):
    with pytest.raises(ValueError):
        service.create_document("   ", "contrato.pdf", VALID_PDF)


def test_create_document_rejects_non_pdf_filename(service):
    with pytest.raises(InvalidFilenameError):
        service.create_document("Doc", "archivo.txt", VALID_PDF)


def test_create_document_rejects_invalid_pdf_signature(service):
    with pytest.raises(InvalidPdfError):
        service.create_document("Doc", "contrato.pdf", b"NOT A PDF")


def test_create_document_rejects_duplicate_checksum(service, fake_db):
    fake_db._cols["documents"].find_one.return_value = {
        "id": 1, "name": "Otro", "file_path": "p", "checksum": "x",
        "file_size": 1, "extracted_text": None, "is_processed": False,
    }
    with pytest.raises(DuplicateDocumentError):
        service.create_document("Doc", "contrato.pdf", VALID_PDF)


def test_get_document_raises_when_missing(service, fake_db):
    fake_db._cols["documents"].find_one.return_value = None
    with pytest.raises(DocumentNotFoundError):
        service.get_document(999)


def test_get_document_returns_when_found(service, fake_db):
    fake_db._cols["documents"].find_one.return_value = {
        "id": 5, "name": "Contrato", "file_path": "p", "checksum": "x",
        "file_size": 1, "extracted_text": None, "is_processed": False,
    }
    result = service.get_document(5)
    assert result.id == 5


def test_delete_document_raises_when_missing(service, fake_db):
    fake_db._cols["documents"].find_one.return_value = None
    with pytest.raises(DocumentNotFoundError):
        service.delete_document(999)


def test_delete_document_success(service, fake_db):
    fake_db._cols["documents"].find_one.return_value = {
        "id": 5, "name": "Contrato", "file_path": "p", "checksum": "x",
        "file_size": 1, "extracted_text": None, "is_processed": False,
    }
    fake_db._cols["documents"].delete_one.return_value.deleted_count = 1
    service.delete_document(5)
    fake_db._cols["documents"].delete_one.assert_called_once_with({"id": 5})
