"""Excepciones de dominio para el microservicio de Documentos."""


class DocumentException(Exception):
    """Excepción base para errores de negocio de este servicio."""


class InvalidFilenameError(DocumentException):
    """El nombre de archivo es inválido o no corresponde a un PDF."""


class InvalidPdfError(DocumentException):
    """El contenido del archivo no es un PDF válido."""


class FileSizeExceededError(DocumentException):
    """El archivo excede el tamaño máximo permitido."""


class DuplicateDocumentError(DocumentException):
    """Ya existe un documento con el mismo checksum."""


class DocumentNotFoundError(DocumentException):
    """No se encontró un documento con el ID solicitado."""
