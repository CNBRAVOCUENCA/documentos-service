"""Prueba de integración end-to-end: ciclo de vida completo de un documento.

A diferencia de los demás tests de test_api_document_routes.py (que prueban
un endpoint por vez, aislado), este test encadena TODOS los endpoints en un
solo flujo realista: subir -> leer -> listar -> rechazar duplicado ->
404 en inexistente -> borrar -> confirmar borrado. Sirve como prueba
integral de que el microservicio funciona de punta a punta, no solo pieza
por pieza.
"""

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


def test_full_document_lifecycle_end_to_end(client):
    # 1) El servicio está disponible
    health = client.get("/health")
    assert health.status_code == 200

    # 2) Subir un documento real
    upload = client.post(
        "/api/v1/documents",
        data={"name": "Contrato de alquiler"},
        files={"file": ("contrato.pdf", VALID_PDF, "application/pdf")},
    )
    assert upload.status_code == 201
    doc = upload.json()
    doc_id = doc["id"]
    assert doc["name"] == "Contrato de alquiler"
    assert doc["is_processed"] is False

    # 3) Leerlo por ID
    get_one = client.get(f"/api/v1/documents/{doc_id}")
    assert get_one.status_code == 200
    assert get_one.json()["id"] == doc_id

    # 4) Aparece en el listado
    listing = client.get("/api/v1/documents")
    assert listing.status_code == 200
    assert any(d["id"] == doc_id for d in listing.json())

    # 5) Descargar el binario real del PDF
    file_download = client.get(f"/api/v1/documents/{doc_id}/file")
    assert file_download.status_code == 200
    assert file_download.content == VALID_PDF

    # 6) Subir el mismo PDF de nuevo -> rechazado por duplicado
    duplicate = client.post(
        "/api/v1/documents",
        data={"name": "Otro nombre"},
        files={"file": ("otro.pdf", VALID_PDF, "application/pdf")},
    )
    assert duplicate.status_code == 409

    # 7) Pedir un documento inexistente -> 404
    missing = client.get("/api/v1/documents/999999")
    assert missing.status_code == 404

    # 8) Borrarlo
    delete = client.delete(f"/api/v1/documents/{doc_id}")
    assert delete.status_code == 204

    # 9) Confirmar que ya no existe
    after_delete = client.get(f"/api/v1/documents/{doc_id}")
    assert after_delete.status_code == 404
