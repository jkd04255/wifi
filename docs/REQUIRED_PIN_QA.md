# Required Area Pin — GATE 3 QA (Draft PR #3)

Date: 2026-11-11 (KST)  
Feature: `feat/optimizer-required-pin` based on `feat/optimizer-stage3-integration` (Draft PR #2).  
Status: **LOCAL PREVIEW TESTED · GATE 3 FULL INTEGRATION HOLD**.

## Requested UI change

- Removed the **room purpose** tool, the room-label/importance drawer and the room-purpose legend from the **isolated** `preview/stage3.html`. Existing legacy v1.6 `index.html` and `legacy/WiFi_Placement_Studio_v1.6_offline.html` are unchanged.
- Added the **필수영역** pin tool. Click the floor-plan to place a circular pin, set radius **0.3–3.0m** (default 0.8m, up to 12 pins). Each pin can be removed from the existing element list and is included in undo/JSON export/import and floor scale changes.
- Old room-purpose `zones` in imported layout JSON are intentionally **not imported into the new prototype**, with visible toast notice.
- A pin immediately selects the **local Python API demo mode**, but still requires explicit LAN port X/Z/Y and cable budget inputs. No silent fallback to old JS optimization.
- The current router's minimum predicted quality over pin samples is shown, and rings change appearance depending on the predicted pass/fail.
- If a proposed AP fails the mandatory criterion, optimizer does not recommend it even when its overall weighted score is high.

## Hard constraint algorithm

- Quality per predicted RSSI sample: `quality = clamp((rssi_dBm + 90) / 55 * 100, 0, 100)` — the same score mapping as the existing v1.6 engine.
- **70 points corresponds to -51.5 dBm** on this specific model scale, not to an externally calibrated throughput requirement.
- Per pin, **17 sample locations** are evaluated: center + eight samples at half radius + eight samples along circumference. Each sample is marked `minQualityScore: 70` within optimizer `probes`.
- Python `OptimizeRequest` accepts an optional `probes[].minQualityScore`, and rejects every candidate violating **any** mandatory sample. Even a high-scoring `current` position cannot bypass these constraints.
- If no candidate meets all mandatory samples and physical/cable constraints, the UI shows a clear **not feasible** message and leaves no stale BEST recommendation.
- **Important limitation:** A finite set of 17 sampled points cannot mathematically guarantee quality throughout a continuous circular area. Actual RSSI is also uncalibrated. The UI says this explicitly. The floor boundary is currently approximated by a rectangle.

## How to test the isolated preview

```bash
git clone https://github.com/jkd04255/wifi.git
cd wifi
git switch feat/optimizer-required-pin
cd backend
python -m pip install -r requirements.txt
python -m uvicorn dev_server:app --host 127.0.0.1 --port 8001
```

Open **http://127.0.0.1:8001/preview/stage3.html** in the browser.

Select **필수영역** → adjust radius → click floor-plan → Apply → expand local API constraints and enter LAN details → **최고의 위치 찾기**. The public GitHub Pages remains the old v1.6 demo and **does not** yet show this feature.

## Verified QA

Initial relevant GitHub Actions CI: https://github.com/jkd04255/wifi/actions/runs/42977957957

- Python backend + contract tests: **94/94 PASS**.
- Chromium/WebKit Playwright browser suite: **12/12 PASS**.
- Total: **106/106 PASS** at commit `c25dade0cf669aee47ff0104995557c393a2bad6`.
- Checks include threshold exact boundary, all pin samples, current-location bypass block, backwards compatibility when no pins, click-to-place pin, 17 mandatory sample payload, removal, legacy mode blocking, existing original regression.
- A previous CI run at `39a5d4e` failed because the browser test read `inner_text()` from a collapsed details section; after updating the test to inspect DOM text the full suite passed.
- Later UI copy change at `b13775a0` only clarifies local API usage and old zone import and must be verified against the same suite.

## Gate policy

Main branch and deployed Pages remain unchanged. PR #3 is Draft and based on Draft PR #2. Do **not** merge or deploy until integration contracts, real signal source, exterior footprint and full approval are verified. The proposed `minQualityScore` is compatible with requests that omit it.

Remaining decisions: Continuous-area accuracy sampling vs verification, 2/3-team actual contracts, real measured RSSI calibration, physical phone QA and deployment architecture.
