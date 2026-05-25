import sys, os
_PYTHON_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "python", "src"))
if _PYTHON_SRC not in sys.path:
    sys.path.insert(0, _PYTHON_SRC)

from fastapi import APIRouter
from redtonomous.models.registry import KNOWN_MODELS

router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
async def list_models():
    return KNOWN_MODELS
