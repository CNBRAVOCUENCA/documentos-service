"""Pruebas de integración de la API de Documentos, usando mongomock (sin Mongo real)."""

import asyncio
import os

import httpx
import pytest
from App.utils.validators import PdfValidator
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "mongomock://localhost")

VALID_PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


@pytest.fixture
def client(monkeypatch):
    from App.config.settings import settings

    monkeypatch.setattr(settings, "extraction_service_api_key", "test-internal-key")
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


@pytest.mark.parametrize(
    ("payload", "expected_detail"),
    [
        (b"", "El archivo está vacío"),
        (b"not a PDF", "El archivo no tiene una firma PDF válida"),
    ],
)
def test_create_document_rejects_invalid_pdf_without_persisting(client, payload, expected_detail):
    response = client.post(
        "/api/v1/documents",
        data={"name": "Inválido"},
        files={"file": ("invalido.pdf", payload, "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == expected_detail
    assert client.get("/api/v1/documents").json() == []


def test_create_document_accepts_file_at_size_limit(client, monkeypatch):
    monkeypatch.setattr(PdfValidator, "MAX_FILE_SIZE_BYTES", 64)
    payload = b"%PDF-" + b"x" * (64 - len(b"%PDF-"))

    response = client.post(
        "/api/v1/documents",
        data={"name": "En el límite"},
        files={"file": ("limite.pdf", payload, "application/pdf")},
    )

    assert response.status_code == 201, response.text
    assert response.json()["file_size"] == 64


def test_create_document_rejects_file_over_size_limit_without_persisting(client, monkeypatch):
    monkeypatch.setattr(PdfValidator, "MAX_FILE_SIZE_BYTES", 64)
    payload = b"%PDF-" + b"x" * (64 - len(b"%PDF-") + 1)

    response = client.post(
        "/api/v1/documents",
        data={"name": "Demasiado grande"},
        files={"file": ("grande.pdf", payload, "application/pdf")},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "El archivo excede el tamaño máximo permitido (64 bytes)"
    assert client.get("/api/v1/documents").json() == []


@pytest.mark.parametrize("declared_length", [None, "1"])
def test_create_document_rejects_oversized_stream_without_reliable_content_length(
    client, monkeypatch, declared_length
):
    monkeypatch.setattr(PdfValidator, "MAX_FILE_SIZE_BYTES", 64)
    boundary = "upload-boundary"
    payload = b"%PDF-" + b"x" * (64 - len(b"%PDF-") + 1)
    parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"name\"\r\n\r\nGrande\r\n".encode(),
        (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"grande.pdf\"\r\nContent-Type: application/pdf\r\n\r\n"
        ).encode(),
        payload,
        f"\r\n--{boundary}--\r\n".encode(),
    ]

    async def body():
        for part in parts:
            yield part

    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if declared_length is not None:
        headers["Content-Length"] = declared_length

    async def send_request():
        transport = httpx.ASGITransport(app=client.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as async_client:
            response = await async_client.post("/api/v1/documents", headers=headers, content=body())
            documents = await async_client.get("/api/v1/documents")
        return response, documents

    response, documents = asyncio.run(send_request())
    assert response.status_code == 413
    assert response.json()["detail"] == "El archivo excede el tamaño máximo permitido (64 bytes)"
    assert documents.json() == []


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


def test_update_extraction_result_persists_text_and_processed_flag(client):
    created = client.post(
        "/api/v1/documents",
        data={"name": "A"},
        files={"file": ("a.pdf", VALID_PDF, "application/pdf")},
    ).json()

    response = client.put(
        f"/api/v1/documents/{created['id']}/extraction",
        headers={"X-Internal-API-Key": "test-internal-key"},
        json={"extracted_text": "Texto extraído"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["extracted_text"] == "Texto extraído"
    assert response.json()["is_processed"] is True
    assert client.get(f"/api/v1/documents/{created['id']}").json()["is_processed"] is True


def test_update_extraction_result_is_idempotent_for_retries(client):
    created = client.post(
        "/api/v1/documents",
        data={"name": "A"},
        files={"file": ("a.pdf", VALID_PDF, "application/pdf")},
    ).json()
    url = f"/api/v1/documents/{created['id']}/extraction"
    headers = {"X-Internal-API-Key": "test-internal-key"}
    payload = {"extracted_text": "Texto extraído"}

    first = client.put(url, headers=headers, json=payload)
    retry = client.put(url, headers=headers, json=payload)

    assert first.status_code == retry.status_code == 200
    assert retry.json()["extracted_text"] == first.json()["extracted_text"]
    assert retry.json()["is_processed"] is True


def test_update_extraction_result_requires_internal_key(client):
    response = client.put("/api/v1/documents/1/extraction", json={"extracted_text": "texto"})

    assert response.status_code == 401


def test_update_extraction_result_rejects_invalid_internal_key(client):
    response = client.put(
        "/api/v1/documents/1/extraction",
        headers={"X-Internal-API-Key": "incorrect"},
        json={"extracted_text": "texto"},
    )

    assert response.status_code == 401


def test_update_extraction_result_requires_configured_key(client, monkeypatch):
    from App.config.settings import settings

    monkeypatch.setattr(settings, "extraction_service_api_key", "")
    response = client.put(
        "/api/v1/documents/1/extraction",
        headers={"X-Internal-API-Key": "test-internal-key"},
        json={"extracted_text": "texto"},
    )

    assert response.status_code == 503


def test_update_extraction_result_missing_document_returns_404(client):
    response = client.put(
        "/api/v1/documents/999999/extraction",
        headers={"X-Internal-API-Key": "test-internal-key"},
        json={"extracted_text": "texto"},
    )

    assert response.status_code == 404
