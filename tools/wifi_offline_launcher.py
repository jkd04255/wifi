"""Windows offline launcher for the unmodified Wi-Fi Placement Studio v1.6 HTML.

This is a newly built launcher, NOT a recovered original pre-existing EXE.
PyInstaller must bundle legacy/WiFi_Placement_Studio_v1.6_offline.html.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile
import webbrowser

HTML_NAME = "WiFi_Placement_Studio_v1.6_offline.html"


def bundled_html() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / HTML_NAME
    return Path(__file__).resolve().parent.parent / "legacy" / HTML_NAME


def publish_html(source: Path) -> Path:
    data = source.read_bytes()
    if len(data) < 50000 or b"WifiEngine" not in data:
        raise RuntimeError("Bundled v1.6 HTML is missing or does not match expected source structure")
    target_dir = Path(os.getenv("LOCALAPPDATA") or Path.home()) / "WiFi Placement Studio" / "v1.6"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / HTML_NAME
    if target.exists() and hashlib.sha256(target.read_bytes()).digest() == hashlib.sha256(data).digest():
        return target
    fd, name = tempfile.mkstemp(prefix="wifi-v1.6-", suffix=".tmp", dir=target_dir)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return target


def report_error(exc: Exception) -> None:
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, str(exc), "Wi-Fi Placement Studio v1.6", 0x10)
    except Exception:
        print(str(exc), file=sys.stderr)


def main() -> int:
    try:
        source = bundled_html()
        if not source.is_file():
            raise FileNotFoundError("Missing bundled offline HTML: " + str(source))
        if "--self-test" in sys.argv:
            data = source.read_bytes()
            if len(data) < 50000 or b"WifiEngine" not in data:
                raise ValueError("Invalid bundled v1.6 HTML")
            return 0
        target = publish_html(source)
        # PyInstaller onefile extraction is temporary. Copy before opening
        # the default browser so the page survives after the EXE exits.
        if not webbrowser.open(target.as_uri(), new=1, autoraise=True):
            os.startfile(str(target))
        return 0
    except Exception as exc:
        report_error(exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
