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
        self.assertIn("CALIBRATION_CONFLICT", self.page.locator("#statusLine").inner_text())
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

    def test_offline_engine_identical_on_http_and_file_origins(self):
        self.page.locator("#applyBottomBtn").click()
        self.page.wait_for_function(
            "document.getElementById('applyBtn').disabled===false && "
            "document.getElementById('engineMode').textContent.includes('오프라인 JS')",
            timeout=30000,
        )
        file_score = self.page.locator("#scoreStat").inner_text()
        self.assertNotEqual(file_score, "—")
        contacted = []
        self.page.on("request", lambda req: contacted.append(req.url) if "/api/" in req.url else None)
        html = (Path(__file__).resolve().parents[2] / "preview" / "stage4_offline.html").read_text(encoding="utf-8")
        self.page.route(
            "http://standalone.test/**",
            lambda route: route.fulfill(status=200, content_type="text/html", body=html),
        )
        self.page.goto("http://standalone.test/offline.html", wait_until="load")
        self.page.locator("#applyBottomBtn").click()
        self.page.wait_for_function(
            "document.getElementById('applyBtn').disabled===false && "
            "document.getElementById('engineMode').textContent.includes('오프라인 JS')",
            timeout=30000,
        )
        self.assertEqual(self.page.locator("#scoreStat").inner_text(), file_score)
        self.assertIn("오프라인 JS", self.page.locator("#engineMode").inner_text())
        self.assertEqual(contacted, [])

    def test_invalid_pin_coordinate_import_does_not_corrupt_layout(self):
        self.pin()
        original = self.export()
        malformed = json.loads(json.dumps(original))
        malformed["requiredPins"][0]["x"] = None
        self.page.locator("#importFile").set_input_files({
            "name": "invalid-pin.json", "mimeType": "application/json",
            "buffer": json.dumps(malformed).encode("utf-8"),
        })
        self.page.wait_for_function("document.getElementById('toast').textContent.includes('JSON 불러오기 실패')")
        self.assertEqual(self.export()["requiredPins"], original["requiredPins"])

    def test_uncapped_router_and_receiver_height_and_no_ceiling_control(self):
        self.assertEqual(self.page.locator("#roomHeightM").count(), 0)
        self.page.locator("#applyBottomBtn").click()
        self.page.locator("#routerY").fill("40")
        self.page.locator("#routerY").press("Tab")
        self.page.locator("#receiverY").fill("35")
        self.page.locator("#receiverY").press("Tab")
        result = self.export()
        self.assertEqual(result["router"]["y"], 40)
        self.assertEqual(result["receiverY"], 35)
        self.page.locator("#applyBtn").click()
        self.page.wait_for_function("document.getElementById('applyBtn').disabled===false", timeout=30000)
        self.assertIn("오프라인 JS", self.page.locator("#engineMode").inner_text())

    def test_mobile_signal_palette_and_json(self):
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.page.locator('[data-tool="required"]').click()
        self.page.locator("#editorCanvas").click(position={"x": 70, "y": 85})
        self.assertTrue(self.page.locator("#toolsRail").is_hidden())
        self.page.locator("#paletteToggleBtn").click()
        self.assertTrue(self.page.locator("#requiredDrawer").evaluate("(node) => node.open"))
        self.page.locator("#signalBarsSelect").select_option("2")
        pin = self.export()["requiredPins"][0]
        self.assertEqual((pin["signalBars"], pin["minQualityScore"]), (2, 27))

    def test_one_tap_bar_buttons_and_delete_selected_pin(self):
        self.pin()
        self.page.locator("#editorCanvas").click(position={"x": 650, "y": 380})
        self.page.locator("#paletteToggleBtn").click()
        self.assertTrue(self.page.locator("#requiredDrawer").evaluate("(node) => node.open"))
        buttons = self.page.locator("[data-signal-level]")
        self.assertEqual(buttons.count(), 5)
        self.page.locator('[data-signal-level="1"]').click()
        pins = self.export()["requiredPins"]
        self.assertEqual([p["minQualityScore"] for p in pins], [64, 9])
        self.assertEqual(self.page.locator('[data-signal-level="1"]').get_attribute("aria-pressed"), "true")
        self.page.locator("#requiredPinSelect").select_option(pins[0]["id"])
        self.assertEqual(self.page.locator('[data-signal-level="4"]').get_attribute("aria-pressed"), "true")
        self.page.locator("#requiredDeletePin").click()
        remaining = self.export()["requiredPins"]
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["minQualityScore"], 9)
        self.page.locator("#undoBtn").click()
        self.assertEqual(len(self.export()["requiredPins"]), 2)
        self.page.locator("#requiredDeletePin").click()
        self.page.locator("#requiredDeletePin").click()
        self.assertTrue(self.page.locator("#requiredDeletePin").is_disabled())
        self.assertEqual(self.export()["requiredPins"], [])

    def test_export_import_roundtrip_keeps_independent_bars_and_positions(self):
        self.pin()
        self.change_bars(3)
        self.page.locator("#editorCanvas").click(position={"x": 630, "y": 330})
        self.page.locator('[data-signal-level="0"]').click()
        original = self.export()
        for pin in original["requiredPins"]:
            self.assertEqual(set(pin), {"id", "x", "z", "signalBars", "minQualityScore"})
            self.assertNotIn("radiusM", pin)
        self.page.locator("#resetBtn").click()
        self.assertEqual(self.export()["requiredPins"], [])
        self.page.locator("#importFile").set_input_files({
            "name": "roundtrip.json",
            "mimeType": "application/json",
            "buffer": json.dumps(original).encode("utf-8"),
        })
        self.page.wait_for_function("document.querySelectorAll('#requiredPinSelect option').length===2")
        self.assertEqual(self.export()["requiredPins"], original["requiredPins"])
        if self.page.locator("#toolsRail").is_hidden():
            self.page.locator("#paletteToggleBtn").click()
        self.page.locator("#requiredDrawer").evaluate("(node) => { node.open = true; }")
        self.page.locator("#requiredPinSelect").select_option(original["requiredPins"][0]["id"])
        self.assertEqual(self.page.locator('[data-signal-level="3"]').get_attribute("aria-pressed"), "true")
        self.page.locator("#requiredPinSelect").select_option(original["requiredPins"][1]["id"])
        self.assertEqual(self.page.locator('[data-signal-level="0"]').get_attribute("aria-pressed"), "true")

    def test_import_empty_pin_layout_clears_previous_state(self):
        self.pin()
        self.page.locator("#applyBottomBtn").click()
        self.page.wait_for_function("document.getElementById('applyBtn').disabled===false")
        self.page.locator("#designTab").click()
        original = self.export()
        original["requiredPins"] = []
        self.page.locator("#importFile").set_input_files({
            "name": "empty-pins.json",
            "mimeType": "application/json",
            "buffer": json.dumps(original).encode("utf-8"),
        })
        self.page.wait_for_function("document.getElementById('requiredPinPicker').hidden")
        self.assertEqual(self.export()["requiredPins"], [])
        self.assertTrue(self.page.locator("#requiredDeletePin").is_disabled())
        self.assertIn("신호 세기 핀 없음", self.page.locator("#requiredStatus").inner_text())
        self.assertEqual(self.page.locator("#heatmapEmpty").evaluate("(el) => getComputedStyle(el).display"), "flex")

    def test_apply_optimized_position_satisfies_mixed_pin_thresholds(self):
        self.pin()
        self.change_bars(3)
        self.page.locator("#editorCanvas").click(position={"x": 640, "y": 290})
        self.change_bars(0)
        self.page.locator("#applyBottomBtn").click()
        self.page.locator("#optimizeBtn").click()
        self.page.wait_for_function("document.getElementById('optimizeBtn').disabled===false", timeout=30000)
        self.assertTrue(self.page.locator("#recommendation").is_visible(), self.page.locator("#statusLine").inner_text())
        self.page.locator("#useBestBtn").click()
        self.page.wait_for_function("document.getElementById('applyBtn').disabled===false", timeout=30000)
        rows = self.page.locator("#requiredResults > div")
        self.assertGreaterEqual(rows.count(), 2)
        self.assertIn("2/2곳 기준 충족", self.page.locator("#requiredStatus").inner_text())
        after = self.export()["requiredPins"]
        self.assertEqual([p["minQualityScore"] for p in after], [42, 0])
        self.assertTrue(self.page.locator("#recommendation").is_hidden())

    def test_campusrssi_report_profiles_and_5ghz_isolation(self):
        layout = self.export()
        model = self.page.evaluate("""layout => {
            const engine = window.WifiEngine;
            const profiles = Object.fromEntries(engine.calibrationProfileNames.map(
                name => [name, engine.profileSettings(layout, name)]
            ));
            const modified = {...layout, modelOverrides:{...layout.modelOverrides, pathLossExponent:3}};
            const five = {...layout, router:{...layout.router, frequency:5}};
            return {
                names:engine.calibrationProfileNames,
                general:engine.settings(layout),
                profiles:profiles,
                forcedN:engine.settings(modified).n,
                five:engine.settings(five)
            };
        }""", layout)
        self.assertEqual(model["names"], ["OPEN", "GENERAL", "DENSE"])
        self.assertAlmostEqual(model["general"]["n"], 2.0011, places=4)
        self.assertAlmostEqual(model["general"]["wallLoss"]["concrete"], 6.8491, places=4)
        self.assertAlmostEqual(model["forcedN"], 2.0011, places=4)
        for name, n, alpha in [("OPEN", 1.6538, 6.28), ("GENERAL", 2.0011, 6.8491), ("DENSE", 2.3784, 7.21)]:
            self.assertAlmostEqual(model["profiles"][name]["n"], n, places=4)
            self.assertAlmostEqual(model["profiles"][name]["wallLoss"]["concrete"], alpha, places=4)
            self.assertAlmostEqual(model["profiles"][name]["p0"], model["general"]["p0"], places=4)
        self.assertFalse(model["five"]["calibrated"])
        self.assertAlmostEqual(model["five"]["n"], 2.2, places=4)
        self.assertAlmostEqual(model["five"]["wallLoss"]["concrete"], 18, places=4)

    def test_campusrssi_concrete_crossing_deduplicates_split_segments(self):
        layout = self.export()
        readings = self.page.evaluate("""base => {
            const model = window.WifiEngine;
            const wall = (id, x) => ({id,x1:x,z1:1,x2:x,z2:9,material:'concrete'});
            const trial = walls => ({
                ...base,
                router:{...base.router,x:1,z:5,y:1.2,frequency:2.4},
                receiverY:1.2,
                walls
            });
            const no = model.value(trial([]),9,5);
            const one = model.value(trial([wall('a',5)]),9,5);
            const duplicate = model.value(trial([wall('a',5),wall('b',5)]),9,5);
            const two = model.value(trial([wall('a',3),wall('b',6)]),9,5);
            return {oneLoss:no-one,duplicateLoss:no-duplicate,twoLoss:no-two};
        }""", layout)
        self.assertAlmostEqual(readings["oneLoss"], 6.8491, places=3)
        self.assertAlmostEqual(readings["duplicateLoss"], 6.8491, places=3)
        self.assertAlmostEqual(readings["twoLoss"], 13.6982, places=3)

    def test_signal_pin_results_use_robust_worst_case_not_just_general(self):
        self.pin()
        self.change_bars(0)
        self.page.locator("#applyBottomBtn").click()
        self.page.wait_for_function("document.getElementById('applyBtn').disabled===false", timeout=30000)
        self.assertIn("3개 프로파일 최악값", self.page.locator("#requiredStatus").inner_text())
        self.assertIn("현재 3프로파일 최악 예상", self.page.locator("#requiredResults").inner_text())
        self.page.locator("#optimizeBtn").click()
        self.page.wait_for_function("document.getElementById('optimizeBtn').disabled===false", timeout=30000)
        self.assertTrue(self.page.locator("#recommendation").is_visible(), self.page.locator("#statusLine").inner_text())
        self.assertIn("Robust", self.page.locator("#recommendBody").inner_text())
        self.assertIn("Robust 추천 최악 예상", self.page.locator("#requiredResults").inner_text())

    def test_baseline_24_matches_precalibration_git_commit_and_5ghz_unchanged(self):
        data = self.export()
        model = self.page.evaluate("""layout => {
            const e=window.WifiEngine;
            const before=e.baselineSettings(layout),after=e.settings(layout);
            const five={...layout,router:{...layout.router,frequency:5}};
            return {before,after,fiveBaseline:e.baselineSettings(five),fiveCurrent:e.settings(five)};
        }""", data)
        self.assertAlmostEqual(model["before"]["n"], 2.2, places=4)
        self.assertAlmostEqual(model["before"]["wallLoss"]["concrete"], 12.0, places=4)
        self.assertAlmostEqual(model["before"]["p0"], model["after"]["p0"], places=4)
        self.assertAlmostEqual(model["after"]["n"], 2.0011, places=4)
        self.assertAlmostEqual(model["after"]["wallLoss"]["concrete"], 6.8491, places=4)
        self.assertEqual(model["fiveBaseline"], model["fiveCurrent"])
        self.assertFalse(model["fiveCurrent"]["calibrated"])

    def test_profiles_and_same_layout_before_after_visualization(self):
        self.page.locator("#applyBottomBtn").click()
        self.page.wait_for_function("document.getElementById('applyBtn').disabled===false", timeout=30000)
        self.assertTrue(self.page.locator("#profileComparison").is_visible())
        self.assertEqual(self.page.locator("#profileComparisonRows .profile-row").count(), 3)
        self.assertEqual(
            self.page.locator("#profileComparisonRows .profile-row b").all_inner_texts(),
            ["OPEN", "GENERAL", "DENSE"],
        )
        self.assertEqual(self.page.locator("#profileComparisonRows .profile-meter span").count(), 3)
        self.assertTrue(self.page.locator("#calibrationComparison").is_visible())
        self.assertEqual(self.page.locator("#calibrationComparisonRows > div").count(), 2)
        self.assertIn("보정 전 (기존)", self.page.locator("#calibrationComparisonRows").inner_text())
        self.assertIn("보정 후 (GENERAL)", self.page.locator("#calibrationComparisonRows").inner_text())
        self.assertIn("예상 평균 RSSI 차이", self.page.locator("#calibrationComparison").inner_text())
        self.page.locator("#powerInput").fill("25")
        self.page.locator("#powerInput").press("Tab")
        self.assertTrue(self.page.locator("#calibrationComparison").is_hidden())
        self.assertTrue(self.page.locator("#profileComparison").is_hidden())
        self.page.locator("#applyBtn").click()
        self.page.wait_for_function("document.getElementById('applyBtn').disabled===false", timeout=30000)
        self.assertTrue(self.page.locator("#calibrationComparison").is_visible())

    def test_pin_worst_case_margin_before_and_after_robust_optimization(self):
        self.pin()
        self.change_bars(2)
        self.page.locator("#applyBottomBtn").click()
        self.page.wait_for_function("document.getElementById('applyBtn').disabled===false", timeout=30000)
        self.assertIn("핀 최악 여유점수", self.page.locator("#requiredResults").inner_text())
        self.assertIn("3개 프로파일 최악값", self.page.locator("#requiredStatus").inner_text())
        self.page.locator("#optimizeBtn").click()
        self.page.wait_for_function("document.getElementById('optimizeBtn').disabled===false", timeout=30000)
        self.assertTrue(self.page.locator("#recommendation").is_visible(), self.page.locator("#statusLine").inner_text())
        self.assertIn("→ 추천 +", self.page.locator("#requiredResults").inner_text())

    def test_robust_top_three_sorted_spaced_and_second_candidate_applies(self):
        self.page.locator("#applyBottomBtn").click()
        self.page.locator("#optimizeBtn").click()
        self.page.wait_for_function("document.getElementById('optimizeBtn').disabled===false", timeout=30000)
        self.assertTrue(self.page.locator("#topThreeCandidates").is_visible(), self.page.locator("#statusLine").inner_text())
        options=self.page.locator("#topThreeRows button[data-top-rank]")
        self.assertEqual(options.count(), 3)
        coords=[]
        for i in range(options.count()):
            b=options.nth(i)
            self.assertEqual(b.get_attribute("data-top-rank"), str(i+1))
            coords.append((float(b.get_attribute("data-candidate-x")),float(b.get_attribute("data-candidate-z"))))
        for i in range(len(coords)):
            for j in range(i+1,len(coords)):
                distance=((coords[i][0]-coords[j][0])**2+(coords[i][1]-coords[j][1])**2)**.5
                self.assertGreaterEqual(distance, .5-1e-6)
        self.page.locator('[data-top-rank="2"]').click()
        self.page.wait_for_function(
            "document.getElementById('applyBtn').disabled===false && "
            "document.getElementById('engineMode').textContent.includes('GENERAL')",
            timeout=30000,
        )
        saved=self.export()
        self.assertAlmostEqual(saved["router"]["x"],coords[1][0],places=5)
        self.assertAlmostEqual(saved["router"]["z"],coords[1][1],places=5)
        self.assertTrue(self.page.locator("#recommendation").is_hidden())
        self.assertTrue(self.page.locator("#calibrationComparison").is_visible())

    def test_calibration_visualizations_hidden_for_5ghz_and_restored_after_json(self):
        self.pin()
        original=self.export()
        data=json.loads(json.dumps(original))
        data["router"]["frequency"]=5
        self.page.locator("#importFile").set_input_files({
            "name":"five.json","mimeType":"application/json",
            "buffer":json.dumps(data).encode("utf-8"),
        })
        self.page.wait_for_function("document.getElementById('frequencySelect').value==='5'")
        self.page.locator("#applyBottomBtn").click()
        self.page.wait_for_function("document.getElementById('applyBtn').disabled===false", timeout=30000)
        self.assertTrue(self.page.locator("#profileComparison").is_hidden())
        self.assertTrue(self.page.locator("#calibrationComparison").is_hidden())
        self.assertIn("5 GHz",self.page.locator("#engineMode").inner_text())
        self.assertEqual(self.export()["requiredPins"],original["requiredPins"])
        self.page.locator("#designTab").click()
        self.page.locator("#importFile").set_input_files({
            "name":"return-24.json","mimeType":"application/json",
            "buffer":json.dumps(original).encode("utf-8"),
        })
        self.page.wait_for_function("document.getElementById('frequencySelect').value==='2.4'")
        self.assertTrue(self.page.locator("#calibrationComparison").is_hidden())
        self.page.locator("#applyBottomBtn").click()
        self.page.wait_for_function("document.getElementById('applyBtn').disabled===false", timeout=30000)
        self.assertTrue(self.page.locator("#calibrationComparison").is_visible())
        self.assertEqual(self.export()["requiredPins"],original["requiredPins"])

    def test_near_optimal_feasible_sample_overlay_toggle(self):
        self.page.locator("#applyBottomBtn").click()
        self.page.locator("#optimizeBtn").click()
        self.page.wait_for_function("document.getElementById('optimizeBtn').disabled===false", timeout=30000)
        self.assertTrue(self.page.locator("#topThreeCandidates").is_visible(), self.page.locator("#statusLine").inner_text())
        description=self.page.locator("#stabilitySummary").inner_text()
        self.assertIn("J 최고점 대비 1.0점 이내", description)
        self.assertIn("이산 표본", description)
        self.assertTrue(self.page.locator("#stabilityToggle").is_checked())
        image_on=self.page.locator("#heatmapCanvas").evaluate("(canvas)=>canvas.toDataURL('image/png')")
        self.page.locator("#stabilityToggle").uncheck()
        self.assertFalse(self.page.locator("#stabilityToggle").is_checked())
        image_off=self.page.locator("#heatmapCanvas").evaluate("(canvas)=>canvas.toDataURL('image/png')")
        self.assertNotEqual(image_on,image_off)
        self.page.locator("#stabilityToggle").check()
        image_again=self.page.locator("#heatmapCanvas").evaluate("(canvas)=>canvas.toDataURL('image/png')")
        self.assertEqual(image_on,image_again)

    def test_compare_candidate_no_router_mutation_and_three_objective_scores(self):
        self.page.locator("#applyBottomBtn").click()
        self.page.locator("#optimizeBtn").click()
        self.page.wait_for_function("document.getElementById('optimizeBtn').disabled===false", timeout=30000)
        opts=self.page.locator("#topThreeRows button[data-compare-rank]")
        self.assertEqual(opts.count(),3)
        self.assertEqual(opts.nth(0).get_attribute("aria-pressed"),"true")
        before=self.export()
        opts.nth(1).click()
        self.assertEqual(opts.nth(1).get_attribute("aria-pressed"),"true")
        self.assertEqual(opts.nth(0).get_attribute("aria-pressed"),"false")
        self.assertIn("비교 중: #2", self.page.locator("#candidateCompare").inner_text())
        self.assertIn("1순위와의 거리", self.page.locator("#candidateCompare").inner_text())
        labels=self.page.locator("#candidateCompare [data-compare-profile]").evaluate_all(
            "(els)=>els.map(el=>el.dataset.compareProfile)")
        self.assertEqual(labels,["OPEN","GENERAL","DENSE"])
        self.assertEqual(self.export(),before)
        self.assertTrue(self.page.locator("#recommendation").is_visible())

    def test_json_roundtrip_preserves_calibration_inputs_not_ephemeral_candidates(self):
        self.pin()
        original=self.export()
        original["modelOverrides"]["p0"]=-40
        original["modelOverrides"]["wallLoss"]={"concrete":5.5}
        self.page.locator("#importFile").set_input_files({
            "name":"calibration-inputs.json","mimeType":"application/json",
            "buffer":json.dumps(original).encode("utf-8"),
        })
        self.page.wait_for_function(
            "document.getElementById('toast').textContent.includes('XZ 도면을 불러왔습니다')")
        imported=self.export()
        self.assertEqual(imported["modelOverrides"]["p0"],-40)
        self.assertEqual(imported["modelOverrides"]["wallLoss"],{"concrete":5.5})
        self.assertEqual(imported["requiredPins"],original["requiredPins"])
        self.assertNotIn("topThree",imported)
        self.assertNotIn("stability",imported)
        self.page.locator("#applyBottomBtn").click()
        self.page.wait_for_function("document.getElementById('applyBtn').disabled===false",timeout=30000)
        self.page.locator("#optimizeBtn").click()
        self.page.wait_for_function("document.getElementById('optimizeBtn').disabled===false",timeout=30000)
        self.assertTrue(self.page.locator("#topThreeCandidates").is_visible(),self.page.locator("#statusLine").inner_text())
        self.assertEqual(self.export(),imported)

    def test_invalid_calibration_json_rejected_and_original_layout_preserved(self):
        self.pin()
        original=self.export()
        for suffix,invalid in [("p0",{"p0":"not-a-number"}),("wall",{"wallLoss":{"concrete":"bad"}})]:
            data=json.loads(json.dumps(original))
            data["modelOverrides"].update(invalid)
            self.page.locator("#importFile").set_input_files({
                "name":"invalid-"+suffix+".json","mimeType":"application/json",
                "buffer":json.dumps(data).encode("utf-8"),
            })
            label="기준세기 P0" if suffix=="p0" else "벽 감쇠"
            self.page.wait_for_function(
                "(label)=>document.getElementById('toast').textContent.includes(label)", label)
            self.assertEqual(self.export(),original)

    def test_5ghz_candidate_comparison_does_not_claim_campusrssi_calibration(self):
        data=self.export()
        data["router"]["frequency"]=5
        self.page.locator("#importFile").set_input_files({
            "name":"legacy-five.json","mimeType":"application/json",
            "buffer":json.dumps(data).encode("utf-8"),
        })
        self.page.wait_for_function("document.getElementById('frequencySelect').value==='5'")
        self.page.locator("#applyBottomBtn").click()
        self.page.locator("#optimizeBtn").click()
        self.page.wait_for_function("document.getElementById('optimizeBtn').disabled===false",timeout=30000)
        self.assertIn("5 GHz 미보정",self.page.locator("#topThreeCandidates").inner_text())
        self.assertEqual(self.page.locator("#candidateCompare [data-compare-profile]").count(),1)
        self.assertEqual(self.page.locator("#candidateCompare [data-compare-profile]").first.get_attribute("data-compare-profile"),"LEGACY")
        self.assertTrue(self.page.locator("#profileComparison").is_hidden())
        self.assertTrue(self.page.locator("#calibrationComparison").is_hidden())

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
