"""Local-only GATE 3 desktop package: real 70-point mandatory-pin optimizer.

Unlike the historical v1.6 desktop package, this is a separately rebuilt EXE.
No third-party/team 2/3 prediction source is connected: RSSI comes from the
v1.6 estimate embedded in the exact Stage 3 HTML. No cloud connection.
"""
from __future__ import annotations

import socket
import sys
import threading
import time
from pathlib import Path

from fastapi.responses import FileResponse, RedirectResponse
from optimizer.api import app
from optimizer.core import OptimizeRequest, optimize

RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
PREVIEW = RESOURCE_ROOT / "preview" / "stage3.html"
TITLE = "Wi-Fi Placement Studio — 필수영역 70점 (GATE 3 미보정 시연)"


@app.get("/", include_in_schema=False)
def root_page():
    return RedirectResponse("/preview/stage3.html")


@app.get("/preview/stage3.html", include_in_schema=False)
def preview_page():
    return FileResponse(PREVIEW, media_type="text/html; charset=utf-8")


def verify_package() -> None:
    content = PREVIEW.read_bytes()
    if len(content) < 80_000:
        raise ValueError("GATE 3 preview HTML is unexpectedly small")
    for word in (b'data-tool="required"', b'id="requiredRadius"',
                 b"requiredSamples", b"minQualityScore", b"/optimize"):
        if word not in content:
            raise ValueError("Missing mandatory-pin feature: " + repr(word))
    for forbidden in (b'data-tool="zone"', b'id="roomDrawer"'):
        if forbidden in content:
            raise ValueError("Retired room-purpose drawing UI is still present")
    request = OptimizeRequest.model_validate({
        "floor": {"widthM": 4, "depthM": 3, "walls": []},
        "lanPort": {"x": 0.5, "z": 0.5, "y": 0.3, "maxCableLengthM": 20},
        "probes": [{"x": 1.0, "z": 1.0, "priorityPct": 100,
                    "targetDbm": -51.5, "minQualityScore": 70}],
        "candidates": [{"position": {"x": 2, "z": 1.5, "y": 1.2},
                        "rssisDbm": [-80]}],
    })
    result = optimize(request)
    if result.get("status") != "no_feasible_candidate":
        raise AssertionError("Mandatory quality 70 hard constraint not enforced")
    if result.get("requiredAreaSatisfied") is not False:
        raise AssertionError("The mandatory quality failure was not reported")


def choose_free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_local_server(port: int):
    import uvicorn
    config = uvicorn.Config(
        app, host="127.0.0.1", port=port, loop="asyncio",
        http="h11", log_level="error", access_log=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="local-wifi-api", daemon=True)
    thread.start()
    for _ in range(300):
        if server.started:
            return server, thread
        if not thread.is_alive():
            raise RuntimeError("Local Wi-Fi optimizer server stopped unexpectedly")
        time.sleep(0.05)
    raise RuntimeError("Local Wi-Fi optimizer server did not become ready")


def show_error(error: Exception):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, str(error), TITLE, 0x10)
    except Exception:
        print(str(error), file=sys.stderr)


def main():
    try:
        verify_package()
        if "--self-test" in sys.argv:
            print("REQUIRED_PIN_70_HARD_CONSTRAINT_OK")
            return 0
        # Import the GUI only after --self-test, to avoid booting WebView in CI.
        import webview
        port = choose_free_local_port()
        server, thread = start_local_server(port)
        try:
            webview.create_window(
                TITLE, f"http://127.0.0.1:{port}/preview/stage3.html",
                width=1440, height=920, min_size=(850, 620),
                confirm_close=False
            )
            webview.start(gui="edgechromium", debug=False)
        finally:
            server.should_exit = True
            thread.join(timeout=5)
        return 0
    except Exception as exc:
        show_error(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
