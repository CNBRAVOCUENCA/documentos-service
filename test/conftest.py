"""Fixtures compartidos para los tests del microservicio de Documentos."""

import pytest
from unittest.mock import MagicMock


class FakeDB:
    """Base de datos falsa en memoria para tests de repositorio, sin depender de Mongo real."""

    def __init__(self):
        self._cols = {
            "documents": MagicMock(),
            "counters": MagicMock(),
        }

    def __getitem__(self, name):
        return self._cols[name]


@pytest.fixture
def fake_db():
    return FakeDB()
