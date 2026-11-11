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


## Final regression after JSON roundtrip coverage — 2026-11-11

**Final functional/code SHA:** `68b5622b85192cad4ef49a94f49859b7a01e3f51`  
**GitHub Actions:** https://github.com/jkd04255/wifi/actions/runs/42978598628 — `completed / success`.

- Python unittest **94/94** passed.
- Browser Playwright Chromium/WebKit **13/13** passed.
- **Total 107/107** checks passed.
- New browser case `test_import_export_preserves_required_pins_and_drops_old_rooms` confirms required pins persist in JSON and legacy room-purpose zones are not restored.
- Old wall/brush/RSSI prediction and local optimizer regressions also passed.
- Hardware/real RSSI and full continuously sampled disk are **not verified**. Draft PR #3 and parent PR #2 remain HOLD.


## UI/UX follow-up: draggable pins, selected radius, quality cards (2026-11-11)

**Verified application/test code SHA:** `18c998114a194bf040af002c9dbaf678f6c5a0ef`  
**GitHub Actions:** https://github.com/jkd04255/wifi/actions/runs/42982663205 — **completed / success**.

- Python existing backend/contract regression **94/94 passed**.
- Playwright Chromium & WebKit browser regression **17/17 passed**.
- **111/111 total tests passed**.

### Implemented
- `preview/stage3.html` now supports selection of an existing mandatory-area pin by clicking its center and dragging it within the valid floor boundary, without creating a duplicate. Dragging records a single Undo step when the position actually changes, and pointer cancellation restores the original coordinate.
- Selecting an existing pin reveals `#requiredSelectedControls` and `#selectedRequiredRadius` with a 0.3–3.0m range. Invalid radii extending beyond the floor bounds are rejected; valid edits support Undo.
- Result panel `#requiredResults` displays each pin's radius, minimum current quality score, pass/fail vs 70, and — only after successful local Python optimization — minimum predicted score at the recommended position and pass/fail. It distinguishes **current** from **recommended** placement, and labels the entire panel **uncalibrated model predictions only**.
- Any layout/pin edit or failed optimizer request clears the old recommendation and does not leave a stale recommended score.
- No change to legacy room-purpose removal, pin 17-sample hard constraint, importance brush, walls, v1.6 predictions or existing API contract.

### Browser coverage added
- Chromium & WebKit mouse drag position change, no duplicate pin, Undo back to exact original X-Z position.
- WebKit selected pin radius edit, Undo, floor-edge rejection.
- Local optimizer actual success displays **current vs recommended** quality and 70-point status cards.
- A subsequent edit removes stale "recommended" scores until optimization is run again.

### Manual local preview
```bash
git clone https://github.com/jkd04255/wifi.git
cd wifi
git switch feat/optimizer-required-pin
cd backend
python -m pip install -r requirements.txt
python -m uvicorn dev_server:app --host 127.0.0.1 --port 8001
```
Open `http://127.0.0.1:8001/preview/stage3.html`. Click the **필수영역** tool; place a pin, tap its center again and drag, then adjust the selected-pin radius in the open drawer. For the recommended score comparison, set LAN port location and cable budget, Apply, then use the **4번 Python API (로컬 시연)** optimizer mode.

### Remaining HOLD conditions
- All scores are from v1.6 synthetic/un-calibrated predictions, and 17 discrete samples do not guarantee the quality of every point inside the continuous disk.
- 1/2/3 teammate real data contracts, real wall/floor footprint, field measurements, actual iPhone Safari and Python production deployment remain unverified.
- **Draft PR #3 stays unmerged. Main and GitHub Pages remain v1.6 and must NOT be updated under this gate.**
