from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_configs import router as configs_router
from app.api.routes_documents import router as documents_router
from app.api.routes_exports import router as exports_router
from app.api.routes_jobs import router as jobs_router
from app.core.logging import configure_logging
from app.core.settings import get_settings
from app.storage.database import initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    initialize_database()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(documents_router, prefix=settings.api_prefix)
app.include_router(configs_router, prefix=settings.api_prefix)
app.include_router(jobs_router, prefix=settings.api_prefix)
app.include_router(exports_router, prefix=settings.api_prefix)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "remote-enabled" if settings.mistral_api_key else "local-only"}
