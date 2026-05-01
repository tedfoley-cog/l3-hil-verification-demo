"""V&V Pipeline Dashboard — real-time visualization of the verification flow.

Shows requirement analysis, scenario decomposition, test generation, execution
results, and the traceability matrix. Reads state.json and auto-refreshes.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

_DIR = Path(__file__).resolve().parent
_STATE_FILE = _DIR / "state.json"

app = FastAPI(title="L3 HIL V&V Dashboard")
templates = Jinja2Templates(directory=str(_DIR / "templates"))


def _load_state() -> dict[str, object]:
    if _STATE_FILE.exists():
        with open(_STATE_FILE) as f:
            state: dict[str, object] = json.load(f)
        return state
    return {
        "pipeline_stage": "idle",
        "requirements_analyzed": 0,
        "scenarios_generated": 0,
        "tests_generated": 0,
        "tests_executed": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "traceability_records": [],
        "stages": [],
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    state = _load_state()
    return templates.TemplateResponse(
        request, "index.html", {"state": state}
    )


@app.get("/api/state")
async def api_state() -> dict[str, object]:
    return _load_state()
