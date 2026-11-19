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

    def test_xp_status_bar_tracks_real_layout_and_mode(self):
        self.assertTrue(self.page.locator(".xp-statusbar").is_visible())
        self.assertEqual(self.page.locator(".xp-statusbar > span").count(), 5)
        self.assertIn("도면 편집",self.page.locator("#xpStatusState").inner_text())
        self.assertIn("신호 핀 0개",self.page.locator("#xpStatusPins").inner_text())
        self.assertIn("중간",self.page.locator("#xpStatusModel").inner_text())
        self.pin()
        self.assertIn("신호 핀 1개",self.page.locator("#xpStatusPins").inner_text())
        self.page.locator(".xp-toolbar [data-xp-action='run']").click()
        self.page.wait_for_function(
            "document.body.dataset.view==='analysis' && document.getElementById('applyBtn').disabled===false",
            timeout=30000,
        )
        self.assertIn("신호 분석",self.page.locator("#xpStatusState").inner_text())
        self.assertIn("계산 완료",self.page.locator("#xpStatusState").inner_text())
        self.assertIn("2.4 GHz",self.page.locator("#xpStatusBand").inner_text())

    def test_xp_keyboard_save_and_edit_field_shortcuts(self):
        self.pin()
        with self.page.expect_download() as task:
            self.page.keyboard.press("Control+s")
        saved=json.loads(task.value.path().read_text(encoding="utf-8"))
        self.assertEqual(len(saved["requiredPins"]),1)
        before=self.export()
        self.page.locator("#pyeongInput").focus()
        self.page.locator("#pyeongInput").fill("23.5")
        self.page.keyboard.press("Control+z")
        self.assertEqual(self.export(),before)
        self.page.locator("#editorCanvas").focus()
        self.page.keyboard.press("Control+z")
        self.assertEqual(len(self.export()["requiredPins"]),0)

    def test_xp_compact_layout_on_mobile_does_not_overflow(self):
        self.page.set_viewport_size({"width":390,"height":844})
        self.assertTrue(self.page.locator(".xp-caption").is_visible())
        self.assertTrue(self.page.locator(".xp-toolbar").is_visible())
        width=self.page.evaluate("document.documentElement.scrollWidth")
        self.assertLessEqual(width,410)
        self.page.locator(".xp-toolbar [data-xp-action='help']").click()
        self.assertTrue(self.page.locator("#xpHelpDialog").is_visible())
        self.page.locator("#xpHelpClose").click()
        self.assertTrue(self.page.locator("#editorCanvas").is_visible())


    def test_xp_desktop_tool_palette_is_on_left_and_can_collapse(self):
        self.assertTrue(self.page.locator("#toolsRail").is_hidden())
        self.page.locator("#paletteToggleBtn").click()
        self.assertTrue(self.page.locator("#toolsRail").is_visible())
        canvas=self.page.locator(".editor-workarea .canvas-column").bounding_box()
        palette=self.page.locator("#toolsRail").bounding_box()
        self.assertLess(palette["x"],canvas["x"])
        self.assertLessEqual(palette["width"],310)
        self.assertEqual(self.page.locator("#paletteToggleBtn").get_attribute("aria-expanded"),"true")
        self.page.locator(".xp-toolbar [data-xp-action='palette']").click()
        self.assertTrue(self.page.locator("#toolsRail").is_hidden())
        self.assertEqual(self.page.locator("#paletteToggleBtn").get_attribute("aria-expanded"),"false")
        self.assertTrue(self.page.locator("#editorCanvas").is_visible())

    def test_xp_canvas_numeric_tool_shortcuts_respect_form_focus(self):
        self.page.locator("#editorCanvas").focus()
        self.page.keyboard.press("5")
        self.assertEqual(self.page.locator('[data-tool="required"]').get_attribute("aria-pressed"),"true")
        self.assertEqual(self.page.locator("#xpActiveTool").inner_text(),"신호 세기")
        self.page.keyboard.press("Enter")
        self.assertEqual(len(self.export()["requiredPins"]),1)
        self.page.locator("#pyeongInput").focus()
        self.page.keyboard.press("2")
        self.assertEqual(self.page.locator('[data-tool="required"]').get_attribute("aria-pressed"),"true")
        self.page.locator("#editorCanvas").focus()
        self.page.keyboard.press("2")
        self.assertEqual(self.page.locator('[data-tool="rectangle"]').get_attribute("aria-pressed"),"true")
        self.assertEqual(self.page.locator("#xpActiveTool").inner_text(),"직사각형")
        self.assertEqual(len(self.export()["requiredPins"]),1)

    def test_xp_menu_dismisses_other_menus_and_mobile_palette_stays_below_canvas(self):
        menus=self.page.locator(".xp-menu")
        menus.nth(0).locator("summary").click()
        self.assertTrue(menus.nth(0).evaluate("(el)=>el.open"))
        menus.nth(1).locator("summary").click()
        self.page.wait_for_function(
            "document.querySelectorAll('.xp-menu[open]').length===1 && document.querySelectorAll('.xp-menu')[1].open"
        )
        self.page.locator("#pyeongInput").click()
        self.assertEqual(self.page.locator(".xp-menu[open]").count(),0)
        self.page.set_viewport_size({"width":390,"height":844})
        self.page.locator("#paletteToggleBtn").click()
        canvas=self.page.locator(".editor-workarea .canvas-column").bounding_box()
        palette=self.page.locator("#toolsRail").bounding_box()
        self.assertGreaterEqual(palette["y"],canvas["y"]+canvas["height"]-1)
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"),410)


    def test_beginner_four_step_flow_and_height_presets(self):
        self.page.locator("#applyFromEditorBtn").click()
        self.assertEqual(self.page.locator("body").get_attribute("data-view"),"router")
        self.assertTrue(self.page.locator("#routerSimpleInfo").is_visible())
        self.page.locator('[name="wizardRouterMode"][value="advanced"]').check()
        self.assertTrue(self.page.locator("#routerAdvancedInfo").is_visible())
        self.page.locator("#wizardPower").fill("23")
        self.page.locator("#wizardPower").press("Tab")
        self.assertEqual(self.export()["router"]["txPowerDbm"],23)
        self.page.locator("#nextWizardHeight").click()
        self.assertEqual(self.page.locator("body").get_attribute("data-view"),"height")
        self.page.locator('[data-height="1.6"]').click()
        self.assertAlmostEqual(self.export()["router"]["y"],1.6)
        self.page.locator('[name="wizardHeightMode"][value="advanced"]').check()
        self.page.locator("#manualHeightInput").fill("15.5")
        self.page.locator("#manualHeightInput").press("Tab")
        self.assertAlmostEqual(self.export()["router"]["y"],15.5)
        self.page.locator("#nextWizardAnalysis").click()
        self.page.wait_for_function("document.body.dataset.view==='analysis' && document.getElementById('applyBtn').disabled===false",timeout=30000)
        self.assertIn("/ 100",self.page.locator("#scoreStat").inner_text())
        self.assertIn("/ 100",self.page.locator("#meanStat").inner_text())
        self.assertEqual(self.page.locator("#legendLow").inner_text(),"0점")
        self.page.locator("#expertToggle").click()
        self.assertIn("dBm",self.page.locator("#meanStat").inner_text())
        self.assertEqual(self.page.locator("#legendLow").inner_text(),"−90 dBm")

    def test_resizable_canvas_up_and_down_keeps_coordinates(self):
        start=self.page.locator("#editorFrame").bounding_box()["height"]
        self.page.locator("#sizeUpBtn").click()
        grown=self.page.locator("#editorFrame").bounding_box()["height"]
        self.assertGreater(grown,start+40)
        self.page.locator("#sizeDownBtn").click()
        self.assertAlmostEqual(self.page.locator("#editorFrame").bounding_box()["height"],start,delta=3)
        handle=self.page.locator('[data-resize-edge="bottom"]')
        handle.evaluate("(el)=>el.scrollIntoView({block:'center',behavior:'instant'})")
        box=handle.bounding_box()
        self.page.mouse.move(box["x"]+box["width"]/2,box["y"]+box["height"]/2)
        self.page.mouse.down()
        self.page.mouse.move(box["x"]+box["width"]/2,box["y"]+box["height"]/2+100,steps=6)
        self.page.mouse.up()
        self.assertGreater(self.page.locator("#editorFrame").bounding_box()["height"],start+70)
        self.pin()
        self.assertEqual(self.export()["requiredPins"][0]["signalBars"],4)

    def test_auto_wall_mount_and_wall_only_optimizer(self):
        data=self.export()
        data["walls"]=[{"id":"vertical","x1":5,"x2":5,"z1":1,"z2":7,"material":"concrete"}]
        data["router"]["x"]=6
        data["router"]["z"]=4
        data["requiredPins"]=[{"id":"p","x":6,"z":4,"signalBars":0,"minQualityScore":0}]
        self.page.locator("#importFile").set_input_files({
            "name":"wall-auto.json","mimeType":"application/json",
            "buffer":json.dumps(data).encode()
        })
        self.page.wait_for_function("document.getElementById('numWallsChip').textContent.includes('벽 1')")
        self.page.locator("#routerTab").click()
        self.assertEqual(self.page.locator("#mountFace").count(),0)
        self.page.locator('[name="wizardMount"][value="wall"]').check()
        self.assertIn("자동",self.page.locator("#mountStatus").inner_text())
        self.assertIn("오른쪽",self.page.locator("#mountAutoSummary").inner_text())
        mounted=self.export()
        self.assertAlmostEqual(mounted["router"]["x"],5.04,places=2)
        self.assertEqual(mounted["router"]["mountFace"],"right")
        self.assertGreater(mounted["router"]["mountNormalX"],.99)
        auto=self.page.evaluate("""layout=>{
          const e=window.WifiEngine;
          const right=e.mountCandidate(layout,6,4);
          const left=e.mountCandidate(layout,4,4);
          const leftRouter={...layout.router,x:left.x,z:left.z,mountFace:left.face,
             mountNormalX:left.mountNormalX,mountNormalZ:left.mountNormalZ};
          const rightRssi=e.value(layout,7,4);
          const facingAway=e.value({...layout,router:leftRouter},7,4);
          return {right,left,rightRssi,facingAway};
        }""",mounted)
        self.assertEqual(auto["right"]["face"],"right")
        self.assertEqual(auto["left"]["face"],"left")
        self.assertAlmostEqual(auto["right"]["x"],5.04,places=2)
        self.assertAlmostEqual(auto["left"]["x"],4.96,places=2)
        self.assertGreater(auto["rightRssi"],auto["facingAway"])
        self.page.locator("#nextWizardHeight").click()
        self.page.locator("#nextWizardAnalysis").click()
        self.page.wait_for_function("document.getElementById('applyBtn').disabled===false",timeout=30000)
        self.page.locator("#optimizeBtn").click()
        self.page.wait_for_function("document.getElementById('optimizeBtn').disabled===false",timeout=30000)
        self.assertTrue(self.page.locator("#recommendation").is_visible(),self.page.locator("#statusLine").inner_text())
        candidates=self.page.locator("#topThreeRows button[data-top-rank]").evaluate_all(
            "(els)=>els.map(el=>({x:Number(el.dataset.candidateX),z:Number(el.dataset.candidateZ)}))")
        self.assertTrue(candidates)
        for candidate in candidates:self.assertLess(abs(candidate["x"]-5),.06)
        self.page.locator("#topThreeRows button[data-top-rank]").first.click()
        self.page.wait_for_function("document.getElementById('applyBtn').disabled===false",timeout=30000)
        final=self.export()["router"]
        self.assertLess(abs(final["x"]-5),.06)
        self.assertIn(final["mountFace"],["right","left"])

    def test_receiver_height_independent_presets_manual_and_json(self):
        self.page.locator("#heightTab").click()
        self.assertIn("공유기 설치 높이",self.page.locator("#wizardHeight").inner_text())
        self.assertIn("스마트폰 사용 높이",self.page.locator("#wizardHeight").inner_text())
        self.assertAlmostEqual(self.export()["receiverY"],1)
        self.page.locator('[data-height="1.6"]').click()
        self.page.locator('[data-receiver-height=".7"]').click()
        saved=self.export()
        self.assertAlmostEqual(saved["router"]["y"],1.6)
        self.assertAlmostEqual(saved["receiverY"],.7)
        self.assertIn("앉아서 사용",self.page.locator("#receiverHeightSummary").inner_text())
        self.page.locator('[name="receiverHeightMode"][value="advanced"]').check()
        self.assertTrue(self.page.locator("#receiverHeightManual").is_visible())
        self.assertTrue(self.page.locator("#receiverHeightPresets").is_hidden())
        self.page.locator("#manualReceiverHeightInput").fill("2.8")
        self.page.locator("#manualReceiverHeightInput").press("Tab")
        saved=self.export()
        self.assertAlmostEqual(saved["receiverY"],2.8)
        self.assertAlmostEqual(saved["router"]["y"],1.6)
        self.page.locator("#importFile").set_input_files({
            "name":"heights.json","mimeType":"application/json",
            "buffer":json.dumps(saved).encode()
        })
        self.page.wait_for_function(
            "document.getElementById('toast').textContent.includes('XZ 도면을 불러왔습니다')",
            timeout=30000
        )
        loaded=self.export()
        self.assertAlmostEqual(loaded["receiverY"],2.8)
        self.assertAlmostEqual(loaded["router"]["y"],1.6)
        self.page.locator("#heightTab").click()
        self.assertIn("2.80m",self.page.locator("#receiverHeightSummary").inner_text())

    def test_mobile_four_step_labels_and_compact_toolbar(self):
        self.page.set_viewport_size({"width":390,"height":844})
        labels=self.page.locator(".view-tab").all_inner_texts()
        self.assertEqual(labels,["① 도면 그리기","② 공유기 설정","③ 높이 설정","④ 신호 분석"])
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"),410)
        toolbar=self.page.locator(".xp-toolbar")
        self.assertLess(toolbar.bounding_box()["height"],65)
        self.page.locator("#routerTab").click()
        self.assertTrue(self.page.locator("#wizardRouter").is_visible())
        self.assertEqual(self.page.locator("#mountFace").count(),0)
        self.page.locator("#heightTab").click()
        self.assertTrue(self.page.locator("#receiverHeightPresets").is_visible())

    def test_wall_mount_requires_actual_wall_and_rejects_invalid_json(self):
        self.page.locator("#routerTab").click()
        self.page.locator('[name="wizardMount"][value="wall"]').check()
        self.page.locator("#nextWizardHeight").click()
        self.assertEqual(self.page.locator("body").get_attribute("data-view"),"router")
        data=self.export()
        data["router"]["mountFace"]="sideways"
        self.page.locator("#importFile").set_input_files({"name":"bad-mount.json","mimeType":"application/json","buffer":json.dumps(data).encode()})
        self.page.wait_for_function("document.getElementById('toast').textContent.includes('벽 부착 방향')")
        self.assertEqual(self.export()["router"]["mountFace"],"right")

    def test_position_judgment_four_axis_walls(self):
        data=self.export()
        data["width"]=10
        data["depth"]=8
        data["router"]["x"]=5
        data["router"]["z"]=4
        data["walls"]=[
            {"id":"left","x1":2,"x2":2,"z1":2,"z2":6,"material":"concrete"},
            {"id":"right","x1":8,"x2":8,"z1":2,"z2":6,"material":"concrete"},
            {"id":"top","x1":2,"x2":8,"z1":2,"z2":2,"material":"concrete"},
            {"id":"bottom","x1":2,"x2":8,"z1":6,"z2":6,"material":"concrete"}]
        self.page.locator("#importFile").set_input_files({"name":"rectangle.json","mimeType":"application/json","buffer":json.dumps(data).encode()})
        self.page.wait_for_function("document.getElementById('numWallsChip').textContent.includes('벽 4')")
        self.page.locator("#applyBottomBtn").click()
        self.page.wait_for_function("document.getElementById('applyBtn').disabled===false",timeout=30000)
        self.page.locator("#positionJudgmentBtn").click()
        output=self.page.locator("#positionJudgment").inner_text()
        for expected in ["왼쪽: 3.00m","오른쪽: 3.00m","위쪽: 2.00m","아래쪽: 2.00m"]:
            self.assertIn(expected,output)

    def test_context_info_glossary_and_expert_restore(self):
        self.page.locator("#applyBottomBtn").click()
        self.page.wait_for_function("document.getElementById('applyBtn').disabled===false",timeout=30000)
        self.assertGreaterEqual(self.page.locator(".info-dot").count(),10)
        self.page.locator(".stat .info-dot[data-term='중요도 반영 품질']").click()
        self.assertTrue(self.page.locator("#infoDialog").is_visible())
        self.assertIn("Σ",self.page.locator("#infoContent").inner_text())
        self.page.locator("#infoClose").click()
        self.page.locator("#expertToggle").click()
        self.assertTrue(self.page.locator("#probeReadout").is_visible())
        self.assertTrue(self.page.locator("#calibrationComparison").is_visible())
        self.assertTrue(self.page.locator("#routerY").is_visible())
        self.page.locator("#infoGlossary").locator("summary").first.click()
        self.assertGreaterEqual(self.page.locator("#glossaryContent .info-entry").count(),16)

    def test_wooden_door_rf_loss_24_5_open_closed_two_crossings(self):
        fixture=self.export()
        results=self.page.evaluate("""base=>{
          const e=window.WifiEngine,out={};
          for(const frequency of [2.4,5]){
            const fixture={...base,width:10,depth:10,
              router:{...base.router,x:1,z:5,frequency,mountMode:'furniture'},
              walls:[{id:'left',x1:4,z1:1,x2:4,z2:9,material:'concrete'},
                     {id:'right',x1:7,z1:1,x2:7,z2:9,material:'concrete'}],
              doors:[]};
            const makeDoor=(id,wallId)=>({id,type:'wood',state:'closed',
                ...e.createDoor(fixture,wallId,.5,.9)});
            const a=makeDoor('a','left'),b=makeDoor('b','right');
            const noObstacles=e.value({...fixture,walls:[],doors:[]},9,5);
            const one=e.value({...fixture,doors:[a]},9,5);
            const oneOpen=e.value({...fixture,doors:[{...a,state:'open'}]},9,5);
            const two=e.value({...fixture,doors:[a,b]},9,5);
            const twoOpen=e.value({...fixture,doors:[{...a,state:'open'},{...b,state:'open'}]},9,5);
            const mixed=e.value({...fixture,doors:[a,{...b,state:'open'}]},9,5);
            const noCross=e.value({...fixture,doors:[a,b]},9,8);
            const noCrossBase=e.value({...fixture,doors:[]},9,8);
            const detail=e.value({...fixture,doors:[a,b]},9,5,undefined,true);
            out[frequency]={noObstacles,one,oneOpen,two,twoOpen,mixed,noCross,noCrossBase,detail,
              effectiveSegments:e.effectiveWalls({...fixture,doors:[a,b]}).length};
          }
          return out;
        }""",fixture)
        for freq,loss in [("2.4",4),("5",6)]:
            x=results[freq]
            # Each replaced passage must not also subtract the original wall's concrete loss.
            self.assertAlmostEqual(x["twoOpen"],x["noObstacles"],places=4)
            self.assertAlmostEqual(x["oneOpen"]-x["one"],loss,places=4)
            self.assertAlmostEqual(x["twoOpen"]-x["two"],2*loss,places=4)
            self.assertAlmostEqual(x["twoOpen"]-x["mixed"],loss,places=4)
            self.assertAlmostEqual(x["noCross"],x["noCrossBase"],places=4)
            self.assertEqual(x["effectiveSegments"],4)
            self.assertEqual(len(x["detail"]["walls"]),0)
            self.assertEqual(len(x["detail"]["doors"]),2)
            self.assertAlmostEqual(x["detail"]["doorLossDb"],2*loss,places=3)
            self.assertAlmostEqual(x["detail"]["wallLossDb"],0,places=3)
            self.assertAlmostEqual(x["detail"]["totalObstacleLossDb"],2*loss,places=3)

    def test_wooden_door_geometry_ends_and_overlap_prevent_double_loss(self):
        fixture=self.export()
        result=self.page.evaluate("""base=>{
          const e=window.WifiEngine;
          const wall={id:'w',x1:5,z1:2,x2:5,z2:8,material:'concrete'};
          const l={...base,width:10,depth:10,router:{...base.router,x:1,z:5,mountMode:'furniture'},
                   walls:[wall],doors:[]};
          const shape=e.createDoor(l,'w',.5,.9),d={id:'d',type:'wood',state:'closed',...shape};
          const closed={...l,doors:[d]},opened={...l,doors:[{...d,state:'open'}]};
          const edgeZ=d.z2;
          const edgeDetails=e.value(closed,9,edgeZ,undefined,true);
          let overlap=false,tooWide=false;
          try{e.createDoor(closed,'w',.5,.9);}catch(x){overlap=true;}
          try{e.createDoor(closed,'w',.5,7);}catch(x){tooWide=true;}
          return {edgeDetails,overlap,tooWide,
            left:e.value(closed,9,4,undefined,true),right:e.value(opened,9,4,undefined,true)};
        }""",fixture)
        self.assertTrue(result["overlap"])
        self.assertTrue(result["tooWide"])
        self.assertLessEqual(result["edgeDetails"]["totalObstacleLossDb"],7.0)
        self.assertAlmostEqual(result["left"]["rssiDbm"],result["right"]["rssiDbm"],delta=.11)

    def test_wooden_door_editor_state_width_position_delete_undo_and_json(self):
        data=self.export()
        data["width"]=10;data["depth"]=10
        data["walls"]=[{"id":"w","x1":5,"z1":1,"x2":5,"z2":9,"material":"concrete"}]
        data["router"]["x"]=2;data["router"]["z"]=5
        self.page.locator("#importFile").set_input_files({
            "name":"door-wall.json","mimeType":"application/json","buffer":json.dumps(data).encode()
        })
        self.page.wait_for_function("document.getElementById('numWallsChip').textContent.includes('벽 1')")
        self.page.locator('[data-tool="door"]').click()
        self.assertTrue(self.page.locator("#doorEditorPanel").is_visible())
        canvas=self.page.locator("#editorCanvas")
        box=canvas.bounding_box()
        canvas.click(position={"x":box["width"]*.5,"y":box["height"]*.5})
        saved=self.export()
        self.assertEqual(len(saved["doors"]),1)
        door=saved["doors"][0]
        self.assertEqual(door["state"],"closed")
        self.assertAlmostEqual(door["widthM"],.9)
        self.assertEqual(door["wallId"],"w")
        self.assertEqual(len(self.page.evaluate("layout=>window.WifiEngine.effectiveWalls(layout)",saved)),2)
        self.assertTrue(self.page.locator("#doorSelectedControls").is_visible())
        self.page.locator("#doorWidthInput").fill("1.2")
        self.page.locator("#doorWidthInput").press("Tab")
        self.assertAlmostEqual(self.export()["doors"][0]["widthM"],1.2)
        self.page.locator("#doorPositionInput").fill("65")
        self.page.locator("#doorPositionInput").dispatch_event("change")
        self.assertAlmostEqual(self.export()["doors"][0]["centerT"],.65,delta=.02)
        self.page.locator("#doorStateBtn").click()
        self.assertEqual(self.export()["doors"][0]["state"],"open")
        saved=self.export()
        self.page.locator("#importFile").set_input_files({
            "name":"saved-doors.json","mimeType":"application/json","buffer":json.dumps(saved).encode()
        })
        self.page.wait_for_function("document.getElementById('toast').textContent.includes('XZ 도면을 불러왔습니다')")
        self.assertEqual(self.export()["doors"],saved["doors"])
        self.page.locator('[data-tool="door"]').click()
        self.page.locator("#doorDeleteBtn").click()
        self.assertEqual(len(self.export()["doors"]),0)
        self.page.locator("#undoBtn").click()
        self.assertEqual(len(self.export()["doors"]),1)

    def test_wooden_door_invalid_json_rejects_without_overwriting(self):
        data=self.export()
        data["walls"]=[{"id":"w","x1":4,"z1":1,"x2":4,"z2":7,"material":"concrete"}]
        self.page.locator("#importFile").set_input_files({
            "name":"good-wall.json","mimeType":"application/json","buffer":json.dumps(data).encode()
        })
        self.page.wait_for_function("document.getElementById('toast').textContent.includes('XZ 도면을 불러왔습니다')")
        before=self.export()
        for issue in ["orphan","offwall","overlap"]:
            bad=json.loads(json.dumps(before))
            door={"id":"d","type":"wood","state":"closed","wallId":"w",
                  "x1":4,"z1":3.55,"x2":4,"z2":4.45,"widthM":.9}
            if issue=="orphan":door["wallId"]="missing"
            if issue=="offwall":door["x1"]=5;door["x2"]=5
            bad["doors"]=[door]
            if issue=="overlap":bad["doors"].append({**door,"id":"d2"})
            self.page.locator("#importFile").set_input_files({
                "name":"bad-door-"+issue+".json","mimeType":"application/json","buffer":json.dumps(bad).encode()
            })
            self.page.wait_for_function(
                "document.getElementById('toast').textContent.includes('JSON 불러오기 실패')",
                timeout=10000
            )
            self.assertEqual(self.export(),before)

    def test_wooden_door_comparison_live_heatmap_and_square_info(self):
        data=self.export()
        data["width"]=10;data["depth"]=10
        data["router"]["x"]=1;data["router"]["z"]=5
        data["walls"]=[{"id":"w","x1":5,"z1":1,"x2":5,"z2":9,"material":"concrete"}]
        self.page.locator("#importFile").set_input_files({
            "name":"door-analysis.json","mimeType":"application/json","buffer":json.dumps(data).encode()
        })
        self.page.wait_for_function("document.getElementById('toast').textContent.includes('XZ 도면을 불러왔습니다')")
        self.page.locator('[data-tool="door"]').click()
        box=self.page.locator("#editorCanvas").bounding_box()
        self.page.locator("#editorCanvas").click(position={"x":box["width"]*.5,"y":box["height"]*.5})
        self.page.locator("#applyBottomBtn").click()
        self.page.wait_for_function("document.getElementById('applyBtn').disabled===false",timeout=30000)
        self.assertTrue(self.page.locator("#doorAnalysisPanel").is_visible())
        self.assertIn("모두 열림",self.page.locator("#doorComparison").inner_text())
        panel=self.page.locator("#doorAnalysisList button")
        self.assertEqual(panel.count(),1)
        panel.click()
        self.page.wait_for_function(
            "document.getElementById('applyBtn').disabled===false && document.getElementById('doorAnalysisList').textContent.includes('열림')",
            timeout=30000
        )
        self.assertEqual(self.export()["doors"][0]["state"],"open")
        self.page.locator("#positionJudgmentBtn").click()
        self.assertIn("왼쪽",self.page.locator("#positionJudgment").inner_text())
        dots=self.page.locator(".info-dot")
        self.assertGreater(dots.count(),0)
        dims=dots.first.evaluate("(e)=>({w:e.getBoundingClientRect().width,h:e.getBoundingClientRect().height,r:getComputedStyle(e).borderRadius})")
        self.assertLessEqual(dims["w"],24)
        self.assertLessEqual(dims["h"],24)
        self.assertEqual(dims["r"],"3px")

    def test_xp_luna_chrome_and_menus_visible(self):
        self.assertTrue(self.page.locator(".xp-caption").is_visible())
        self.assertIn("Wiplan - Wi-Fi 배치 시뮬레이터", self.page.locator(".xp-caption").inner_text())
        self.assertEqual(self.page.locator(".xp-menu").count(), 5)
        self.assertEqual(self.page.locator(".xp-toolbar button").count(), 8)
        self.assertIn("linear-gradient", self.page.locator(".xp-caption").evaluate("(e)=>getComputedStyle(e).backgroundImage"))
        self.assertEqual(self.page.locator(".xp-toolbar [data-xp-action='optimize']").get_attribute("type"), "button")
        self.assertTrue(self.page.locator("#editorCanvas").is_visible())

    def test_xp_menu_save_new_undo_and_help_are_functional(self):
        self.pin()
        self.assertEqual(len(self.export()["requiredPins"]), 1)
        self.page.locator(".xp-menu").first.locator("summary").click()
        self.assertTrue(self.page.locator(".xp-menu").first.evaluate("(e)=>e.open"))
        with self.page.expect_download() as task:
            self.page.locator(".xp-menu").first.locator("[data-xp-action='save']").click()
        downloaded=json.loads(task.value.path().read_text(encoding="utf-8"))
        self.assertEqual(len(downloaded["requiredPins"]),1)
        self.assertFalse(self.page.locator(".xp-menu").first.evaluate("(e)=>e.open"))
        self.page.locator(".xp-toolbar [data-xp-action='new']").click()
        self.assertEqual(self.export()["requiredPins"], [])
        self.page.locator(".xp-toolbar [data-xp-action='undo']").click()
        self.assertEqual(len(self.export()["requiredPins"]),1)
        self.page.locator(".xp-toolbar [data-xp-action='help']").click()
        self.assertTrue(self.page.locator("#xpHelpDialog").is_visible())
        self.assertIn("신호 원활·중간·혼잡",self.page.locator("#xpHelpDialog").inner_text())
        self.page.locator("#xpHelpClose").click()
        self.assertFalse(self.page.locator("#xpHelpDialog").is_visible())

    def test_xp_toolbar_simulation_and_optimizer_run_real_engine(self):
        self.page.locator(".xp-toolbar [data-xp-action='run']").click()
        self.page.wait_for_function(
            "document.body.dataset.view==='analysis' && "
            "document.getElementById('applyBtn').disabled===false && "
            "document.getElementById('engineMode').textContent.includes('중간')",
            timeout=30000,
        )
        self.assertIn("/ 100",self.page.locator("#meanStat").inner_text())
        self.page.locator("#expertToggle").click()
        self.assertIn("dBm",self.page.locator("#meanStat").inner_text())
        self.page.locator(".xp-toolbar [data-xp-action='optimize']").click()
        self.page.wait_for_function("document.getElementById('optimizeBtn').disabled===false",timeout=30000)
        self.assertTrue(self.page.locator("#recommendation").is_visible(),self.page.locator("#statusLine").inner_text())
        self.assertTrue(self.page.locator("#topThreeCandidates").is_visible())
        self.page.locator(".xp-toolbar [data-xp-action='palette']").click()
        self.assertTrue(self.page.locator("#editorScreen").is_visible())
        self.assertTrue(self.page.locator("#toolsRail").is_visible())

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
        self.page.locator("#expertToggle").click()
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
            ["신호 원활", "중간", "혼잡"],
        )
        self.assertEqual(self.page.locator("#profileComparisonRows .profile-meter span").count(), 3)
        self.assertTrue(self.page.locator("#calibrationComparison").is_hidden())
        self.page.locator("#expertToggle").click()
        self.assertTrue(self.page.locator("#calibrationComparison").is_visible())
        self.assertEqual(self.page.locator("#calibrationComparisonRows > div").count(), 2)
        self.assertIn("보정 전 (기존)", self.page.locator("#calibrationComparisonRows").inner_text())
        self.assertIn("보정 후 (중간)", self.page.locator("#calibrationComparisonRows").inner_text())
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
            "document.getElementById('engineMode').textContent.includes('중간')",
            timeout=30000,
        )
        saved=self.export()
        self.assertAlmostEqual(saved["router"]["x"],coords[1][0],places=5)
        self.assertAlmostEqual(saved["router"]["z"],coords[1][1],places=5)
        self.assertTrue(self.page.locator("#recommendation").is_hidden())
        self.assertTrue(self.page.locator("#calibrationComparison").is_hidden())
        self.page.locator("#expertToggle").click()
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
        self.page.locator("#expertToggle").click()
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
        self.assertEqual(self.page.locator("#candidateCompare .compare-line b").all_inner_texts(), ["신호 원활", "중간", "혼잡"])
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
                "(label)=>document.getElementById('toast').textContent.includes(label)", arg=label)
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
        self.page.locator("#expertToggle").click()
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
