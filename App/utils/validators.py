"""Validaciones reutilizables: nombre de archivo, contenido PDF y checksum."""

import hashlib

from fastapi import UploadFile

from App.exceptions import FileSizeExceededError, InvalidFilenameError, InvalidPdfError

PDF_SIGNATURE = b"%PDF-"


class PdfValidator:
    """Valida nombre de archivo y contenido binario de un PDF subido."""

    MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MiB
    READ_CHUNK_SIZE_BYTES = 64 * 1024

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
        PdfValidator.validate_size(len(content))

    @staticmethod
    def validate_size(size: int) -> None:
        """Rechaza tamaños superiores al máximo permitido."""
        if size > PdfValidator.MAX_FILE_SIZE_BYTES:
            raise FileSizeExceededError(
                f"El archivo excede el tamaño máximo permitido ({PdfValidator.MAX_FILE_SIZE_BYTES} bytes)"
            )

    @staticmethod
    async def read_upload(file: UploadFile) -> bytes:
        """Lee un PDF por fragmentos, sin confiar en Content-Length ni cargarlo ilimitadamente."""
        if file.size is not None:
            PdfValidator.validate_size(file.size)

        signature = await file.read(len(PDF_SIGNATURE))
        if not signature:
            raise InvalidPdfError("El archivo está vacío")
        if not signature.startswith(PDF_SIGNATURE):
            raise InvalidPdfError("El archivo no tiene una firma PDF válida")

        content = bytearray(signature)
        while True:
            remaining = PdfValidator.MAX_FILE_SIZE_BYTES - len(content)
            chunk = await file.read(min(PdfValidator.READ_CHUNK_SIZE_BYTES, remaining + 1))
            if not chunk:
                return bytes(content)
            content.extend(chunk)
            PdfValidator.validate_size(len(content))


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
