"""GATE 3 local-only integration host.

Run from backend/: uvicorn dev_server:app --host 127.0.0.1 --port 8001

Use the same origin for preview and /candidate-locations, /optimize.
This is deliberately NOT a production deployment or a replacement for teammates' APIs.
"""
from pathlib import Path

from fastapi.responses import FileResponse, RedirectResponse

from optimizer.api import app

_ROOT = Path(__file__).resolve().parents[1]
_PREVIEW = _ROOT / "preview" / "stage3.html"


@app.get("/", include_in_schema=False)
def preview_redirect():
    return RedirectResponse(url="/preview/stage3.html")


@app.get("/preview/stage3.html", include_in_schema=False)
def preview_page():
    return FileResponse(_PREVIEW, media_type="text/html")
