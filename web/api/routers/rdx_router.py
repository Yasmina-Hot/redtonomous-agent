"""RDX Red Testing endpoints."""
import sys
import os
import uuid
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict

from ..auth import require_token, require_ws_token
from ..ws_manager import ConnectionManager
from ..agent_runner import run_agent_stream

_PYTHON_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "python", "src"))
if _PYTHON_SRC not in sys.path:
    sys.path.insert(0, _PYTHON_SRC)
from redtonomous import config as cfg_module

router = APIRouter(prefix="/rdx", tags=["rdx"], dependencies=[Depends(require_token)])
rdx_manager = ConnectionManager()

RDX_STORE_PATH = os.path.expanduser("~/.redtonomous/rdx_tests.json")


def _load_tests() -> list[dict]:
    if not os.path.exists(RDX_STORE_PATH):
        return []
    with open(RDX_STORE_PATH) as f:
        return json.load(f)


def _save_tests(tests: list[dict]):
    os.makedirs(os.path.dirname(RDX_STORE_PATH), exist_ok=True)
    with open(RDX_STORE_PATH, "w") as f:
        json.dump(tests, f, indent=2)


class TestCase(BaseModel):
    name: str
    prompt: str
    expected: str = ""
    scoring: str = "llm"  # llm | exact | regex | custom
    rubric: str = ""
    tags: list[str] = []
    suite: str = "default"


class RunTestRequest(BaseModel):
    # ``model_overrides`` conflicts with pydantic's ``model_`` protected
    # namespace; opt out explicitly so we don't get a UserWarning every time
    # this module loads.
    model_config = ConfigDict(protected_namespaces=())

    test_ids: list[str]
    providers: list[str]
    model_overrides: dict[str, str] = {}
    cwd: str = "."
    max_iterations: int = 50


class PipelineRunRequest(BaseModel):
    pipeline_yaml: str
    task: str
    cwd: str = "."


@router.get("/tests")
async def list_tests():
    return _load_tests()


@router.post("/tests")
async def create_test(test: TestCase):
    tests = _load_tests()
    entry = {"id": str(uuid.uuid4()), **test.model_dump()}
    tests.append(entry)
    _save_tests(tests)
    return entry


@router.put("/tests/{test_id}")
async def update_test(test_id: str, test: TestCase):
    tests = _load_tests()
    for i, t in enumerate(tests):
        if t["id"] == test_id:
            tests[i] = {"id": test_id, **test.model_dump()}
            _save_tests(tests)
            return tests[i]
    raise HTTPException(404, "Test not found")


@router.delete("/tests/{test_id}")
async def delete_test(test_id: str):
    tests = _load_tests()
    tests = [t for t in tests if t["id"] != test_id]
    _save_tests(tests)
    return {"ok": True}


@router.post("/run")
async def start_rdx_run(req: RunTestRequest):
    run_id = str(uuid.uuid4())
    return {"run_id": run_id}


# WebSocket bypasses the router-level HTTP dependency; token check happens inline.
@router.websocket("/ws/{run_id}")
async def rdx_run_ws(
    ws: WebSocket,
    run_id: str,
    test_ids: str = "",
    providers: str = "",
    cwd: str = ".",
    token: str = "",
):
    if not await require_ws_token(ws, token):
        return
    await rdx_manager.connect(run_id, ws)
    try:
        cfg = cfg_module.load_config()
        test_id_list = test_ids.split(",") if test_ids else []
        provider_list = providers.split(",") if providers else [cfg.get("default_provider", "claude")]
        all_tests = _load_tests()
        if test_id_list:
            selected = [t for t in all_tests if t["id"] in test_id_list]
        else:
            # Explicit "no ids" used to silently run the first 5 tests, which
            # could spend tokens without consent. Require an explicit list.
            await rdx_manager.send(run_id, {
                "type": "error",
                "message": "No test_ids provided. Pass ?test_ids=a,b,c.",
            })
            return

        for test in selected:
            for provider in provider_list:
                model = cfg.get("default_model", "claude-sonnet-4-6")
                await rdx_manager.send(run_id, {
                    "type": "test_start",
                    "test_id": test["id"],
                    "test_name": test["name"],
                    "provider": provider,
                    "model": model,
                })
                full_output: list[str] = []
                async for event in run_agent_stream(
                    task=test["prompt"], provider=provider, model=model,
                    cwd=cwd, config_dict=cfg, max_iterations=50,
                ):
                    await rdx_manager.send(run_id, {**event, "test_id": test["id"], "provider": provider})
                    if event.get("type") == "done":
                        full_output.append(event.get("text", ""))

                await rdx_manager.send(run_id, {
                    "type": "test_done",
                    "test_id": test["id"],
                    "provider": provider,
                    "output": "\n".join(full_output),
                })

        await rdx_manager.send(run_id, {"type": "run_complete"})
    except WebSocketDisconnect:
        pass
    finally:
        await rdx_manager.disconnect(run_id)
