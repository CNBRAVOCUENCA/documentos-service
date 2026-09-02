"""Pruebas de integración de la API de Documentos, usando mongomock (sin Mongo real)."""

import os

os.environ.setdefault("DATABASE_URL", "mongomock://localhost")

import pytest
from fastapi.testclient import TestClient

VALID_PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


@pytest.fixture
def client():
    from App.main import app
    from App.utils.database import get_client, settings

    get_client().drop_database(settings.database_name)
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_create_and_get_document(client):
    response = client.post(
        "/api/v1/documents",
        data={"name": "Contrato"},
        files={"file": ("contrato.pdf", VALID_PDF, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    doc = response.json()
    assert doc["name"] == "Contrato"
    assert doc["is_processed"] is False

    get_response = client.get(f"/api/v1/documents/{doc['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == doc["id"]


def test_create_document_duplicate_returns_409(client):
    client.post(
        "/api/v1/documents",
        data={"name": "A"},
        files={"file": ("a.pdf", VALID_PDF, "application/pdf")},
    )
    response = client.post(
        "/api/v1/documents",
        data={"name": "B"},
        files={"file": ("b.pdf", VALID_PDF, "application/pdf")},
    )
    assert response.status_code == 409


def test_create_document_invalid_name_returns_400(client):
    response = client.post(
        "/api/v1/documents",
        data={"name": "   "},
        files={"file": ("a.pdf", VALID_PDF, "application/pdf")},
    )
    assert response.status_code == 400


def test_get_missing_document_returns_404(client):
    response = client.get("/api/v1/documents/999999")
    assert response.status_code == 404


def test_list_documents(client):
    client.post(
        "/api/v1/documents",
        data={"name": "A"},
        files={"file": ("a.pdf", VALID_PDF, "application/pdf")},
    )
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_delete_document(client):
    created = client.post(
        "/api/v1/documents",
        data={"name": "A"},
        files={"file": ("a.pdf", VALID_PDF, "application/pdf")},
    ).json()

    delete_response = client.delete(f"/api/v1/documents/{created['id']}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/documents/{created['id']}")
    assert get_response.status_code == 404


def test_get_document_file_returns_raw_pdf_bytes(client):
    created = client.post(
        "/api/v1/documents",
        data={"name": "A"},
        files={"file": ("a.pdf", VALID_PDF, "application/pdf")},
    ).json()

    response = client.get(f"/api/v1/documents/{created['id']}/file")
    assert response.status_code == 200
    assert response.content == VALID_PDF
    assert response.headers["content-type"] == "application/pdf"


def test_get_document_file_missing_returns_404(client):
    response = client.get("/api/v1/documents/999999/file")
    assert response.status_code == 404


def test_update_document_name(client):
    created = client.post(
        "/api/v1/documents",
        data={"name": "A"},
        files={"file": ("a.pdf", VALID_PDF, "application/pdf")},
    ).json()

    response = client.put(f"/api/v1/documents/{created['id']}", json={"name": "Actualizado"})

    assert response.status_code == 200
    assert response.json()["name"] == "Actualizado"


def test_update_missing_document_returns_404(client):
    response = client.put("/api/v1/documents/999999", json={"name": "Actualizado"})
    assert response.status_code == 404
