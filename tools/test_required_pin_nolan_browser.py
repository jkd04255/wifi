"""Browser checks for one-point-only mandatory pins in standalone file:// HTML."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

html = Path("dist/WiFi_Placement_RequiredPoint_70_NoLAN.html").resolve()
assert html.exists()

with sync_playwright() as play:
    for engine in ("chromium", "webkit"):
        browser = getattr(play,engine).launch(headless=True)
        page = browser.new_page(viewport={"width":1440,"height":900},accept_downloads=True)
        errors=[]
        page.on("pageerror",lambda error:errors.append(str(error)))
        try:
            page.goto(html.as_uri(),wait_until="load",timeout=30000)
            assert page.locator('[data-tool="required"]').count()==1
            assert page.locator('[data-tool="zone"]').count()==0
            for retired in ("requiredRadius","selectedRequiredRadius","requiredRadiusValue",
                            "selectedRequiredRadiusValue","roomDrawer","g3LanX","g3LanZ",
                            "g3LanY","g3Cable","g3Mode","g3Settings"):
                assert page.locator("#"+retired).count()==0,retired
            assert "정확히 지정한 점 1곳" in page.locator("#requiredDrawer").inner_text()
            if page.evaluate("document.body.dataset.view") != "design":
                page.locator("#backToEditorBtn").click()
            page.wait_for_function("document.body.dataset.view==='design'",timeout=10000)
            page.locator('[data-tool="required"]').click()
            canvas=page.locator("#editorCanvas")
            box=canvas.bounding_box()
            assert box and box["width"]>100
            canvas.click(position={"x":box["width"]/2,"y":box["height"]/2})
            assert "필수영역" in page.locator("#elementList").text_content()
            assert "반경" not in page.locator("#elementList").text_content().split("필수영역")[-1]
            with page.expect_download() as dl:
                page.locator("#exportBtn").click()
            saved=json.loads(dl.value.path().read_text(encoding="utf-8"))
            assert len(saved["requiredPins"])==1
            assert saved["requiredPins"][0]["minQualityScore"]==70
            assert "radiusM" not in saved["requiredPins"][0]
            # Import old v1.6-style radius JSON: center coordinates are kept;
            # obsolete radius is silently ignored and not exported again.
            legacy=json.loads(json.dumps(saved))
            legacy["requiredPins"][0]["radiusM"]=2.8
            page.locator("#importFile").set_input_files({
                "name":"old-radius-layout.json",
                "mimeType":"application/json",
                "buffer":json.dumps(legacy).encode("utf-8"),
            })
            page.wait_for_function("document.body.dataset.view==='design'",timeout=15000)
            with page.expect_download() as dl:
                page.locator("#exportBtn").click()
            converted=json.loads(dl.value.path().read_text(encoding="utf-8"))
            assert len(converted["requiredPins"])==1
            assert converted["requiredPins"][0]["x"]==saved["requiredPins"][0]["x"]
            assert converted["requiredPins"][0]["z"]==saved["requiredPins"][0]["z"]
            assert "radiusM" not in converted["requiredPins"][0]
            page.locator("#applyBottomBtn").click()
            page.wait_for_function("document.body.dataset.view==='analysis'",timeout=15000)
            page.locator("#optimizeBtn").click()
            page.wait_for_function(
                "document.getElementById('statusLine').textContent.includes('추천 완료')"
                "||document.getElementById('statusLine').textContent.includes('추천 실패')",
                timeout=60000)
            state=page.locator("#statusLine").inner_text()
            assert "추천 완료" in state,(engine,state)
            assert page.locator("#recommendation").is_visible()
            recommendation=page.locator("#recommendBody").inner_text()
            assert "70점 이상" in recommendation,recommendation
            assert "총 1개" in recommendation,recommendation
            assert "배선 제약" in recommendation or "조건 없이 계산" in recommendation
            assert "17개" not in recommendation
            results=page.locator("#requiredResults").inner_text()
            assert "추천 최소" in results,results
            assert "70점 충족" in results,results
            assert "반경" not in results,results
            # Router and receiver heights remain configurable, but are never
            # limited by a ceiling or any old wall-height field.
            assert page.locator("#roomHeightM").count()==0
            assert page.locator("#routerY").get_attribute("type")=="number"
            assert page.locator("#routerY").get_attribute("max") is None
            assert page.locator("#receiverY").get_attribute("max") is None
            page.locator("#routerY").fill("12.5")
            page.locator("#routerY").dispatch_event("change")
            page.locator("#receiverY").fill("13.5")
            page.locator("#receiverY").dispatch_event("change")
            assert page.locator("#routerY").input_value()=="12.5"
            assert page.locator("#receiverY").input_value()=="13.5"
            page.locator("#backToEditorBtn").click()
            with page.expect_download() as dl:
                page.locator("#exportBtn").click()
            heights=json.loads(dl.value.path().read_text(encoding="utf-8"))
            assert "roomHeightM" not in heights
            assert heights["router"]["y"]==12.5
            assert heights["receiverY"]==13.5
            # Import old ceiling and low wall metadata, then export. The
            # coordinates/Y stay, but ceiling and individual wall heights vanish.
            old_height=json.loads(json.dumps(heights))
            old_height["roomHeightM"]=0.5
            old_height["walls"].append({"id":"old-short-wall",
                "x1":1,"z1":1,"x2":2,"z2":2,"material":"concrete","heightM":0.01})
            page.locator("#importFile").set_input_files({
                "name":"legacy-height-bound-layout.json",
                "mimeType":"application/json",
                "buffer":json.dumps(old_height).encode("utf-8"),
            })
            page.wait_for_function("document.body.dataset.view==='design'",timeout=15000)
            with page.expect_download() as dl:
                page.locator("#exportBtn").click()
            reexport=json.loads(dl.value.path().read_text(encoding="utf-8"))
            assert "roomHeightM" not in reexport
            assert "heightM" not in reexport["walls"][-1]
            assert reexport["router"]["y"]==12.5
            assert reexport["receiverY"]==13.5
            assert not errors,errors
            print(engine.upper(),"ONE_POINT_REQUIRED_70_OFFLINE_HTML_PASS")
        finally:
            browser.close()
