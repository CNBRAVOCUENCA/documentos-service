"""Conexión a MongoDB. Soporta `mongomock://` para tests/desarrollo local."""

from functools import lru_cache

from pymongo import ASCENDING, MongoClient
from pymongo.database import Database

from App.config.settings import settings


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    if settings.database_url.startswith("mongomock://"):
        import mongomock

        return mongomock.MongoClient()

    return MongoClient(
        settings.database_url,
        serverSelectionTimeoutMS=settings.database_timeout_ms,
        connect=False,
    )


def get_database() -> Database:
    return get_client()[settings.database_name]


def get_db() -> Database:
    """Dependencia de FastAPI que devuelve la base de datos configurada."""
    return get_database()


def ensure_indexes() -> None:
    """Crea los índices necesarios en la colección `documents`."""
    db = get_database()
    documents = db["documents"]
    documents.create_index([("id", ASCENDING)], unique=True, name="idx_documents_id")
    documents.create_index([("checksum", ASCENDING)], unique=True, name="idx_documents_checksum")

    counters = db["counters"]
    counters.update_one({"_id": "document_id"}, {"$setOnInsert": {"value": 0}}, upsert=True)
