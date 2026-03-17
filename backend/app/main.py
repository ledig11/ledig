from fastapi import FastAPI

from app.api.analyze import router as analyze_router

app = FastAPI(
    title="Windows Step Guide Backend",
    version="0.1.0",
)

app.include_router(analyze_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
