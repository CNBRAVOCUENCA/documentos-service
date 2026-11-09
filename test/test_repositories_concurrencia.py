"""Casos de concurrencia y rendimiento del repositorio, sobre mongomock."""

import mongomock
import pytest
from App.exceptions import DuplicateDocumentError
from App.models.document import Document
from App.repositories.document_repository import DocumentRepository


@pytest.fixture
def repo():
    db = mongomock.MongoClient()["test_docs"]
    db["documents"].create_index("checksum", unique=True)
    return DocumentRepository(db)


def _doc(checksum: str) -> Document:
    return Document(
        name="Doc", original_filename="a.pdf", file_path="memory://a.pdf",
        checksum=checksum, file_size=6, file_content=b"%PDF-1",
    )


def test_insert_duplicado_simultaneo_se_informa_como_duplicado(repo):
    # Dos subidas del mismo PDF al mismo tiempo pasan ambas la verificación
    # previa; el índice único frena la segunda y debe responderse 409, no 500.
    repo.create(_doc("igual"))
    with pytest.raises(DuplicateDocumentError):
        repo.create(_doc("igual"))


def test_listado_no_carga_el_binario_del_pdf(repo):
    repo.create(_doc("uno"))
    repo.create(_doc("dos"))

    documentos = repo.get_all()

    assert [d.checksum for d in documentos] == ["uno", "dos"]
    assert all(d.file_content is None for d in documentos)


def test_buscar_por_id_si_trae_el_binario(repo):
    creado = repo.create(_doc("tres"))
    assert repo.get_by_id(creado.id).file_content == b"%PDF-1"
