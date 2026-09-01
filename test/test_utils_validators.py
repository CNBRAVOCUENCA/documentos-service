"""Pruebas unitarias para las utilidades de validación."""

import pytest

from App.exceptions import FileSizeExceededError, InvalidFilenameError, InvalidPdfError
from App.utils.validators import ChecksumCalculator, PdfValidator, StringValidator


class TestPdfValidator:
    def test_validate_filename_accepts_pdf(self):
        assert PdfValidator.validate_filename("contrato.pdf") == "contrato.pdf"

    def test_validate_filename_rejects_missing(self):
        with pytest.raises(InvalidFilenameError):
            PdfValidator.validate_filename(None)

    def test_validate_filename_rejects_non_pdf_extension(self):
        with pytest.raises(InvalidFilenameError):
            PdfValidator.validate_filename("archivo.txt")

    def test_validate_bytes_accepts_valid_pdf_signature(self):
        PdfValidator.validate_bytes(b"%PDF-1.4\n...")

    def test_validate_bytes_rejects_empty(self):
        with pytest.raises(InvalidPdfError):
            PdfValidator.validate_bytes(b"")

    def test_validate_bytes_rejects_wrong_signature(self):
        with pytest.raises(InvalidPdfError):
            PdfValidator.validate_bytes(b"NOT A PDF")

    def test_validate_bytes_rejects_oversized(self):
        oversized = b"%PDF-1.4" + (b"0" * (PdfValidator.MAX_FILE_SIZE_BYTES + 1))
        with pytest.raises(FileSizeExceededError):
            PdfValidator.validate_bytes(oversized)


class TestChecksumCalculator:
    def test_from_bytes_is_deterministic(self):
        payload = b"contenido de prueba"
        assert ChecksumCalculator.from_bytes(payload) == ChecksumCalculator.from_bytes(payload)

    def test_from_bytes_differs_for_different_content(self):
        assert ChecksumCalculator.from_bytes(b"a") != ChecksumCalculator.from_bytes(b"b")


class TestStringValidator:
    def test_validate_required_string_strips_whitespace(self):
        assert StringValidator.validate_required_string("  Contrato  ", "nombre") == "Contrato"

    def test_validate_required_string_rejects_blank(self):
        with pytest.raises(ValueError):
            StringValidator.validate_required_string("   ", "nombre")

    def test_validate_required_string_rejects_none(self):
        with pytest.raises(ValueError):
            StringValidator.validate_required_string(None, "nombre")
