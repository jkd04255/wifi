"""Browser smoke tests for isolated HTML-only Wi-Fi desktop deliverable."""
from pathlib import Path
import json
import unittest

from playwright.sync_api import sync_playwright

FILE_URL=(Path(__file__).resolve().parents[2]/"preview"/"stage4_offline.html").as_uri()


class OfflineDesktopSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=sync_playwright().start()
        cls.browser=cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.context=self.browser.new_context(accept_downloads=True, viewport={"width":1440,"height":900})
        self.page=self.context.new_page()
        self.errors=[]
        self.page.on("pageerror",lambda e:self.errors.append(str(e)))
        self.page.goto(FILE_URL,wait_until="load")
        self.page.locator("#editorScreen").wait_for(state="visible")

    def tearDown(self):
        self.context.close()

    def export(self):
        with self.page.expect_download() as task:
            self.page.locator("#exportBtn").click()
        return json.loads(task.value.path().read_text(encoding="utf-8"))

    def pin(self):
        self.page.locator('[data-tool="required"]').click()
        c=self.page.locator("#editorCanvas")
        c.click(position={"x":200,"y":150})

    def test_point_pin_round_trip_no_radius(self):
        self.pin()
        payload=self.export()
        self.assertEqual(len(payload["requiredPins"]),1)
        self.assertEqual(payload["requiredPins"][0]["minQualityScore"],70)
        self.assertNotIn("radiusM",payload["requiredPins"][0])
        self.assertFalse(self.errors)

    def test_keyboard_pin_creation_and_uncapped_height(self):
        self.page.locator('[data-tool="required"]').click()
        c=self.page.locator("#editorCanvas")
        c.focus()
        c.press("Enter")
        self.assertEqual(len(self.export()["requiredPins"]),1)
        self.page.locator("#applyBottomBtn").click()
        self.page.locator("#receiverY").fill("25")
        self.page.locator("#receiverY").press("Tab")
        self.assertEqual(self.export()["receiverY"],25)
        self.assertFalse(self.errors)

    def test_offline_pin_optimizer_without_lan(self):
        self.pin()
        self.page.locator("#applyBottomBtn").click()
        self.page.locator("#optimizeBtn").click()
        self.page.wait_for_function("document.getElementById('optimizeBtn').disabled===false",timeout=30000)
        self.assertTrue(self.page.locator("#recommendation").is_visible(),self.page.locator("#statusLine").inner_text())
        self.assertIn("필수 지정점 1개",self.page.locator("#recommendBody").inner_text())
        self.assertIn("LAN",self.page.locator("#recommendBody").inner_text())
        self.assertFalse(self.errors)


if __name__=="__main__":
    unittest.main()
