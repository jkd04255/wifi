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


if __name__ == "__main__":
    unittest.main(verbosity=2)
