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


## Mobile interaction and accessibility QA — 2026-11-11

**Code/test SHA:** `cb6112a0612d8d3700d0134299d2fb8aa5aba322`  
**GitHub Actions:** https://github.com/jkd04255/wifi/actions/runs/42984403224 — **completed/success**.

- Python unit/contracts **94/94 PASS**; Playwright Chromium and WebKit desktop/mobile **21/21 PASS**; **115/115 total**.
- `preview/stage3.html` **touch interaction**: CSS `touch-action:none` on drawing canvas, touch-aware hit target radius (34 CSS px vs mouse 19px); one primary pointer at a time, 10px touch / 5px mouse movement threshold to prevent accidental drags and unnecessary undo. Continuous drag follows unsnapped X-Z coordinates, maintains finger-to-center offset, clamps center to floor by pin radius, and commits exactly one Undo on movement. Pointer cancellation restores prior coordinate.
- **Overlapping pins**: repeated taps cycle through hit-tested pins without making duplicate pins. Drag moves the selected pin; an explicit labeled select and “다음 핀” button provide deterministic selection even when pins overlap. Selected pin receives a higher contrast outline; status reads number and coordinates.
- **Accessibility**: `#requiredPinSelect` and `#requiredNextPin` have 44px minimum target height; selected radius input has `aria-label`, description link, value text, keyboard arrow-key support and visible focus. The active selection status is announced via a polite live region.
- **Browser tests added**: `test_mobile_touch_pin_drag_and_single_step_undo_both_engines`, `test_mobile_overlapping_pins_cycle_and_explicit_picker_both_engines`, `test_mobile_pin_accessibility_keyboard_radius_and_touch_targets`, `test_mobile_touch_jitter_does_not_create_undo_move`. Mobile tests use an emulated touchscreen for true taps and synthetic PointerEvent sequences to check drag handlers; **they do not substitute actual iPhone Safari/device tests**.
- Existing wall/sketch, brush (+100/0/-100), 17 mandatory samples, 70/100 hard constraints, local API and JSON import/export regression tests retained.
- No `index.html`/v1.6 legacy change, no GitHub Pages deployment and no main merge. Parent Draft PR #2 and this Draft PR #3 remain **GATE 3 HOLD** until 1/2/3-team contracts and physical verification are provided.


## GATE 3 mobile exception hardening — 2026-11-11

**Verified code/test commit:** `edd06870fe22c2b55945dd873f5a0e909c7b2017`  
**GitHub Actions:** https://github.com/jkd04255/wifi/actions/runs/42986058154 — `completed / success`  
Python **94/94**, Chromium/WebKit **25/25**, total **119/119 PASS**.

### Defects and UX protections resolved
- A secondary touch pointer's move event no longer updates the active required-pin drag's hover/coordinate UI or steals its pointer session; only the primary pointer may finish or cancel the original drag.
- A cancelled required-pin drag restores the original X-Z coordinates and removes the intermediate Undo snapshot. A later touch is still accepted.
- The required-pin picker always points to an actually existing selected pin after import, deletion or Undo instead of displaying an unselected implicit first option.
- The selected ring is painted *after other pins* so an overlapping pin cannot hide selection feedback, and pin layers remain visible above the brush/walls in the isolated preview.
- The editor canvas is keyboard-focusable (`tabindex=0`, accessible label/description). With the required tool selected, **Enter/Space** adds one center pin when none exist; arrow keys nudge the selected pin **0.1m**, Shift+arrow **0.5m**, constrained to floor bounds. Each real nudge supports Undo.
- Import, drawing, and preexisting priority brush `+100 / 0 / -100`, wall and Python optimizer contracts were not replaced. The **70/100 mandatory quality requirement at 17 points per pin** remains unchanged.

### Regression tests added
- `test_mobile_secondary_touch_does_not_steal_active_pin_drag`: second touch press/move/cancel during primary move, pin count and one-step Undo, Chromium and WebKit.
- `test_mobile_cancelled_drag_restores_pin_without_extra_undo`: touch drag cancel, no ghost Undo entry, next touch succeeds, Chromium and WebKit.
- `test_required_pin_keyboard_create_nudge_boundary_and_undo`: focusable canvas, Enter creation, arrow-key nudge, Shift accelerated nudge, 70-point persistence and two-step Undo, Chromium and WebKit.
- `test_imported_overlaps_picker_remains_synced_after_delete`: two overlapping imported pins, remove selected pin, remaining selection and screen-reader status match, Chromium and WebKit.
- Existing 21 browser regressions and 94 Python/contract tests were retained and passed.
- Touch drag streams in Playwright are **synthetic PointerEvents**, while tap emulation uses a touchscreen. Real iPhone Safari multitouch/VoiceOver remains **unverified**.

### GATE policy
**GATE 3 HOLD:** 1번 official floor/footprint, 2번 actual `/simulate` schema/source and 3번 measurement-calibration schema/source are not checked into this repo; `docs/TEAM_CONTRACT_TEMPLATE.md` is still PROPOSED/UNVERIFIED.
No code was integrated from those sources, and no actual RSSI calibration is claimed. Draft PR #2 and #3 stay unmerged, `main/index.html` and legacy v1.6 unchanged, no GitHub Pages redeployment.


## Undo history capacity and exact keyboard-edge regression — 2026-11-11

**Verified HEAD:** `ee542b751b9eda123fe13d3bfefb41a3ec3ca928`  
**GitHub Actions:** [#42987876155](https://github.com/jkd04255/wifi/actions/runs/42987876155) — completed/success.  
Python **94/94 PASS**; Playwright browser suite **27/27 PASS** (Chromium and WebKit, including dual-engine mobile pin cases).

### Additional defect found and fixed
A touch drag previously called `pushUndo()` as soon as the movement threshold was crossed. If the 30-entry Undo stack was full, this shifted out the oldest snapshot; `pointercancel` then popped the new snapshot, but could not restore the evicted oldest entry. The cancelled gesture therefore silently reduced the user's undo history by one.

- Drag now stages its pre-drag JSON snapshot without changing the Undo stack.
- A normal `pointerup` commits exactly one snapshot through the same bounded-history helper.
- `pointercancel` restores the original X-Z center and does not mutate Undo history; the pointer label explains the rollback.
- No-op keyboard nudges at the floor edge do not create an Undo entry.

### New regression cases
- `test_cancelled_drag_preserves_full_undo_history`: fill the 30-step history, cancel a real-handler touch drag after threshold, then verify the 29th and 30th Undo states. Chromium and WebKit.
- `test_keyboard_nudge_stops_at_pin_radius_and_noop_keeps_undo`: keyboard movement reaches the right and lower floor boundaries exactly at the pin radius; another nudge is a no-op and one Undo restores the previous valid coordinate. Chromium and WebKit.
- Existing multi-touch isolation, pointer cancellation rollback, overlapping pin selection, import/delete selection reconciliation, keyboard creation/movement, wall/brush and optimizer hard-constraint regressions remain included.

### Scope and remaining limitations
- Existing `main/index.html`, legacy v1.6, concrete-wall drawing, +100/0/-100 importance brush, and 70/100 mandatory-pin hard constraint remain unchanged.
- 1/2/3-team signed-off contracts remain absent; no actual RSSI prediction/calibration source was connected. Local preview continues to identify v1.6 estimates as uncalibrated.
- Synthetic touch PointerEvents and browser emulation are not actual iPhone Safari/VoiceOver hardware validation.
- **GATE 3 HOLD**: Draft PR #2/#3 remain unmerged; no main update or Pages deployment.
