import sys
import os

# Ensure the Python package is importable
_PYTHON_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "python", "src"))
if _PYTHON_SRC not in sys.path:
    sys.path.insert(0, _PYTHON_SRC)

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import auth_warning_banner
from .routers.agent_router import router as agent_router
from .routers.config_router import router as config_router
from .routers.models_router import router as models_router
from .routers.logs_router import router as logs_router
from .routers.rdx_router import router as rdx_router
from .routers.files_router import router as files_router

logging.basicConfig(
    level=os.environ.get("REDTONOMOUS_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("redtonomous.api")


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    warning = auth_warning_banner()
    if warning:
        log.warning(warning)
    yield


app = FastAPI(title="Redtonomous API", version="0.1.0", lifespan=_lifespan)

_DEFAULT_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]
_extra = os.environ.get("REDTONOMOUS_CORS_ORIGINS", "")
_origins = _DEFAULT_ORIGINS + [o.strip() for o in _extra.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

app.include_router(agent_router)
app.include_router(config_router)
app.include_router(models_router)
app.include_router(logs_router)
app.include_router(rdx_router)
app.include_router(files_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "redtonomous-api"}
