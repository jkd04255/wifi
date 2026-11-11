# Offline HTML / Windows EXE packaging — isolated prototype

Updated: 2026-11-11 (KST). Branch: `feat/point-pin-heightless-offline-exe`.

## Outputs

The workflow `.github/workflows/build-windows-offline.yml` builds an Actions artifact `wifi-studio-real-exe-and-html` containing:

- `WiFi_Placement_Studio.html`: single UTF-8 HTML file with embedded JS/CSS, designed to open in a modern browser offline.
- `WiFi_Placement_Studio.exe`: an actual Windows x64 PE32+ GUI executable, compiled with MSVC /MT, which embeds the same HTML in a Win32 RCDATA resource. At runtime it extracts to `%LOCALAPPDATA%\\WiFiPlacementStudio\\studio_offline.html` and launches Microsoft Edge in `--app` window mode (or the default browser if Edge is unavailable). Python, Node and localhost servers are **not** required by the deliverable. Browser itself is required. It is **not** a fake EXE with HTML extension.
- Windows SmartScreen may warn about a new **unsigned** executable. No code signing certificate is configured.

## Current user requirements

- Geometry remains X-Z floor plan; Y is independent receiver/router elevation (nonnegative). Do not cap Y by ceiling height.
- All wall intersections in RSSI use a concrete barrier on the X-Z plane without vertical wall-height clipping.
- The `신호 세기` tool places a **single point**, not a radius. Each new pin defaults to **4 bars (at least 64/100)**; selecting an existing pin opens a palette dropdown for 4/3/2/1/0 bars with respective minimum predicted quality scores **64/42/27/9/0**. These bar thresholds are project-specific display categories, not manufacturer-native phone bar readings. A marker is only a visual icon, never a sampled region. Each pin has an independent **hard optimization constraint**.
- LAN-port coordinates and cable budgets are neither shown nor used in the new **offline JS optimizer**. Existing separate GATE 2 Python API still has cable constraints; this is an isolated new user-directed offline configuration, not an undocumented rewrite of the previously approved backend.
- Legacy room-purpose UI is still absent. Importance brushes (+100, 0, -100), wall drawing and erasing, export/import and heatmap remain present.
- Point-pin JSON export uses `{id,x,z,signalBars:4,minQualityScore:64}` by default; each pin retains its own selected `signalBars` and matching `minQualityScore`. Older imports with `minQualityScore:70` map to 4 bars (64 points), and obsolete radius metadata is discarded.
- Coordinates are rectangular floor extents pending the 1번 team's authoritative footprint; actual floor shape, 2번 engine, 3번 measured correction, real physical signal quality assurance are NOT verified.

## QA / project gate

- The isolated new page is `preview/stage4_offline.html`; the original `index.html`, immutable `legacy/WiFi_Placement_Studio_v1.6_offline.html`, Draft PR #3 and main/Pages are untouched.
- Workflow validates each inline JavaScript block with Node and verifies a real Windows PE executable with MZ signature; browser test coverage in `backend/tests_browser/test_stage4_offline.py` checks keyboard/mouse pin creation, five signal-bar thresholds, independent pin settings, legacy JSON import, high receiver Y and optimization without LAN inputs.
- Verified Windows compile is not the same as running the EXE on a physical Windows PC; that remains to be checked.
- Keep Draft PR #6 and the parent PR #3 **unmerged**, and do not redeploy Pages pending GATE 3 team contracts and real integration QA.

## How to retrieve

Open the latest successful **Lightweight standalone HTML and Windows EXE** run on the feature branch, and download the artifact named **wifi-studio-real-exe-and-html** from its Artifacts section. Extract ZIP; Windows users open the EXE, other users open the HTML directly.

