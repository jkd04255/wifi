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
        self.page.locator("#signalBarsSelect").select_option(str(bars))

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
