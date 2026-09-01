# documentos-service

Microservicio de **gestión de documentos**, parte de la migración del monolito
[`El-Destripador-de-PDFs`](https://github.com/AARON-MRB86/El-Destripador-de-PDFs)
hacia una arquitectura de microservicios.

Este servicio es dueño del ciclo de vida del documento: alta, lectura,
actualización, borrado y detección de duplicados por checksum. La extracción
de texto y el resumen con IA son responsabilidad de otros microservicios que
se comunican con este.

## Por qué este corte

Siguiendo el criterio de separar por **funcionalidades de negocio** (no por
capas técnicas), el proyecto original se está dividiendo en:

1. **Documentos** (este repo) — dueño del documento como concepto de negocio.
2. **Extracción de texto** — PDF → texto plano.
3. **Resumen con IA** — texto → resumen.
4. **Notificaciones / Estado** — informa el avance del flujo subir → extraer → resumir.

## Arquitectura

Mismo patrón en capas validado y corregido en el monolito (clean code:
DRY / SOLID / KISS / YAGNI aplicados desde el inicio, con TDD):

```
App/
├── api/               # Rutas HTTP (FastAPI) — capa de entrada
│   └── Routes/
├── services/          # Lógica de negocio (orquestación)
├── repositories/      # Acceso a datos (MongoDB / mongomock en tests)
├── schemas/           # DTOs de entrada/salida (pydantic)
├── models/            # Modelo de dominio
├── utils/             # Validaciones, checksum, extracción, conexión a DB
└── static/            # Assets estáticos (si aplica)
test/                  # Suite de tests unitarios (TDD)
```

Cada pieza se desarrolla con TDD: primero el test (rojo), después el código
mínimo para pasarlo (verde), y recién ahí se refactoriza si hace falta.

## Estado actual

- [x] Estructura base del proyecto
- [x] Modelo de dominio `Document`
- [x] `DocumentRepository` (acceso a datos)
- [ ] `DocumentService` (lógica de negocio: validación, checksum, duplicados)
- [ ] Endpoints REST (`POST/GET/PUT/DELETE /documents`)
- [ ] Dockerfile + integración con Traefik
- [ ] Comunicación con el microservicio de Extracción (Saga)

## Cómo correr los tests

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest test/ -v
```

## Stack

- Python 3.12+
- FastAPI
- MongoDB (pymongo) / mongomock en tests
- pytest (TDD)

## Relación con el monolito

Este servicio reutiliza los aprendizajes del refactor de clean code aplicado
sobre `El-Destripador-de-PDFs`: excepciones de dominio, inyección de
dependencias del repositorio en el servicio, y separación estricta de
responsabilidades por capa.
