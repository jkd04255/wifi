"""Chromium regression tests for lightweight single-point Wi-Fi signal-level pins."""
from pathlib import Path
import json
import unittest

from playwright.sync_api import sync_playwright

FILE_URL = (Path(__file__).resolve().parents[2] / "preview" / "stage4_offline.html").as_uri()
LEVELS = {4: 64, 3: 42, 2: 27, 1: 9, 0: 0}


class OfflineDesktopSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.context = self.browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 900})
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.goto(FILE_URL, wait_until="load")
        self.page.locator("#editorScreen").wait_for(state="visible")

    def tearDown(self):
        self.assertFalse(self.errors, "Unexpected browser errors: " + "; ".join(self.errors))
        self.context.close()

    def export(self):
        with self.page.expect_download() as task:
            self.page.locator("#exportBtn").click()
        return json.loads(task.value.path().read_text(encoding="utf-8"))

    def pin(self, x=200, y=150):
        self.page.locator('[data-tool="required"]').click()
        self.page.locator("#editorCanvas").click(position={"x": x, "y": y})

    def change_bars(self, bars):
        if self.page.locator("#toolsRail").is_hidden():
            self.page.locator("#paletteToggleBtn").click()
        self.page.locator("#requiredDrawer").evaluate("(el) => { el.open = true; }")
        self.page.locator("#signalBarsSelect").select_option(str(bars))

    def test_tool_does_not_auto_expand_palette(self):
        self.assertTrue(self.page.locator("#toolsRail").is_hidden())
        self.pin()
        self.assertTrue(self.page.locator("#toolsRail").is_hidden())
        self.assertEqual(self.page.locator("#paletteToggleBtn").get_attribute("aria-expanded"), "false")
        self.page.locator("#paletteToggleBtn").click()
        self.assertTrue(self.page.locator("#toolsRail").is_visible())
        self.assertTrue(self.page.locator("#requiredDrawer").evaluate("(node) => node.open"))
        self.assertEqual(self.page.locator("#signalBarsSelect").input_value(), "4")

    def test_threshold_change_is_undoable(self):
        self.pin()
        self.change_bars(1)
        self.assertEqual(self.export()["requiredPins"][0]["minQualityScore"], 9)
        self.page.locator("#undoBtn").click()
        self.assertEqual(self.export()["requiredPins"][0]["minQualityScore"], 64)
        self.assertEqual(self.page.locator("#signalBarsSelect").input_value(), "4")

    def test_import_duplicate_ids_are_unique_and_selection_survives(self):
        self.pin()
        data = self.export()
        data["requiredPins"] = [
            {"id": "duplicated", "x": 1, "z": 1, "signalBars": 3, "minQualityScore": 64},
            {"id": "duplicated", "x": 4, "z": 3, "signalBars": 1, "minQualityScore": 64},
            {"x": 6, "z": 5, "minQualityScore": None},
        ]
        self.page.locator("#importFile").set_input_files({
            "name": "duplicate-pins.json",
            "mimeType": "application/json",
            "buffer": json.dumps(data).encode("utf-8"),
        })
        self.page.wait_for_function("document.querySelectorAll('#requiredPinSelect option').length === 3")
        pins = self.export()["requiredPins"]
        self.assertEqual(len(set(p["id"] for p in pins)), 3)
        self.assertEqual([(p["signalBars"], p["minQualityScore"]) for p in pins], [(3, 42), (1, 9), (4, 64)])
        self.page.locator("#paletteToggleBtn").click()
        self.page.locator("#requiredPinSelect").select_option(pins[1]["id"])
        self.assertEqual(self.page.locator("#signalBarsSelect").input_value(), "1")
        self.change_bars(2)
        self.assertEqual([v["minQualityScore"] for v in self.export()["requiredPins"]], [42, 27, 64])

    def test_optimizer_rejects_infeasible_four_bars_then_accepts_zero(self):
        self.pin()
        data = self.export()
        data["width"] = 24
        data["depth"] = 20
        data["walls"] = []
        data["requiredPins"] = [
            {"id": "far-a", "x": 0.3, "z": 0.3, "signalBars": 4, "minQualityScore": 64},
            {"id": "far-b", "x": 23.7, "z": 19.7, "signalBars": 4, "minQualityScore": 64},
        ]
        data["router"]["x"], data["router"]["z"] = 12, 10
        self.page.locator("#importFile").set_input_files({
            "name": "far-pins.json", "mimeType": "application/json",
            "buffer": json.dumps(data).encode("utf-8"),
        })
        self.page.wait_for_function("document.querySelectorAll('#requiredPinSelect option').length === 2")
        self.page.locator("#applyBottomBtn").click()
        self.page.locator("#optimizeBtn").click()
        self.page.wait_for_function("document.getElementById('optimizeBtn').disabled===false", timeout=30000)
        self.assertIn("추천 불가:", self.page.locator("#statusLine").inner_text())
        self.assertTrue(self.page.locator("#recommendation").is_hidden())
        self.page.locator("#designTab").click()
        self.page.locator("#paletteToggleBtn").click()
        self.change_bars(0)
        self.page.locator("#requiredPinSelect").select_option("far-b")
        self.change_bars(0)
        self.assertEqual([p["minQualityScore"] for p in self.export()["requiredPins"]], [0, 0])
        self.page.locator("#applyBottomBtn").click()
        self.page.locator("#optimizeBtn").click()
        self.page.wait_for_function("document.getElementById('optimizeBtn').disabled===false", timeout=30000)
        self.assertTrue(self.page.locator("#recommendation").is_visible(), self.page.locator("#statusLine").inner_text())

    def test_default_four_bars_and_point_only_no_radius(self):
        tool = self.page.locator('[data-tool="required"]')
        self.assertIn("신호 세기", tool.inner_text())
        self.pin()
        self.assertEqual(self.page.locator("#signalBarsSelect").input_value(), "4")
        payload = self.export()
        self.assertEqual(len(payload["requiredPins"]), 1)
        pin = payload["requiredPins"][0]
        self.assertEqual(pin["signalBars"], 4)
        self.assertEqual(pin["minQualityScore"], 64)
        self.assertNotIn("radiusM", pin)
        self.assertNotIn("requiredRadius", self.page.content())

    def test_all_bar_thresholds_and_per_pin_independence(self):
        self.pin()
        for bars, score in LEVELS.items():
            self.change_bars(bars)
            pin = self.export()["requiredPins"][0]
            self.assertEqual((pin["signalBars"], pin["minQualityScore"]), (bars, score))
            self.assertIn(f"{bars}칸", self.page.locator("#requiredSelectionStatus").inner_text())
        self.page.locator("#editorCanvas").click(position={"x": 650, "y": 380})
        data = self.export()
        self.assertEqual(len(data["requiredPins"]), 2)
        self.assertEqual([v["signalBars"] for v in data["requiredPins"]], [0, 4])
        self.assertEqual([v["minQualityScore"] for v in data["requiredPins"]], [0, 64])
        self.change_bars(2)
        data = self.export()
        self.assertEqual([v["minQualityScore"] for v in data["requiredPins"]], [0, 27])
        self.page.locator("#requiredPinSelect").select_option(data["requiredPins"][0]["id"])
        self.assertEqual(self.page.locator("#signalBarsSelect").input_value(), "0")

    def test_import_normalizes_legacy_70_to_four_bars(self):
        self.pin()
        old = self.export()
        old["requiredPins"][0].pop("signalBars")
        old["requiredPins"][0]["minQualityScore"] = 70
        old["requiredPins"][0]["radiusM"] = 2
        self.page.locator("#importFile").set_input_files({
            "name": "old-layout.json",
            "mimeType": "application/json",
            "buffer": json.dumps(old).encode("utf-8"),
        })
        self.page.wait_for_function("document.getElementById('signalBarsSelect').value==='4'")
        pin = self.export()["requiredPins"][0]
        self.assertEqual((pin["signalBars"], pin["minQualityScore"]), (4, 64))
        self.assertNotIn("radiusM", pin)

    def test_keyboard_pin_creation_and_uncapped_height(self):
        self.page.locator('[data-tool="required"]').click()
        canvas = self.page.locator("#editorCanvas")
        canvas.focus()
        canvas.press("Enter")
        self.assertEqual(self.export()["requiredPins"][0]["minQualityScore"], 64)
        self.page.locator("#applyBottomBtn").click()
        self.page.locator("#receiverY").fill("25")
        self.page.locator("#receiverY").press("Tab")
        self.assertEqual(self.export()["receiverY"], 25)

    def test_offline_pin_optimizer_without_lan(self):
        self.pin()
        self.change_bars(3)
        self.page.locator("#applyBottomBtn").click()
        self.page.locator("#optimizeBtn").click()
        self.page.wait_for_function("document.getElementById('optimizeBtn').disabled===false", timeout=30000)
        self.assertTrue(self.page.locator("#recommendation").is_visible(), self.page.locator("#statusLine").inner_text())
        body = self.page.locator("#recommendBody").inner_text()
        self.assertIn("신호 세기 핀 1개", body)
        self.assertIn("설정한 최소 칸수 모두 충족", body)
        self.assertIn("LAN", body)


if __name__ == "__main__":
    unittest.main()
