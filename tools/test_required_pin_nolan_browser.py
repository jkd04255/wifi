"""End-to-end offline file:// smoke tests for shipped no-LAN HTML on Windows CI."""
from pathlib import Path
from playwright.sync_api import sync_playwright

html=Path("dist/WiFi_Placement_RequiredPin_70_NoLAN.html").resolve()
assert html.exists()

with sync_playwright() as p:
    for engine in ("chromium","webkit"):
        browser=getattr(p,engine).launch(headless=True)
        page=browser.new_page(viewport={"width":1440,"height":900},accept_downloads=True)
        errors=[]
        page.on("pageerror",lambda err: errors.append(str(err)))
        try:
            page.goto(html.as_uri(),wait_until="load",timeout=30000)
            assert page.locator('[data-tool="required"]').count()==1
            assert page.locator('[data-tool="zone"]').count()==0
            assert page.locator("#roomDrawer").count()==0
            for unused in ("g3LanX","g3LanZ","g3LanY","g3Cable","g3Mode","g3Settings"):
                assert page.locator("#"+unused).count()==0,unused
            page.locator("#backToEditorBtn").click()
            page.wait_for_function("document.body.dataset.view==='design'",timeout=10000)
            page.locator('[data-tool="required"]').click()
            assert page.locator("#requiredRadius").is_visible()
            canvas=page.locator("#editorCanvas")
            box=canvas.bounding_box()
            assert box and box["width"]>100
            canvas.click(position={"x":box["width"]/2,"y":box["height"]/2})
            assert "필수영역" in page.locator("#elementList").text_content()
            page.locator("#applyBottomBtn").click()
            page.wait_for_function("document.body.dataset.view==='analysis'",timeout=10000)
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
            assert "총 17개 표본점" in recommendation,recommendation
            assert "배선 제약" in recommendation,recommendation
            results=page.locator("#requiredResults").inner_text()
            assert "추천 최소" in results,results
            assert "70점 충족" in results,results
            assert not errors,errors
            print(engine.upper(),"REQUIRED_PIN_70_NO_LAN_BROWSER_PASS")
        finally:
            browser.close()
