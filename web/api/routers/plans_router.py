"""Public ``/plans`` endpoint — backs the pricing page."""
import sys
import os

from fastapi import APIRouter, HTTPException

_PYTHON_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "python", "src"))
if _PYTHON_SRC not in sys.path:
    sys.path.insert(0, _PYTHON_SRC)

from redtonomous.plans import plan_by_id, public_catalog

# No auth — pricing pages need to be public.
router = APIRouter(tags=["plans"])


@router.get("/plans")
async def list_plans():
    return {"plans": public_catalog()}


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str):
    plan = plan_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="No such plan")
    return plan.as_public()
