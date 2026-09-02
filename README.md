# micro-docu

Microservicio HTTP inicial con FastAPI.

## Ejecutar

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m uvicorn main:app --reload
```

Endpoints:

- `GET /` identifica el servicio.
- `GET /health` comprueba que está disponible.
- `/docs` muestra la documentación interactiva de la API.