# Mandatory area 70-point desktop distribution (GATE 3 local demo only)

Status: **User-requested new feature distribution, isolated draft branch. Never merge main / deploy Pages without GATE approval.**

Based on original `feat/optimizer-required-pin` Draft PR #3 (code SHA `37d8d7f0d830489256b4fa3474de1994e5da354d`).

## What is included

- **`WiFi_Placement_RequiredPin_70.exe`** — newly built Windows 10/11 self-contained desktop app using pywebview WebView2. Its embedded FastAPI/Python local-only optimizer binds to `127.0.0.1` on a randomly selected free local port. It shows a dedicated application window; it does not open an ordinary browser tab.
- **`WiFi_Placement_RequiredPin_70.html`** — updated drawing UI for direct browser use: **room-purpose drawing controls removed, required-area pins present**, radius 0.3–3m, mobile/keyboard changes, predicted minimum quality indication and heatmap. When opened as a `file://` HTML, the 70-point constrained `/optimize` endpoint is not available; the file states clearly that the EXE is required for this feature.
- **Original, unchanged** `main/index.html` and `legacy/WiFi_Placement_Studio_v1.6_offline.html` are NOT the files shipped as this new feature release.

## Mandatory pin semantics

- The **필수영역** tool adds a pin to the floor plan with adjustable circle radius.
- Each pin uses center plus two rings of eight points (17 predicted RSSI samples).
- Every sample must have quality at least **70/100** under the bundled v1.6 local RSSI model. This equals around **−51.5 dBm** on that model's score mapping.
- Python optimizer treats the condition as a hard constraint, **never just a weighting bonus**. If no physical/cable-feasible candidate passes all pin samples, it returns no recommendation.
- The app requires the operator to enter the LAN port and cable budget for the local 4th-member optimizer.
- **Limitations:** 17 sampled points do not mathematically guarantee continuous-circle RF quality. This is model-predicted, not measured or calibrated. Formal 1/2/3 team contracts remain unverified.

## Why another EXE?

The previous re-upload was **the old v1.6 HTML wrapped in an EXE**, with no mandatory pin; this was the wrong artifact. This packaging build instead bundles the **actual Draft PR #3 `preview/stage3.html`** and local `backend/optimizer` API. The HTML-alone file has the pin UI but cannot enforce cable/mandatory 70 optimizer without that local API.

## Local build / QA

Windows CI installs Python 3.12, FastAPI/Uvicorn/Pydantic, pywebview 5.4, and PyInstaller 6.16, then bundles the stage3 HTML and Python optimizer.

The build verifies:
- MZ/PE header of real Windows EXE.
- Package HTML includes `data-tool="required"`, `requiredRadius`, and `minQualityScore`, and excludes `data-tool="zone"`/`roomDrawer`.
- `EXE --self-test` reads the **bundled HTML** and confirms a candidate with RSSI −80 dBm is rejected by the **hard minimum 70** optimizer condition.
- For previous implementation: PR #3's Python 94 + Chromium/WebKit 27 = **121 automated checks PASS** at [Actions #42988340603](https://github.com/jkd04255/wifi/actions/runs/42988340603).
- GUI appearance/Windows hardware behavior and SmartScreen are not established by the automated self-test.

## How to run

Download the successful Windows workflow's `WiFi_RequiredPin_70_EXE_HTML` artifact and unpack it.
Run `WiFi_Placement_RequiredPin_70.exe`. Internet connectivity is not required; Windows WebView2 runtime (normally provided with Edge) is needed. A Windows SmartScreen warning may appear because this rebuilt EXE is not signed.

For an **HTML-only preview**, open `WiFi_Placement_RequiredPin_70.html`. Do not claim the hard constraint's optimizer works from `file://`: use the EXE for a complete local run.

## Approval / safety constraints

This package lives only in `feat/optimizer-required-pin-distribution`. It does **not** merge Draft PR #3 or #2 into main, overwrite legacy v1.6 HTML, change importance brush/concrete walls, or deploy GitHub Pages. **GATE 3 HOLD** remains.
