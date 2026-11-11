"""Browser-level regression for Stage 3 opt-in demo.

Only checks the local v1.6-estimate preview; never claims 2/3 team integration.
"""
from __future__ import annotations

import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
URL = "http://127.0.0.1:8001/preview/stage3.html"
HEALTH = "http://127.0.0.1:8001/health"


class Stage3BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "dev_server:app",
             "--host", "127.0.0.1", "--port", "8001"],
            cwd=BACKEND, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
        )
        for _ in range(100):
            try:
                with urllib.request.urlopen(HEALTH, timeout=1) as response:
                    if response.status == 200:
                        break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.1)
        else:
            cls.server.terminate()
            raise RuntimeError("Local Stage 3 API did not become ready")
        cls.playwright = sync_playwright().start()

    @classmethod
    def tearDownClass(cls):
        cls.playwright.stop()
        cls.server.terminate()
        try:
            cls.server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.server.kill()

    def open_page(self, engine="chromium", mobile=False):
        browser = getattr(self.playwright, engine).launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844} if mobile else
                                {"width": 1440, "height": 900}, has_touch=mobile)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        response = page.goto(URL, wait_until="load")
        self.assertEqual(response.status, 200)
        self.assertTrue(page.locator("#editorScreen").is_visible())
        page.locator("#applyBottomBtn").click()
        try:
            page.wait_for_function("document.body.dataset.view === 'analysis' && !document.getElementById('resultScreen').hidden", timeout=5000)
        except Exception as exc:
            raise AssertionError(
                "Did not enter analysis screen. JS pageerrors=" + repr(errors) +
                " state=" + str(page.evaluate("document.body.dataset.view")) +
                " analysisHidden=" + str(page.locator("#resultScreen").get_attribute("hidden")) +
                " scripts=" + str(page.locator("script").count())
            ) from exc
        page.locator("#optimizeBtn").wait_for(state="visible", timeout=5000)
        return browser, page, errors

    def test_chromium_local_optimizer_api(self):
        browser, page, errors = self.open_page()
        try:
            page.locator("#g3Settings summary").click()
            page.locator("#g3Mode").select_option("local")
            page.locator("#g3LanX").fill("0.5")
            page.locator("#g3LanZ").fill("0.5")
            page.locator("#g3LanY").fill("0.3")
            page.locator("#g3Cable").fill("30")
            page.locator("#optimizeBtn").click()
            page.wait_for_function("!document.getElementById('recommendation').hidden", timeout=30000)
            txt = page.locator("#recommendBody").inner_text()
            self.assertIn("케이블 예상 길이", txt)
            self.assertIn("v1.6 로컬 예측", txt)
            self.assertIn("추가 AP", txt)
            self.assertIn("4번 Python API", page.locator("#engineMode").inner_text())
            self.assertNotIn("최적화 실패", page.locator("#statusLine").inner_text())
            self.assertEqual(errors, [])
            # Existing apply-button flow should remain usable.
            page.locator("#useBestBtn").click()
            page.wait_for_function("document.getElementById('recommendation').hidden", timeout=30000)
        finally:
            browser.close()

    def test_webkit_legacy_flow_unchanged(self):
        browser, page, errors = self.open_page(engine="webkit")
        try:
            self.assertEqual(page.locator("#g3Mode").input_value(), "legacy")
            page.locator("#optimizeBtn").click()
            page.wait_for_function("!document.getElementById('recommendation').hidden", timeout=30000)
            self.assertIn("추천 좌표", page.locator("#recommendBody").inner_text())
            self.assertNotIn("케이블 예상 길이", page.locator("#recommendBody").inner_text())
            self.assertEqual(errors, [])
        finally:
            browser.close()

    def test_chromium_rejects_missing_lan_without_silent_fallback(self):
        browser, page, errors = self.open_page()
        try:
            page.locator("#g3Settings summary").click()
            page.locator("#g3Mode").select_option("local")
            page.locator("#optimizeBtn").click()
            page.wait_for_function("document.getElementById('statusLine').textContent.includes('최적화 실패')", timeout=10000)
            self.assertTrue(page.locator("#recommendation").is_hidden())
            self.assertIn("직접 입력", page.locator("#statusLine").inner_text())
            self.assertIn("자동으로 기존 모델로 바꾸지", page.locator("#g3ModeInfo").inner_text())
            self.assertEqual(errors, [])
        finally:
            browser.close()

    def test_mobile_chromium_preview(self):
        browser, page, errors = self.open_page(mobile=True)
        try:
            page.locator("#g3Settings summary").click()
            self.assertTrue(page.locator("#g3Mode").is_visible())
            page.locator("#g3Mode").select_option("legacy")
            page.locator("#optimizeBtn").click()
            page.wait_for_function("!document.getElementById('recommendation').hidden", timeout=30000)
            self.assertIn("추천 좌표", page.locator("#recommendBody").inner_text())
            self.assertEqual(errors, [])
        finally:
            browser.close()


    # Extend only the opt-in preview tests. This fixture is synthetic, not a 2/3-team contract.
    def _select_local(self, page, cable="20", lan_x="0.5", lan_z="0.5"):
        page.locator("#g3Settings summary").click()
        page.locator("#g3Mode").select_option("local")
        page.locator("#g3LanX").fill(lan_x)
        page.locator("#g3LanZ").fill(lan_z)
        page.locator("#g3LanY").fill("0.3")
        page.locator("#g3Cable").fill(cable)

    def _run_local(self, page):
        page.locator("#optimizeBtn").click()
        page.wait_for_function(
            "!document.getElementById('recommendation').hidden && !document.getElementById('optimizeBtn').disabled",
            timeout=45000,
        )
        self.assertIn("4번 Python API", page.locator("#engineMode").inner_text())
        self.assertIn("v1.6", page.locator("#recommendBody").inner_text())

    def _import_layout(self, page, layout):
        import json
        page.locator("#importFile").set_input_files({
            "name": "synthetic-stage3-layout.json",
            "mimeType": "application/json",
            "buffer": json.dumps(layout).encode("utf-8"),
        })
        page.wait_for_function(
            "document.body.dataset.view === 'design' && document.getElementById('statusLine').textContent.includes('XZ')",
            timeout=10000,
        )
        page.locator("#applyBottomBtn").click()
        page.wait_for_function("document.body.dataset.view === 'analysis'", timeout=10000)
        page.locator("#optimizeBtn").wait_for(state="visible", timeout=10000)

    @staticmethod
    def _fixture(walls=None, strokes=None):
        return {
            "schemaVersion": "1.1",
            "width": 6.0, "depth": 4.0, "roomHeightM": 2.7, "receiverY": 1.0,
            "router": {"x": 3.0, "z": 2.0, "y": 1.2, "frequency": 2.4,
                       "txPowerDbm": 20, "antennaGainDbi": 0},
            "walls": walls or [],
            "zones": [], "sketches": [], "importanceStrokes": strokes or [],
            "modelOverrides": {"pathLossExponent": 2.2, "wallScale": 1.0},
        }

    def test_webkit_local_api_full_flow(self):
        """New API path works in Safari engine, not only the old fallback."""
        browser, page, errors = self.open_page(engine="webkit")
        try:
            self._select_local(page, cable="30")
            self._run_local(page)
            self.assertIn("케이블 예상 길이", page.locator("#recommendBody").inner_text())
            self.assertIn("미보정", page.locator("#engineMode").inner_text())
            page.locator("#useBestBtn").click()
            page.wait_for_function("document.getElementById('recommendation').hidden", timeout=30000)
            self.assertEqual(errors, [])
        finally:
            browser.close()

    def test_24_and_5_ghz_send_different_predictions(self):
        """Changing band must modify the v1.6 estimate passed into the API."""
        browser, page, errors = self.open_page()
        requests = []
        page.on("request", lambda request: requests.append(request.post_data_json)
                if request.url.endswith("/optimize") else None)
        try:
            self._select_local(page, cable="30")
            page.locator("#frequencySelect").select_option("2.4")
            self._run_local(page)
            self.assertEqual(page.locator("#frequencySelect").input_value(), "2.4")
            pred_24 = requests[-1]["candidates"][0]["rssisDbm"]
            self.assertTrue(pred_24)
            page.locator("#frequencySelect").select_option("5")
            page.locator("#applyBtn").click()
            page.wait_for_function(
                "document.getElementById('heatmapBand').textContent.includes('5 GHz')",
                timeout=10000,
            )
            self._run_local(page)
            pred_5 = requests[-1]["candidates"][0]["rssisDbm"]
            self.assertEqual(page.locator("#frequencySelect").input_value(), "5")
            self.assertNotEqual(pred_24, pred_5)
            self.assertLess(pred_5[0], pred_24[0])
            self.assertEqual(errors, [])
        finally:
            browser.close()

    def test_imported_importance_brushes_all_three_priorities(self):
        """Red +100, green 0, blue -100 are transferred to the optimizer request."""
        strokes = [
            {"id": "important", "points": [[1, 0.4], [1, 3.6]], "radiusM": 1.0, "weightPct": 100},
            {"id": "neutral", "points": [[3, 0.4], [3, 3.6]], "radiusM": 0.9, "weightPct": 0},
            {"id": "low", "points": [[5, 0.4], [5, 3.6]], "radiusM": 1.0, "weightPct": -100},
        ]
        browser, page, errors = self.open_page()
        requests = []
        page.on("request", lambda request: requests.append(request.post_data_json)
                if request.url.endswith("/optimize") else None)
        try:
            self._import_layout(page, self._fixture(strokes=strokes))
            self._select_local(page, cable="20")
            self._run_local(page)
            priorities = [p["priorityPct"] for p in requests[-1]["probes"]]
            self.assertEqual(set(priorities), {-100, 0, 100})
            self.assertGreater(priorities.count(100), 0)
            self.assertGreater(priorities.count(-100), 0)
            self.assertIn("미보정", page.locator("#engineMode").inner_text())
            self.assertEqual(errors, [])
        finally:
            browser.close()

    def test_wall_and_cable_restrict_browser_generated_candidates(self):
        """Candidate endpoint must receive the concrete wall and honor cable budget."""
        wall = {"id": "barrier", "x1": 2, "z1": 0, "x2": 2, "z2": 3.1, "material": "concrete"}
        browser, page, errors = self.open_page()
        requests = []
        page.on("request", lambda request: requests.append(
            (request.url.split("/")[-1], request.post_data_json))
                if request.url.endswith("/optimize") or request.url.endswith("/candidate-locations") else None)
        try:
            self._import_layout(page, self._fixture(walls=[wall]))
            self._select_local(page, cable="3")
            self._run_local(page)
            first = [body for path, body in requests if path == "optimize"][-1]
            candidate_request = [body for path, body in requests if path == "candidate-locations"][-1]
            self.assertEqual(len(candidate_request["floor"]["walls"]), 1)
            self.assertEqual(candidate_request["floor"]["walls"][0]["x1"], 2)
            self.assertEqual(candidate_request["lanPort"]["maxCableLengthM"], 3)
            self.assertGreater(len(first["candidates"]), 0)
            self.assertTrue(all(c["position"]["x"] < 2 for c in first["candidates"]))
            page.locator("#g3Cable").fill("20")
            self._run_local(page)
            second = [body for path, body in requests if path == "optimize"][-1]
            self.assertGreater(len(second["candidates"]), len(first["candidates"]))
            self.assertTrue(any(c["position"]["x"] > 2 for c in second["candidates"]))
            self.assertEqual(errors, [])
        finally:
            browser.close()

    def test_api_errors_never_silently_fallback_or_reuse_stale_result(self):
        browser, page, errors = self.open_page()
        try:
            self._select_local(page, cable="30")
            self._run_local(page)
            self.assertTrue(page.locator("#recommendation").is_visible())

            page.route("**/optimize", lambda route: route.abort("failed"))
            page.locator("#optimizeBtn").click()
            page.wait_for_function(
                "document.getElementById('statusLine').textContent.includes('최적화 실패')",
                timeout=30000,
            )
            self.assertTrue(page.locator("#recommendation").is_hidden())
            self.assertIn("자동으로 기존 모델로 바꾸지", page.locator("#g3ModeInfo").inner_text())
            page.unroute("**/optimize")

            page.route("**/candidate-locations", lambda route: route.fulfill(
                status=503, content_type="application/json",
                body='{"detail":"temporary unavailable"}'))
            page.locator("#optimizeBtn").click()
            page.wait_for_function(
                "document.getElementById('statusLine').textContent.includes('최적화 실패')",
                timeout=30000,
            )
            self.assertIn("temporary unavailable", page.locator("#statusLine").inner_text())
            self.assertTrue(page.locator("#recommendation").is_hidden())
            self.assertEqual(page.locator("#g3Mode").input_value(), "local")
            # Aborted fetch is a network error, not a JavaScript page exception.
            self.assertEqual(errors, [])
        finally:
            browser.close()


    def _place_required_pin(self, page):
        page.locator("#backToEditorBtn").click()
        page.wait_for_function("document.body.dataset.view === 'design'", timeout=10000)
        self.assertEqual(page.locator('[data-tool="zone"]').count(), 0)
        self.assertEqual(page.locator("#roomDrawer").count(), 0)
        page.locator('[data-tool="required"]').click()
        self.assertTrue(page.locator("#requiredRadius").is_visible())
        canvas = page.locator("#editorCanvas")
        rect = canvas.bounding_box()
        canvas.click(position={"x": rect["width"] * .5, "y": rect["height"] * .5})
        # <details> is initially collapsed: inner_text() hides children; text_content reads the DOM.
        self.assertIn("필수영역", page.locator("#elementList").text_content())
        self.assertEqual(page.locator("#g3Mode").input_value(), "local")
        page.locator("#applyBottomBtn").click()
        page.wait_for_function("document.body.dataset.view === 'analysis'", timeout=10000)
        self.assertIn("필수영역 1곳", page.locator("#requiredStatus").inner_text())

    def test_mandatory_pin_creation_radius_and_payload_in_chromium(self):
        browser, page, errors = self.open_page()
        bodies = []
        page.on("request", lambda request: bodies.append(request.post_data_json)
                if request.url.endswith("/optimize") else None)
        try:
            self._place_required_pin(page)
            page.locator("#g3Settings summary").click()
            page.locator("#g3LanX").fill("0.5")
            page.locator("#g3LanZ").fill("0.5")
            page.locator("#g3LanY").fill("0.3")
            page.locator("#g3Cable").fill("30")
            page.locator("#optimizeBtn").click()
            page.wait_for_function(
                "!document.getElementById('optimizeBtn').disabled && "
                "(document.getElementById('statusLine').textContent.includes('추천') || "
                "document.getElementById('statusLine').textContent.includes('최적화 실패'))",
                timeout=45000,
            )
            self.assertTrue(bodies)
            mandatory = [p for p in bodies[-1]["probes"] if p.get("minQualityScore") == 70]
            self.assertEqual(len(mandatory), 17)
            self.assertTrue(all(p["targetDbm"] == -51.5 for p in mandatory))
            self.assertTrue(all(-150 <= v <= 30 for c in bodies[-1]["candidates"] for v in c["rssisDbm"]))
            if page.locator("#recommendation").is_visible():
                self.assertIn("17개 표본점 모두 70점 이상", page.locator("#recommendBody").inner_text())
            else:
                self.assertIn("필수영역", page.locator("#statusLine").inner_text())
            self.assertEqual(errors, [])
        finally:
            browser.close()

    def test_pin_requires_local_api_no_legacy_silent_success(self):
        browser, page, errors = self.open_page(engine="webkit")
        try:
            self._place_required_pin(page)
            page.locator("#g3Settings summary").click()
            page.locator("#g3Mode").select_option("legacy")
            page.locator("#optimizeBtn").click()
            page.wait_for_function(
                "document.getElementById('statusLine').textContent.includes('최적화 실패')",
                timeout=15000)
            self.assertTrue(page.locator("#recommendation").is_hidden())
            self.assertIn("필수영역 70점 조건", page.locator("#statusLine").inner_text())
            self.assertEqual(errors, [])
        finally:
            browser.close()

    def test_pin_import_and_removal_no_room_purpose_ui(self):
        browser, page, errors = self.open_page()
        try:
            self._place_required_pin(page)
            page.locator("#backToEditorBtn").click()
            page.locator("#elementsDrawer summary").click()
            self.assertIn("필수영역", page.locator("#elementList").inner_text())
            # Remove the required pin via its existing element-row delete action.
            page.locator("#elementList .element").filter(has_text="필수영역").locator("button").click()
            self.assertNotIn("◎ 필수영역", page.locator("#elementList").inner_text())
            page.locator("#applyBottomBtn").click()
            page.wait_for_function("document.body.dataset.view === 'analysis'", timeout=10000)
            self.assertIn("필수영역 없음", page.locator("#requiredStatus").inner_text())
            self.assertEqual(errors, [])
        finally:
            browser.close()



    def test_import_export_preserves_required_pins_and_drops_old_rooms(self):
        """Old purpose zones must not return, while mandatory pins survive JSON roundtrip."""
        import json
        browser, page, errors = self.open_page()
        try:
            layout = self._fixture()
            layout["zones"] = [{
                "id": "old-bedroom", "x1": 0.2, "z1": 0.2,
                "x2": 1.5, "z2": 1.5, "label": "침실", "weightPct": 100
            }]
            layout["requiredPins"] = [{
                "id": "must-70", "x": 3.0, "z": 2.0,
                "radiusM": 0.8, "minQualityScore": 70
            }]
            page.locator("#importFile").set_input_files({
                "name": "fixture-with-legacy-zone.json",
                "mimeType": "application/json",
                "buffer": json.dumps(layout).encode("utf-8"),
            })
            page.wait_for_function(
                "document.body.dataset.view === 'design' && "
                "document.getElementById('statusLine').textContent.includes('XZ')",
                timeout=10000,
            )
            self.assertEqual(page.locator('[data-tool="zone"]').count(), 0)
            self.assertEqual(page.locator("#g3Mode").input_value(), "local")
            with page.expect_download() as dl:
                page.locator("#exportBtn").click()
            exported = json.loads(dl.value.path().read_text(encoding="utf-8"))
            self.assertEqual(len(exported["requiredPins"]), 1)
            self.assertEqual(exported["requiredPins"][0]["minQualityScore"], 70)
            self.assertEqual(exported["zones"], [])
            self.assertEqual(errors, [])
        finally:
            browser.close()




    def _export_current_layout(self, page):
        import json
        with page.expect_download() as dl:
            page.locator("#exportBtn").click()
        return json.loads(dl.value.path().read_text(encoding="utf-8"))

    def _drag_pin_to(self, page, pin, layout, new_x, new_z):
        bounds = page.locator("#editorCanvas").bounding_box()
        start_x = bounds["x"] + bounds["width"] * pin["x"] / layout["width"]
        start_z = bounds["y"] + bounds["height"] * pin["z"] / layout["depth"]
        end_x = bounds["x"] + bounds["width"] * new_x / layout["width"]
        end_z = bounds["y"] + bounds["height"] * new_z / layout["depth"]
        page.mouse.move(start_x, start_z)
        page.mouse.down()
        page.mouse.move(end_x, end_z, steps=8)
        page.mouse.up()

    def test_drag_existing_required_pin_and_undo_in_both_engines(self):
        """Dragging the pin center moves exactly one existing pin; one undo restores it."""
        for engine in ("chromium", "webkit"):
            with self.subTest(engine=engine):
                browser, page, errors = self.open_page(engine=engine)
                try:
                    self._place_required_pin(page)
                    page.locator("#backToEditorBtn").click()
                    page.wait_for_function("document.body.dataset.view === 'design'", timeout=10000)
                    layout = self._export_current_layout(page)
                    original = layout["requiredPins"][0]
                    self._drag_pin_to(page, original, layout, original["x"] + 1, original["z"] + .5)
                    shifted = self._export_current_layout(page)["requiredPins"][0]
                    self.assertEqual(len(self._export_current_layout(page)["requiredPins"]), 1)
                    self.assertGreater(shifted["x"], original["x"] + .1)
                    self.assertGreater(shifted["z"], original["z"] + .1)
                    self.assertAlmostEqual(shifted["radiusM"], original["radiusM"])
                    self.assertIn("위치를 변경", page.locator("#statusLine").inner_text())
                    page.locator("#undoBtn").click()
                    restored = self._export_current_layout(page)["requiredPins"][0]
                    self.assertAlmostEqual(restored["x"], original["x"], delta=.001)
                    self.assertAlmostEqual(restored["z"], original["z"], delta=.001)
                    self.assertEqual(errors, [])
                finally:
                    browser.close()

    def test_selected_pin_radius_change_and_invalid_size_rejected(self):
        browser, page, errors = self.open_page(engine="webkit")
        try:
            self._place_required_pin(page)
            page.locator("#backToEditorBtn").click()
            page.wait_for_function("document.body.dataset.view === 'design'", timeout=10000)
            self.assertTrue(page.locator("#requiredSelectedControls").is_visible())
            self.assertEqual(page.locator("#selectedRequiredRadius").input_value(), "0.8")
            page.locator("#selectedRequiredRadius").evaluate(
                "(input) => {input.value='1.2';"
                "input.dispatchEvent(new Event('input',{bubbles:true}));"
                "input.dispatchEvent(new Event('change',{bubbles:true}));}")
            self.assertAlmostEqual(self._export_current_layout(page)["requiredPins"][0]["radiusM"], 1.2, delta=.001)
            self.assertIn("1.2 m", page.locator("#selectedRequiredRadiusValue").inner_text())
            page.locator("#undoBtn").click()
            self.assertAlmostEqual(self._export_current_layout(page)["requiredPins"][0]["radiusM"], .8, delta=.001)

            layout = self._export_current_layout(page)
            self._drag_pin_to(page, layout["requiredPins"][0], layout, 1, 1)
            moved_pin = self._export_current_layout(page)["requiredPins"][0]
            self.assertAlmostEqual(moved_pin["x"], 1, delta=.05)
            page.locator("#selectedRequiredRadius").evaluate(
                "(input) => {input.value='2.0';"
                "input.dispatchEvent(new Event('input',{bubbles:true}));"
                "input.dispatchEvent(new Event('change',{bubbles:true}));}")
            self.assertAlmostEqual(self._export_current_layout(page)["requiredPins"][0]["radiusM"], .8, delta=.001)
            self.assertEqual(page.locator("#selectedRequiredRadius").input_value(), "0.8")
            self.assertEqual(errors, [])
        finally:
            browser.close()

    def _run_recommendation_for_required_pin(self, page):
        page.locator("#powerInput").fill("35")
        page.locator("#powerInput").press("Tab")
        self._place_required_pin(page)
        page.locator("#g3Settings summary").click()
        page.locator("#g3LanX").fill("0.5")
        page.locator("#g3LanZ").fill("0.5")
        page.locator("#g3LanY").fill("0.3")
        page.locator("#g3Cable").fill("30")
        page.locator("#optimizeBtn").click()
        page.wait_for_function(
            "!document.getElementById('optimizeBtn').disabled && "
            "(document.getElementById('recommendation').hidden === false || "
            "document.getElementById('statusLine').textContent.includes('최적화 실패'))",
            timeout=45000)
        self.assertTrue(page.locator("#recommendation").is_visible(),
                        page.locator("#statusLine").inner_text())

    def test_pin_quality_panel_lists_current_and_recommendation(self):
        browser, page, errors = self.open_page()
        try:
            self._run_recommendation_for_required_pin(page)
            cards = page.locator("#requiredResults").inner_text()
            self.assertIn("필수영역 1", cards)
            self.assertIn("현재 최소", cards)
            self.assertIn("추천 최소", cards)
            self.assertIn("70점 충족", cards)
            self.assertIn("17개 표본점", cards)
            self.assertEqual(errors, [])
        finally:
            browser.close()

    def test_pin_quality_panel_clears_outdated_recommendation_on_edit(self):
        browser, page, errors = self.open_page()
        try:
            self._run_recommendation_for_required_pin(page)
            self.assertIn("추천 최소", page.locator("#requiredResults").inner_text())
            page.locator("#backToEditorBtn").click()
            page.wait_for_function("document.body.dataset.view === 'design'", timeout=10000)
            page.locator("#selectedRequiredRadius").evaluate(
                "(input) => {input.value='1.1';"
                "input.dispatchEvent(new Event('input',{bubbles:true}));"
                "input.dispatchEvent(new Event('change',{bubbles:true}));}")
            page.locator("#applyBottomBtn").click()
            page.wait_for_function("document.body.dataset.view === 'analysis'", timeout=10000)
            self.assertNotIn("추천 최소", page.locator("#requiredResults").inner_text())
            self.assertIn("현재 최소", page.locator("#requiredResults").inner_text())
            self.assertEqual(errors, [])
        finally:
            browser.close()


    # Mobile pointer cases intentionally use has_touch=True for real touchscreen taps.
    # Drag sequences are synthetic PointerEvents (not actual iPhone hardware gestures).
    def _mobile_touch_editor(self, engine):
        browser, page, errors = self.open_page(engine=engine, mobile=True)
        page.locator("#backToEditorBtn").click()
        page.wait_for_function("document.body.dataset.view === 'design'", timeout=10000)
        page.locator('[data-tool="required"]').click()
        self.assertTrue(page.locator("#requiredDrawer").is_visible())
        self.assertTrue(page.locator("#requiredRadius").is_visible())
        self.assertEqual(
            page.locator("#editorCanvas").evaluate("(el)=>getComputedStyle(el).touchAction"),
            "none",
        )
        return browser, page, errors

    def _touch_pointer_sequence(self, page, start, end, pointer_id=72):
        canvas=page.locator("#editorCanvas")
        base={
            "pointerId":pointer_id, "pointerType":"touch",
            "isPrimary":True, "button":0, "buttons":1,
        }
        canvas.dispatch_event("pointerdown", {**base,"clientX":start[0],"clientY":start[1]})
        for i in range(1,6):
            x=start[0]+(end[0]-start[0])*i/5
            y=start[1]+(end[1]-start[1])*i/5
            canvas.dispatch_event("pointermove", {**base,"clientX":x,"clientY":y})
        canvas.dispatch_event("pointerup", {**base,"buttons":0,"clientX":end[0],"clientY":end[1]})

    def test_mobile_touch_pin_drag_and_single_step_undo_both_engines(self):
        for engine in ("chromium","webkit"):
            with self.subTest(engine=engine):
                browser,page,errors=self._mobile_touch_editor(engine)
                try:
                    bounds=page.locator("#editorCanvas").bounding_box()
                    x=bounds["x"]+bounds["width"]*.5
                    y=bounds["y"]+bounds["height"]*.5
                    page.touchscreen.tap(x,y)
                    first=self._export_current_layout(page)
                    self.assertEqual(len(first["requiredPins"]),1)
                    self.assertTrue(page.locator("#requiredPinPicker").is_visible())
                    self.assertTrue(page.locator("#requiredSelectedControls").is_visible())
                    pin=first["requiredPins"][0]
                    px=bounds["x"]+bounds["width"]*pin["x"]/first["width"]
                    py=bounds["y"]+bounds["height"]*pin["z"]/first["depth"]
                    self._touch_pointer_sequence(page,(px,py),(px+35,py+24))
                    second=self._export_current_layout(page)
                    self.assertEqual(len(second["requiredPins"]),1)
                    self.assertGreater(second["requiredPins"][0]["x"],pin["x"]+.1)
                    self.assertGreater(second["requiredPins"][0]["z"],pin["z"]+.1)
                    self.assertIn("위치를 변경",page.locator("#statusLine").inner_text())
                    page.locator("#undoBtn").click()
                    restored=self._export_current_layout(page)["requiredPins"][0]
                    self.assertAlmostEqual(restored["x"],pin["x"],delta=.001)
                    self.assertAlmostEqual(restored["z"],pin["z"],delta=.001)
                    self.assertEqual(errors,[])
                finally:
                    browser.close()

    def test_mobile_overlapping_pins_cycle_and_explicit_picker_both_engines(self):
        import json
        for engine in ("chromium","webkit"):
            with self.subTest(engine=engine):
                browser,page,errors=self._mobile_touch_editor(engine)
                try:
                    layout=self._fixture()
                    layout["requiredPins"]=[
                        {"id":"alpha","x":2.0,"z":2.0,"radiusM":.8,"minQualityScore":70},
                        {"id":"beta","x":2.0,"z":2.0,"radiusM":.7,"minQualityScore":70},
                    ]
                    page.locator("#importFile").set_input_files({
                        "name":"overlap-synthetic.json","mimeType":"application/json",
                        "buffer":json.dumps(layout).encode("utf-8"),
                    })
                    page.wait_for_function("document.body.dataset.view === 'design'",timeout=10000)
                    page.locator('[data-tool="required"]').click()
                    bounds=page.locator("#editorCanvas").bounding_box()
                    x=bounds["x"]+bounds["width"]*2/layout["width"]
                    y=bounds["y"]+bounds["height"]*2/layout["depth"]
                    self.assertEqual(page.locator("#requiredPinSelect option").count(),2)
                    page.touchscreen.tap(x,y)
                    first=page.locator("#requiredPinSelect").input_value()
                    self.assertIn(first,("alpha","beta"))
                    page.touchscreen.tap(x,y)
                    second=page.locator("#requiredPinSelect").input_value()
                    self.assertNotEqual(first,second)
                    self.assertIn("선택됨",page.locator("#requiredSelectionStatus").inner_text())
                    page.locator("#requiredNextPin").click()
                    self.assertEqual(page.locator("#requiredPinSelect").input_value(),first)
                    page.locator("#requiredPinSelect").select_option(second)
                    self.assertEqual(page.locator("#requiredPinSelect").input_value(),second)
                    self.assertEqual(len(self._export_current_layout(page)["requiredPins"]),2)
                    self.assertEqual(errors,[])
                finally:
                    browser.close()

    def test_mobile_pin_accessibility_keyboard_radius_and_touch_targets(self):
        for engine in ("chromium","webkit"):
            with self.subTest(engine=engine):
                browser,page,errors=self._mobile_touch_editor(engine)
                try:
                    bounds=page.locator("#editorCanvas").bounding_box()
                    page.touchscreen.tap(bounds["x"]+bounds["width"]*.5,
                                         bounds["y"]+bounds["height"]*.5)
                    slider=page.locator("#selectedRequiredRadius")
                    self.assertTrue(slider.is_visible())
                    self.assertIn("필수영역",slider.get_attribute("aria-label"))
                    self.assertEqual(slider.get_attribute("aria-describedby"),"requiredSelectedHint")
                    self.assertGreaterEqual(slider.bounding_box()["height"],44)
                    self.assertGreaterEqual(page.locator("#requiredPinSelect").bounding_box()["height"],44)
                    self.assertGreaterEqual(page.locator("#requiredNextPin").bounding_box()["height"],44)
                    slider.focus()
                    slider.press("ArrowRight")
                    self.assertGreater(
                        self._export_current_layout(page)["requiredPins"][0]["radiusM"],.8)
                    self.assertEqual(page.locator("#selectedRequiredRadius").get_attribute("aria-valuetext"),"0.9미터")
                    self.assertEqual(errors,[])
                finally:
                    browser.close()

    def test_mobile_touch_jitter_does_not_create_undo_move(self):
        browser,page,errors=self._mobile_touch_editor("webkit")
        try:
            bounds=page.locator("#editorCanvas").bounding_box()
            page.touchscreen.tap(bounds["x"]+bounds["width"]*.5,
                                 bounds["y"]+bounds["height"]*.5)
            first=self._export_current_layout(page)
            p=first["requiredPins"][0]
            sx=bounds["x"]+bounds["width"]*p["x"]/first["width"]
            sy=bounds["y"]+bounds["height"]*p["z"]/first["depth"]
            self._touch_pointer_sequence(page,(sx,sy),(sx+4,sy+3))
            self.assertEqual(self._export_current_layout(page)["requiredPins"][0],p)
            page.locator("#undoBtn").click()
            self.assertEqual(len(self._export_current_layout(page)["requiredPins"]),0)
            self.assertEqual(errors,[])
        finally:
            browser.close()



    def test_mobile_secondary_touch_does_not_steal_active_pin_drag(self):
        """A secondary pointer never changes the active drag, undo or pin count."""
        for engine in ("chromium", "webkit"):
            with self.subTest(engine=engine):
                browser, page, errors = self._mobile_touch_editor(engine)
                try:
                    bounds = page.locator("#editorCanvas").bounding_box()
                    page.touchscreen.tap(bounds["x"] + bounds["width"]*.5,
                                         bounds["y"] + bounds["height"]*.5)
                    before = self._export_current_layout(page)
                    pin = before["requiredPins"][0]
                    px = bounds["x"] + bounds["width"]*pin["x"]/before["width"]
                    py = bounds["y"] + bounds["height"]*pin["z"]/before["depth"]
                    canvas = page.locator("#editorCanvas")
                    primary = {"pointerId":91, "pointerType":"touch",
                               "isPrimary":True, "button":0, "buttons":1}
                    secondary = {"pointerId":92, "pointerType":"touch",
                                 "isPrimary":False, "button":0, "buttons":1}
                    canvas.dispatch_event("pointerdown", {**primary,"clientX":px,"clientY":py})
                    canvas.dispatch_event("pointermove", {**primary,"clientX":px+22,"clientY":py+14})
                    # Secondary finger tries to select another location, move and cancel.
                    canvas.dispatch_event("pointerdown", {**secondary,"clientX":px+80,"clientY":py+65})
                    canvas.dispatch_event("pointermove", {**secondary,"clientX":px+120,"clientY":py+90})
                    canvas.dispatch_event("pointercancel", {**secondary,"buttons":0,"clientX":px+120,"clientY":py+90})
                    canvas.dispatch_event("pointermove", {**primary,"clientX":px+46,"clientY":py+25})
                    canvas.dispatch_event("pointerup", {**primary,"buttons":0,"clientX":px+46,"clientY":py+25})
                    after = self._export_current_layout(page)
                    self.assertEqual(len(after["requiredPins"]),1)
                    self.assertEqual(after["requiredPins"][0]["id"], pin["id"])
                    self.assertGreater(after["requiredPins"][0]["x"],pin["x"]+.1)
                    self.assertGreater(after["requiredPins"][0]["z"],pin["z"]+.1)
                    page.locator("#undoBtn").click()
                    restored = self._export_current_layout(page)["requiredPins"][0]
                    self.assertAlmostEqual(restored["x"],pin["x"],delta=.001)
                    self.assertAlmostEqual(restored["z"],pin["z"],delta=.001)
                    self.assertEqual(errors, [])
                finally:
                    browser.close()

    def test_mobile_cancelled_drag_restores_pin_without_extra_undo(self):
        """Cancelling a touch move rolls back position and its transient undo entry."""
        for engine in ("chromium", "webkit"):
            with self.subTest(engine=engine):
                browser, page, errors = self._mobile_touch_editor(engine)
                try:
                    bounds = page.locator("#editorCanvas").bounding_box()
                    page.touchscreen.tap(bounds["x"] + bounds["width"]*.5,
                                         bounds["y"] + bounds["height"]*.5)
                    original = self._export_current_layout(page)
                    pin = original["requiredPins"][0]
                    px = bounds["x"] + bounds["width"]*pin["x"]/original["width"]
                    py = bounds["y"] + bounds["height"]*pin["z"]/original["depth"]
                    canvas = page.locator("#editorCanvas")
                    primary = {"pointerId":94,"pointerType":"touch",
                               "isPrimary":True,"button":0,"buttons":1}
                    canvas.dispatch_event("pointerdown",{**primary,"clientX":px,"clientY":py})
                    canvas.dispatch_event("pointermove",{**primary,"clientX":px+44,"clientY":py+26})
                    # Cancel after threshold was passed, not a stationary tap cancellation.
                    canvas.dispatch_event("pointercancel",{**primary,"buttons":0,"clientX":px+44,"clientY":py+26})
                    self.assertEqual(self._export_current_layout(page)["requiredPins"][0],pin)
                    self.assertTrue(page.locator("#requiredSelectedControls").is_visible())
                    # If the cancelled drag leaked an undo item, this wouldn't remove the pin.
                    page.locator("#undoBtn").click()
                    self.assertEqual(len(self._export_current_layout(page)["requiredPins"]),0)
                    # Confirm the cancelled pointer no longer blocks later touches.
                    page.touchscreen.tap(bounds["x"]+bounds["width"]*.5,
                                         bounds["y"]+bounds["height"]*.5)
                    self.assertEqual(len(self._export_current_layout(page)["requiredPins"]),1)
                    self.assertEqual(errors, [])
                finally:
                    browser.close()

    def test_required_pin_keyboard_create_nudge_boundary_and_undo(self):
        """Focused canvas supports keyboard-only pin creation and X-Z nudge."""
        for engine in ("chromium","webkit"):
            with self.subTest(engine=engine):
                browser, page, errors = self._mobile_touch_editor(engine)
                try:
                    canvas = page.locator("#editorCanvas")
                    self.assertEqual(canvas.get_attribute("tabindex"),"0")
                    self.assertEqual(canvas.get_attribute("aria-describedby"),"requiredCanvasHelp")
                    canvas.focus()
                    canvas.press("Enter")
                    layout = self._export_current_layout(page)
                    self.assertEqual(len(layout["requiredPins"]),1)
                    self.assertEqual(layout["requiredPins"][0]["minQualityScore"],70)
                    before = layout["requiredPins"][0]
                    canvas.press("ArrowRight")
                    after = self._export_current_layout(page)["requiredPins"][0]
                    self.assertAlmostEqual(after["x"]-before["x"],0.1,delta=.001)
                    canvas.press("Shift+ArrowDown")
                    shifted = self._export_current_layout(page)["requiredPins"][0]
                    self.assertAlmostEqual(shifted["z"]-after["z"],0.5,delta=.001)
                    self.assertEqual(shifted["minQualityScore"],70)
                    self.assertIn("키보드로 필수영역 위치",page.locator("#statusLine").inner_text())
                    page.locator("#undoBtn").click()
                    restored = self._export_current_layout(page)["requiredPins"][0]
                    self.assertAlmostEqual(restored["z"],after["z"],delta=.001)
                    page.locator("#undoBtn").click()
                    again = self._export_current_layout(page)["requiredPins"][0]
                    self.assertAlmostEqual(again["x"],before["x"],delta=.001)
                    self.assertEqual(errors,[])
                finally:
                    browser.close()

    def test_imported_overlaps_picker_remains_synced_after_delete(self):
        """Removing selected pin selects an actual remaining pin, never a phantom default."""
        import json
        for engine in ("chromium","webkit"):
            with self.subTest(engine=engine):
                browser, page, errors = self._mobile_touch_editor(engine)
                try:
                    layout = self._fixture()
                    layout["requiredPins"] = [
                        {"id":"one","x":2,"z":2,"radiusM":0.8,"minQualityScore":70},
                        {"id":"two","x":2,"z":2,"radiusM":0.7,"minQualityScore":70},
                    ]
                    page.locator("#importFile").set_input_files({
                        "name":"pins-only-synthetic.json","mimeType":"application/json",
                        "buffer":json.dumps(layout).encode("utf-8"),
                    })
                    page.wait_for_function("document.body.dataset.view === 'design'",timeout=10000)
                    self.assertEqual(page.locator("#requiredPinSelect").input_value(),"one")
                    self.assertTrue(page.locator("#requiredSelectedControls").is_visible())
                    page.locator("#elementsDrawer summary").click()
                    page.locator("#elementList .element").filter(has_text="필수영역").first.locator("button").click()
                    self.assertEqual(len(self._export_current_layout(page)["requiredPins"]),1)
                    self.assertEqual(page.locator("#requiredPinSelect").input_value(),"two")
                    self.assertIn("필수영역 1 선택됨",page.locator("#requiredSelectionStatus").inner_text())
                    self.assertEqual(errors,[])
                finally:
                    browser.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
