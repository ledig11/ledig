from fastapi import FastAPI

from app.api.analyze import router as analyze_router
from app.api.debug import router as debug_router
from app.api.feedback import router as feedback_router
from app.api.sessions import router as sessions_router
from app.api.ws import router as ws_router
from app.storage.log_store import LogStore

app = FastAPI(
    title="Windows Step Guide Backend",
    version="0.1.0",
)

app.include_router(analyze_router, prefix="/api")
app.include_router(feedback_router, prefix="/api")
app.include_router(sessions_router, prefix="/api")
app.include_router(debug_router, prefix="/api")
app.include_router(ws_router, prefix="/api")


@app.on_event("startup")
def startup() -> None:
    LogStore().initialize()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
