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
                                {"width": 1440, "height": 900})
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



if __name__ == "__main__":
    unittest.main(verbosity=2)
