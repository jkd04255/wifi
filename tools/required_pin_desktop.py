"""Lightweight local-only desktop EXE: hard 70-point required-pin optimizer.

Unlike the historical v1.6 desktop package, this is a separately rebuilt EXE.
No third-party/team 2/3 prediction source is connected: RSSI comes from the
v1.6 estimate embedded in the exact Stage 3 HTML. No cloud connection.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
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


def find_windows_app_browser() -> Path:
    """Use installed Edge/Chrome to avoid shipping an embedded .NET WebView runtime."""
    if os.name != "nt":
        raise RuntimeError("The Windows app-window launcher requires Windows")
    roots = [
        Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")),
        Path(os.environ.get("PROGRAMFILES", "C:/Program Files")),
        Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))),
    ]
    for base in roots:
        for relative in ("Microsoft/Edge/Application/msedge.exe",
                         "Google/Chrome/Application/chrome.exe"):
            browser = base / relative
            if browser.is_file():
                return browser
    for name in ("msedge.exe", "chrome.exe"):
        located = shutil.which(name)
        if located:
            return Path(located)
    try:
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for name in ("msedge.exe", "chrome.exe"):
                key_path = "Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\" + name
                try:
                    with winreg.OpenKey(hive, key_path) as key:
                        path, _ = winreg.QueryValueEx(key, None)
                        if Path(path).is_file():
                            return Path(path)
                except OSError:
                    continue
    except ImportError:
        pass
    raise FileNotFoundError("Microsoft Edge 또는 Google Chrome이 필요합니다.")


def app_window_command(browser: Path, url: str, profile: Path) -> list[str]:
    return [str(browser), "--app=" + url, "--user-data-dir=" + str(profile),
            "--no-first-run", "--no-default-browser-check",
            "--disable-background-mode", "--window-size=1440,920"]


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
            browser = find_windows_app_browser()
            cmd = app_window_command(browser, "http://127.0.0.1:12345/preview/stage3.html", Path("test-profile"))
            if not any(arg.startswith("--app=http://127.0.0.1:") for arg in cmd):
                raise AssertionError("App window launch command missing")
            print("REQUIRED_PIN_70_HARD_CONSTRAINT_AND_APP_BROWSER_OK")
            return 0
        if "--integration-test" in sys.argv:
            import json
            from urllib.request import Request, urlopen
            port = choose_free_local_port()
            server, thread = start_local_server(port)
            try:
                root = f"http://127.0.0.1:{port}"
                with urlopen(root + "/preview/stage3.html", timeout=15) as response:
                    preview = response.read()
                    assert response.status == 200 and b'data-tool="required"' in preview
                    assert b'data-tool="zone"' not in preview
                payload = {
                    "floor": {"widthM": 4, "depthM": 3, "walls": []},
                    "lanPort": {"x": .5, "z": .5, "y": .3, "maxCableLengthM": 20},
                    "probes": [{"x": 1., "z": 1., "priorityPct": 100,
                                "targetDbm": -51.5, "minQualityScore": 70}],
                    "candidates": [{"position": {"x": 2., "z": 1.5, "y": 1.2},
                                    "rssisDbm": [-80]}]
                }
                request = Request(root + "/optimize",
                                  data=json.dumps(payload).encode("utf-8"),
                                  headers={"Content-Type": "application/json"}, method="POST")
                with urlopen(request, timeout=20) as response:
                    output = json.loads(response.read())
                if output["status"] != "no_feasible_candidate" or output["requiredAreaSatisfied"] is not False:
                    raise AssertionError("Local FastAPI hard-constraint contract failed")
                print("LOCAL_HTTP_REQUIRED_PIN_70_ENFORCED")
            finally:
                server.should_exit = True
                thread.join(timeout=6)
            return 0
        # Keep the real local Python optimizer alive for the full lifetime
        # of an isolated Edge/Chrome *app-window* process.
        browser = find_windows_app_browser()
        port = choose_free_local_port()
        server, thread = start_local_server(port)
        with tempfile.TemporaryDirectory(prefix="WifiRequired70_") as temporary:
            profile = Path(temporary) / "browser-profile"
            try:
                args = app_window_command(
                    browser, f"http://127.0.0.1:{port}/preview/stage3.html", profile
                )
                subprocess.run(args, check=True)
            finally:
                server.should_exit = True
                thread.join(timeout=5)
        return 0
    except Exception as exc:
        show_error(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
