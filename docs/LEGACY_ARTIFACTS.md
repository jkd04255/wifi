# v1.6 offline downloads — archived HTML and rebuilt Windows launcher

Status: **Original HTML preserved · corrected app-window EXE is NOT the historical executable**  
Date: 2026-11-11 (KST)  
Branch: `feat/optimizer-legacy-downloads` (isolated from GATE 3).

## Deliverables

1. **Original, unmodified HTML**: `legacy/WiFi_Placement_Studio_v1.6_offline.html` (same Git blob SHA as `main/index.html`).
2. **Rebuilt Windows 10/11 x64 launcher**: `WiFi_Placement_Studio_v1.6_App_Window.exe`. This file is built anew via PyInstaller on a Windows GitHub Actions runner, from `tools/wifi_offline_launcher.py`. It is **not** a recovered or byte-for-byte identical copy of an original v1.6 EXE.
3. GitHub Actions artifact `WiFi_Placement_Studio_v1.6_AppWindow_and_HTML` bundles both files into a ZIP downloadable from the successful workflow run.

## How it works

- The new EXE bundles the unchanged HTML file and copies it to `%LOCALAPPDATA%\WiFi Placement Studio\v1.6\WiFi_Placement_Studio_v1.6_offline.html` before opening it with the installed Microsoft Edge or Google Chrome in app-window mode (`--app=file:///...`).
- This uses **Edge/Chrome app mode**: the existing offline v1.6 HTML opens in its own window without a normal browser tab or address bar. It is not a fully native embedded-browser binary; it has no live 2/3-team RSSI or Python GATE 3 backend.
- Windows does not need a separately installed Python runtime. **Microsoft Edge or Google Chrome must be installed** (Edge ships with typical Windows 10/11 installations).
- The EXE is unsigned; Windows SmartScreen may warn. Only run binaries obtained directly from the official repository's own GitHub Actions run.
- For direct browser use, open the HTML file without installing anything. The new EXE has an app-style standalone window; the previous rebuilt EXE accidentally opened an ordinary browser tab.
- The EXE's `--self-test` mode validates the embedded HTML and the available Edge/Chrome app command without opening a GUI window, and the CI verifies the genuine MZ/PE header and checks the source HTML's SHA-256.

## Build provenance and limitations

The previous Library item `WiFi_Placement_Studio_v1.6.exe` is indexed with HTML MIME/content, and its original binary bytes were not accessible for verified recovery. Therefore **do not relabel HTML to .exe or represent this rebuilt launcher as the old original Windows executable**.

Source for the offline HTML is `main/legacy/WiFi_Placement_Studio_v1.6_offline.html`, unchanged. Windows GitHub Actions creates and tests a real PE file; no claim is made that the application's GUI has been manually exercised on an actual user's Windows hardware.

## Download steps

1. Open the latest successful `Rebuild preserved v1.6 Windows offline package` run from **Actions**.
2. Under **Artifacts**, download `WiFi_Placement_Studio_v1.6_AppWindow_and_HTML`.
3. Extract ZIP to a folder and run `WiFi_Placement_Studio_v1.6_App_Window.exe`, or double-click the HTML directly.

## GATE policy

The original HTML and `main/index.html` are immutable here. This is a separate packaging-only feature branch, not a merger or Pages deployment. **GATE 3 HOLD, Draft PR #2/#3, and all 1/2/3-team contract restrictions remain unchanged.**

## Revision: restore the previous app-window experience

The initial rebuilt launcher opened the default web browser tab, unlike earlier v1.2/v1.6 Edge/Chrome app-style desktop windows. This revision uses an installed Edge or Chrome executable with `--app=file:///...` to show the same preserved v1.6 UI in a dedicated window with no URL/navigation toolbar. The EXE remains a **new rebuilt file**, not a recovered historical binary. Windows runner self-test covers PE format, HTML bundling and presence of an app-capable browser; full user-device GUI/SmartScreen behavior has not been manually verified.
