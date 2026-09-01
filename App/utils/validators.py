"""Validaciones reutilizables: nombre de archivo, contenido PDF y checksum."""

import hashlib

from App.exceptions import FileSizeExceededError, InvalidFilenameError, InvalidPdfError

PDF_SIGNATURE = b"%PDF-"


class PdfValidator:
    """Valida nombre de archivo y contenido binario de un PDF subido."""

    MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

    @staticmethod
    def validate_filename(filename: str | None) -> str:
        """Valida que el nombre de archivo exista y tenga extensión .pdf."""
        if not filename or not filename.strip():
            raise InvalidFilenameError("El nombre de archivo es obligatorio")
        if not filename.lower().endswith(".pdf"):
            raise InvalidFilenameError("El archivo debe tener extensión .pdf")
        return filename

    @staticmethod
    def validate_bytes(content: bytes) -> None:
        """Valida que el contenido no esté vacío, tenga firma PDF y no exceda el tamaño máximo."""
        if not content:
            raise InvalidPdfError("El archivo está vacío")
        if not content.startswith(PDF_SIGNATURE):
            raise InvalidPdfError("El archivo no tiene una firma PDF válida")
        if len(content) > PdfValidator.MAX_FILE_SIZE_BYTES:
            raise FileSizeExceededError(
                f"El archivo excede el tamaño máximo permitido ({PdfValidator.MAX_FILE_SIZE_BYTES} bytes)"
            )


class ChecksumCalculator:
    """Calcula el checksum SHA-256 de un contenido binario."""

    @staticmethod
    def from_bytes(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()


class StringValidator:
    """Valida strings obligatorios (ej: nombre de documento)."""

    @staticmethod
    def validate_required_string(value: str | None, field_name: str) -> str:
        if value is None or not value.strip():
            raise ValueError(f"El {field_name} es obligatorio")
        return value.strip()
