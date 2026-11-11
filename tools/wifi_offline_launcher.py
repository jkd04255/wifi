"""Windows offline launcher for the unmodified Wi-Fi Placement Studio v1.6 HTML.

This is a newly rebuilt app-window launcher, NOT the original EXE binary.
PyInstaller must bundle legacy/WiFi_Placement_Studio_v1.6_offline.html.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile
import shutil
import subprocess

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


def supported_app_browser() -> Path:
    """Find Edge or Chrome; --app opens a chrome-less desktop-style window."""
    if os.name != "nt":
        raise OSError("This EXE launcher runs on Windows only")
    bases = [
        Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")),
        Path(os.environ.get("PROGRAMFILES", "C:/Program Files")),
        Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))),
    ]
    candidates = [
        base / relative
        for relative in (
            "Microsoft/Edge/Application/msedge.exe",
            "Google/Chrome/Application/chrome.exe",
        )
        for base in bases
    ]
    for cmd in ("msedge.exe", "chrome.exe"):
        found = shutil.which(cmd)
        if found:
            candidates.append(Path(found))
    try:
        import winreg
        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for executable in ("msedge.exe", "chrome.exe"):
                key_path = rf"Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{executable}"
                try:
                    with winreg.OpenKey(root, key_path) as key:
                        location, _ = winreg.QueryValueEx(key, None)
                        candidates.append(Path(location))
                except OSError:
                    continue
    except ImportError:
        pass
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "Microsoft Edge or Google Chrome is required for the original-style app window."
    )


def app_window_command(browser: Path, target: Path) -> list[str]:
    """Launch a standalone *app-mode window*, never a browser tab."""
    return [str(browser), "--app=" + target.resolve().as_uri(), "--window-size=1440,900"]


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
            browser = supported_app_browser()
            command = app_window_command(browser, source)
            if not command[1].startswith("--app=file:///") or any("--new-tab" in x for x in command):
                raise ValueError("Browser app-window command is malformed")
            return 0
        target = publish_html(source)
        browser = supported_app_browser()
        # The historical EXE used an Edge/Chrome app-style window instead of
        # opening a tab in the default web browser. Match that interaction.
        # PyInstaller's bundled HTML is copied before the launcher exits.
        subprocess.Popen(app_window_command(browser, target), close_fds=True)
        return 0
    except Exception as exc:
        report_error(exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
