# v1.6 offline downloads — archived HTML and rebuilt Windows launcher

Status: **Original HTML preserved · rebuilt Windows launcher is NOT the historical executable**  
Date: 2026-11-11 (KST)  
Branch: `feat/optimizer-legacy-downloads` (isolated from GATE 3).

## Deliverables

1. **Original, unmodified HTML**: `legacy/WiFi_Placement_Studio_v1.6_offline.html` (same Git blob SHA as `main/index.html`).
2. **Rebuilt Windows 10/11 x64 launcher**: `WiFi_Placement_Studio_v1.6_Windows_Rebuilt.exe`. This file is built anew via PyInstaller on a Windows GitHub Actions runner, from `tools/wifi_offline_launcher.py`. It is **not** a recovered or byte-for-byte identical copy of an original v1.6 EXE.
3. GitHub Actions artifact `WiFi_Placement_Studio_v1.6_Windows_and_HTML` bundles both files into a ZIP downloadable from the successful workflow run.

## How it works

- The new EXE bundles the unchanged HTML file and copies it to `%LOCALAPPDATA%\WiFi Placement Studio\v1.6\WiFi_Placement_Studio_v1.6_offline.html` before opening it using the system's default browser.
- This is an **offline browser-based launcher**, not a native embedded-browser application; it has no live 2/3-team RSSI or Python GATE 3 backend.
- Windows does not need a separately installed Python runtime.
- The EXE is unsigned; Windows SmartScreen may warn. Only run binaries obtained directly from the official repository's own GitHub Actions run.
- For direct browser use, open the HTML file without installing anything.
- The EXE's `--self-test` mode validates the embedded HTML without opening the browser, and the CI verifies the genuine MZ/PE header and checks the source HTML's SHA-256.

## Build provenance and limitations

The previous Library item `WiFi_Placement_Studio_v1.6.exe` is indexed with HTML MIME/content, and its original binary bytes were not accessible for verified recovery. Therefore **do not relabel HTML to .exe or represent this rebuilt launcher as the old original Windows executable**.

Source for the offline HTML is `main/legacy/WiFi_Placement_Studio_v1.6_offline.html`, unchanged. Windows GitHub Actions creates and tests a real PE file; no claim is made that the application's GUI has been manually exercised on an actual user's Windows hardware.

## Download steps

1. Open the latest successful `Rebuild preserved v1.6 Windows offline package` run from **Actions**.
2. Under **Artifacts**, download `WiFi_Placement_Studio_v1.6_Windows_and_HTML`.
3. Extract ZIP to a folder and run `WiFi_Placement_Studio_v1.6_Windows_Rebuilt.exe`, or double-click the HTML directly.

## GATE policy

The original HTML and `main/index.html` are immutable here. This is a separate packaging-only feature branch, not a merger or Pages deployment. **GATE 3 HOLD, Draft PR #2/#3, and all 1/2/3-team contract restrictions remain unchanged.**
