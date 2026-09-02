from fastapi import FastAPI


app = FastAPI(title="micro-docu", version="0.1.0")


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "micro-docu", "status": "running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}