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
- [x] Modelo de dominio `Document` (incluye `file_content`: el binario real del PDF)
- [x] `DocumentRepository` (acceso a datos)
- [x] `DocumentService` (lógica de negocio: validación, checksum, duplicados)
- [x] Endpoints REST (`POST/GET/PUT/DELETE /documents`, `GET /documents/{id}/file`, `GET /health`)
- [x] Consumido de verdad por `extraccion-service` (segundo microservicio),
      vía `GET /documents/{id}/file` — probado con ambos servicios corriendo
      en paralelo, comunicación HTTP real
- [x] Dockerfile + integración con Traefik mediante Docker Compose y labels
- [x] Persistir `extracted_text`/`is_processed` al completar Extracción mediante
      un endpoint interno autenticado e idempotente

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/documents` | Sube un PDF, lo valida y lo da de alta (form-data: `name`, `file`) |
| GET | `/api/v1/documents` | Lista documentos (paginado: `skip`, `limit`) |
| GET | `/api/v1/documents/{id}` | Obtiene los metadatos de un documento por ID |
| PUT | `/api/v1/documents/{id}` | Actualiza el nombre del documento |
| PUT | `/api/v1/documents/{id}/extraction` | Persiste el resultado de Extracción (requiere `X-Internal-API-Key`) |
| GET | `/api/v1/documents/{id}/file` | Descarga el binario del PDF (consumido por `extraccion-service`) |
| DELETE | `/api/v1/documents/{id}` | Elimina un documento |
| GET | `/health` | Health check |

### Usuario de ejecución en Docker

La imagen ejecuta Uvicorn como el usuario sin privilegios `app`, miembro del
grupo `app`. La aplicación no necesita escribir en `/app`; los logs se envían a
stdout. El directorio personal `/home/app` se crea para ese usuario y no se
amplían los permisos de escritura de `/app`.

### Límite y validación de archivos subidos

La subida acepta PDFs de hasta 20 MiB. El servicio lee el archivo en fragmentos
y rechaza el primer byte que excede ese máximo con HTTP 413, sin depender de
`Content-Length` (que puede faltar o no representar el tamaño real del archivo).
Un archivo vacío o sin la firma inicial `%PDF-` devuelve HTTP 400; estas
comprobaciones no validan por completo la estructura del PDF, que aún puede
resultar corrupto y fallar durante la extracción. Los rechazos no se persisten.

El límite aplica al archivo, no al cuerpo multipart completo. Si se configura
un máximo de cuerpo en el proxy, debe permitir 20 MiB más el espacio de los
campos y delimitadores multipart para que la aplicación pueda aplicar su propio
límite al archivo.

Documentos es el dueño de la persistencia del documento. Extracción calcula el
texto y lo envía con `PUT /api/v1/documents/{id}/extraction`; este servicio
actualiza juntos `extracted_text` e `is_processed=true` y solo responde éxito
después de persistir. Las repeticiones del mismo `PUT` son seguras; un documento
inexistente devuelve 404. La ruta exige el secreto compartido configurado como
`EXTRACTION_SERVICE_API_KEY` y enviado por Extracción en `X-Internal-API-Key`.
Configura un secreto aleatorio largo y el mismo valor en ambos servicios antes
de ejecutar el flujo.

## Ejecutar con Docker y Traefik

Requiere Docker Desktop. Desde la raíz de este repositorio:

```powershell
docker compose up --build -d
Invoke-RestMethod http://documentos.localhost/health
docker compose logs -f documentos
docker compose down
```

Traefik detecta el contenedor mediante labels y publica el servicio en
`http://documentos.localhost`. La API también queda disponible bajo
`/api/v1/documents`.

### Registro y descubrimiento con Consul

El registro en Consul es opcional: si `CONSUL_HTTP_ADDR` está vacío, el servicio
arranca sin registrarse. Para habilitarlo, configura las variables del servicio
en el entorno de despliegue (por ejemplo, en `.env`; nunca publiques el token):

| Variable | Predeterminado | Descripción |
|---|---|---|
| `CONSUL_HTTP_ADDR` | vacío | URL del agente Consul, por ejemplo `http://consul:8500` |
| `CONSUL_HTTP_TOKEN` | vacío | Token ACL enviado como `X-Consul-Token` |
| `CONSUL_SERVICE_NAME` | `APP_NAME` | Nombre registrado |
| `CONSUL_SERVICE_PORT` | `8000` | Puerto HTTP de esta instancia |
| `CONSUL_SERVICE_TAGS` | vacío | Tags separados por comas; Traefik puede consumir aquí sus tags |
| `CONSUL_SERVICE_ADDRESS` | inferida | IP alcanzable de esta instancia; opcionalmente se puede fijar explícitamente |

En Compose se debe conectar esta instancia y el agente Consul a una red que
permita el acceso a la API del agente y al endpoint `/health` del servicio.
Cuando no se define `CONSUL_SERVICE_ADDRESS`, la IP se obtiene de la ruta de red
hacia el agente, evitando registrar un nombre DNS compartido por réplicas.
Cada proceso se registra con un ID que incluye su hostname de ejecución. Consul
consulta `http://<instancia>:<puerto>/health` cada 10 segundos y elimina el
registro tras aproximadamente un minuto en estado crítico. La instancia se
registra al iniciar y se desregistra al cerrar; si el registro inicial falla,
el arranque falla también.


## Documentación teórica

Ver [`docs/`](./docs/00-INDICE.md) para el material de estudio: arquitectura
en capas, clean code (DRY/SOLID/KISS/YAGNI), TDD, el criterio de corte de
microservicios, y los conceptos de sistemas distribuidos (Traefik, Saga,
Redis, Circuit Breaker) que se van a implementar en los próximos servicios.

## Cómo correr los tests

Con **uv** (recomendado, más rápido y con `uv.lock` para versiones reproducibles):

```bash
uv sync --extra dev
uv run --extra dev pytest test/ -v
```

O con pip tradicional:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest test/ -v
```

## Escaneo de seguridad

El workflow `Security scan` audita las dependencias de runtime fijadas en
`uv.lock` y construye/escanea la imagen Docker con Trivy. Se ejecuta en cada PR,
push a `main`/`master`, semanalmente (lunes 06:00 UTC) y manualmente desde
GitHub Actions. La política es: **falla el job cualquier hallazgo HIGH o CRITICAL que tenga
parche disponible** (`ignore-unfixed: true`). Los HIGH/CRITICAL sin parche de la
imagen base (paquetes de Debian en estado *affected*, sin versión corregida)
**se siguen mostrando** en la tabla del log, pero no bloquean: no hay acción
posible desde este repo hasta que Debian publique el arreglo, y en ese momento el
escaneo semanal empieza a fallar y obliga a reconstruir la imagen. No se usan
`.trivyignore` ni otros filtros. Los detalles quedan visibles en el log del workflow. También verifica que la imagen se ejecute como
un usuario distinto de root.

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
