"""Pruebas unitarias para DocumentRepository.

Usan una base de datos falsa (`fake_db`, ver conftest.py) para no depender
de una instancia real de MongoDB en los tests unitarios.
"""

from App.models.document import Document
from App.repositories.document_repository import DocumentRepository


def test_create_assigns_incremental_id(fake_db):
    repo = DocumentRepository(fake_db)
    fake_db._cols["counters"].find_one_and_update.return_value = {"value": 1}

    doc = Document(name="Contrato", file_path="memory://x.pdf", checksum="abc", file_size=10)
    created = repo.create(doc)

    assert created.id == 1
    fake_db._cols["documents"].insert_one.assert_called_once()


def test_get_by_id_returns_none_when_missing(fake_db):
    repo = DocumentRepository(fake_db)
    fake_db._cols["documents"].find_one.return_value = None

    assert repo.get_by_id(999) is None


def test_get_by_id_returns_document_when_found(fake_db):
    repo = DocumentRepository(fake_db)
    fake_db._cols["documents"].find_one.return_value = {
        "id": 5,
        "name": "Contrato",
        "file_path": "memory://x.pdf",
        "checksum": "abc",
        "file_size": 10,
        "extracted_text": None,
        "is_processed": False,
    }

    found = repo.get_by_id(5)

    assert found is not None
    assert found.id == 5
    assert found.name == "Contrato"


def test_get_by_checksum_returns_none_when_missing(fake_db):
    repo = DocumentRepository(fake_db)
    fake_db._cols["documents"].find_one.return_value = None

    assert repo.get_by_checksum("nope") is None
