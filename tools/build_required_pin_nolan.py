"""Build a fully offline, no-LAN-port distribution from the unmodified Draft PR #3.

This release is isolated on feat/optimizer-required-pin-distribution; never edit
preview/stage3.html, original v1.6, backend 4, main or deployed GitHub Pages.
"""
from pathlib import Path
import re

source = Path("preview/stage3.html").read_text(encoding="utf-8")
assert 'data-tool="required"' in source
assert 'data-tool="zone"' not in source
assert 'id="requiredRadius"' in source


def replace_once(old: str, new: str, name: str) -> None:
    global source
    if source.count(old) != 1:
        raise ValueError(f"{name}: expected one anchor, got {source.count(old)}")
    source = source.replace(old, new)


# Expose no cable length, no LAN port coordinate and no optimizer mode selector.
start = source.index('<details id="g3Settings"')
end = source.index('</details>', start) + len('</details>')
source = (source[:start] +
    '<p id="g3ModeInfo" role="status" style="font-size:11px;line-height:1.6;color:#536985;'
    'border:1px solid #dce5ef;background:#fff;border-radius:10px;padding:12px">'
    '공유기 위치는 벽과 중요도, 필수영역의 예상 품질 70점 이상을 기준으로 최적화합니다. '
    '배선 제약은 적용하지 않습니다. 실측 미보정 RSSI 예측입니다.</p>' +
    source[end:])

source = source.replace("$('g3Mode').value='local';", "")
replace_once(
    "  if(requiredPins.length)$('g3Mode').value='local';",
    "", "deprecated import mode setting"
) if "  if(requiredPins.length)$('g3Mode').value='local';" in source else None

# Use the existing v1.6 path-loss and weighting engine, with a hard 70-point
# feasibility constraint on the 17 samples of EVERY mandatory pin.
start = source.index(" function optimize(layout,gridStep=.35,searchStep=.75,weighted=true){")
end = source.index("\n global.WifiEngine=", start)
engine = r"""
 function optimize(layout,gridStep=.35,searchStep=.75,weighted=true){
   const L=normalizeLayout(layout),p=settings(L),sample=[];
   const pins=L.requiredPins||[],mandatory=[];
   for(const pin of pins)mandatory.push({x:pin.x,z:pin.z,minimum:70});
   const columns=Math.max(1,Math.ceil(L.width/gridStep)),rows=Math.max(1,Math.ceil(L.depth/gridStep));
   for(let row=0;row<rows;row++)for(let col=0;col<columns;col++){
     const x=Math.min(L.width,(col+.5)*gridStep),z=Math.min(L.depth,(row+.5)*gridStep);
     sample.push({x,z,w:weighted?weight(L,x,z):1});
   }
   let wtotal=sample.reduce((a,s)=>a+s.w,0);
   if(wtotal<=0){sample.forEach(s=>s.w=1);wtotal=sample.length;}
   function evaluate(x,z){
     const trial={...L,router:{...L.router,x,z}};
     let quality=0,weak=0,good=0,dbm=0;
     for(const s of sample){
       const v=value(trial,s.x,s.z,p);
       quality+=clamp((v+90)/55*100,0,100)*s.w;
       weak+=(v< -75?s.w:0);good+=(v>=-67?s.w:0);dbm+=v*s.w;
     }
     return {objective:quality/wtotal-.12*weak/wtotal*100,
       stats:{qualityScore:+(quality/wtotal).toFixed(1),
         weightedWeakPct:+(weak/wtotal*100).toFixed(1),
         weightedGoodPct:+(good/wtotal*100).toFixed(1),
         weightedMeanDbm:+(dbm/wtotal).toFixed(1)}};
   }
   function minRequired(x,z){
     if(!mandatory.length)return null;
     const trial={...L,router:{...L.router,x,z}};
     let min=100;
     for(const point of mandatory){
       const q=clamp((value(trial,point.x,point.z,p)+90)/55*100,0,100);
       if(q<min)min=q;
       if(min+1e-8<point.minimum)return min;
     }
     return min;
   }
   function feasible(x,z){
     // Keep the access point physically inside the floor, never on its edge.
     if(x<.2||x>L.width-.2||z<.2||z>L.depth-.2)return false;
     for(const a of L.walls||[]){
       const dx=a.x2-a.x1,dz=a.z2-a.z1,d2=dx*dx+dz*dz;
       const t=d2?clamp(((x-a.x1)*dx+(z-a.z1)*dz)/d2,0,1):0;
       if(Math.hypot(x-(a.x1+t*dx),z-(a.z1+t*dz))<.2)return false;
     }
     const min=minRequired(x,z);
     return min===null||min+1e-8>=70;
   }
   const ncol=Math.max(2,Math.ceil(L.width/searchStep)),nrow=Math.max(2,Math.ceil(L.depth/searchStep));
   const coord=(i,count,length)=>length<=.7?length/2:.35+(length-.7)*i/(count-1);
   let best={objective:-Infinity,x:0,z:0,stats:null},evaluated=0,feasibleCount=0;
   function check(x,z){
     evaluated++;
     if(!feasible(x,z))return;
     feasibleCount++;
     const result=evaluate(x,z);
     if(result.objective>best.objective)best={...result,x,z};
   }
   for(let row=0;row<nrow;row++)for(let col=0;col<ncol;col++)
     check(coord(col,ncol,L.width),coord(row,nrow,L.depth));
   // Include existing router and pin centers so narrow valid regions are not
   // discarded merely because the coarse grid misses them.
   check(L.router.x,L.router.z);
   for(const pin of pins)check(pin.x,pin.z);
   if(!Number.isFinite(best.objective)){
     if(pins.length)return {
       status:'no_feasible_candidate',best:null,requiredAreaSatisfied:false,
       requiredAreaSampleCount:mandatory.length,
       reason:'탐색한 위치 중 필수영역 전체 표본점 70점과 벽 조건을 만족하는 공유기 후보가 없습니다.'
     };
     const fallback=evaluate(L.router.x,L.router.z);
     best={...fallback,x:L.router.x,z:L.router.z};
   }
   for(const scale of [searchStep/2,searchStep/4]){
     const center={x:best.x,z:best.z};
     for(const dx of [-scale,0,scale])for(const dz of [-scale,0,scale])
       check(clamp(center.x+dx,0,L.width),clamp(center.z+dz,0,L.depth));
   }
   const current=evaluate(L.router.x,L.router.z),min=minRequired(best.x,best.z);
   if(pins.length&&(min===null||min+1e-8<70))
     return {status:'no_feasible_candidate',best:null,requiredAreaSatisfied:false,
       requiredAreaSampleCount:mandatory.length,
       reason:'필수영역 품질을 검증하지 못했습니다.'};
   return {
     status:'ok',stage3:true,
     best:{x:best.x,y:L.router.y,z:best.z},
     bestStats:best.stats,currentStats:current.stats,
     improvementPoints:+(best.objective-current.objective).toFixed(1),
     criterion:'weighted predicted RSSI quality and hard required-area 70, no LAN constraint',
     candidates:evaluated,feasibleCandidatesCount:feasibleCount,weightsUsed:weighted,
     signalSource:'v1.6_local_estimate',
     requiredAreaSatisfied:pins.length?true:null,
     requiredAreaMinimumQualityScore:min===null?null:+min.toFixed(2),
     requiredAreaSampleCount:mandatory.length,
     reason:'벽·중요도·필수영역 예측 품질 기준이며 배선 제약을 적용하지 않았습니다.'
   };
 }
"""
source = source[:start] + engine + source[end:]

# All grid/heatmap and optimization now run locally in the browser.
start = source.index("async function simulate(w){")
end = source.index("function renderStats(){", start)
simulate = r"""async function simulate(w){
 weighted=w;setBusy(true);
 $('statusLine').classList.remove('error');
 $('statusLine').textContent='RSSI를 로컬에서 계산하고 있습니다…';
 await new Promise(resolve=>setTimeout(resolve,25));
 try{
  result=window.WifiEngine.grid(L,.25,w);
  $('engineMode').textContent='오프라인 JS 예측 엔진 · 실측 미보정';
  applied();best=null;$('recommendation').hidden=true;
  $('heatmapEmpty').style.display='none';renderHeat();renderStats();renderProbe();
  $('statusLine').textContent=w?'중요도 반영 품질을 계산했습니다.':'RSSI 히트맵을 계산했습니다.';
 }catch(e){
  $('statusLine').classList.add('error');
  $('statusLine').textContent='계산 실패: '+e.message;
  toast('계산 실패: '+e.message);
 }finally{setBusy(false)}
}
"""
source=source[:start]+simulate+source[end:]

# Remove Python-backed GATE 3 adapter and any mandatory LAN-port fields.
start=source.index("async function g3LocalOptimize(){")
end=source.index("$('optimizeBtn').onclick=async()=>{",start)
source=source[:start]+source[end:]

start=source.index("$('optimizeBtn').onclick=async()=>{")
end=source.index("$('useBestBtn').onclick=async()=>{",start)
handler=r"""$('optimizeBtn').onclick=async()=>{
 setBusy(true);$('statusLine').classList.remove('error');
 $('statusLine').textContent='벽·중요도·필수영역을 반영해 공유기 위치를 탐색합니다…';
 await new Promise(resolve=>setTimeout(resolve,30));
 try{
  const useWeights=weighted||(L.importanceStrokes||[]).length>0;
  const proposal=window.WifiEngine.optimize(L,.35,.75,useWeights);
  if(proposal.status!=='ok'||!proposal.best)
    throw Error(proposal.reason||'필수영역 품질 70점 기준을 만족하는 후보가 없습니다.');
  if((L.requiredPins||[]).length&&proposal.requiredAreaSatisfied!==true)
    throw Error('필수영역 70점 검증에 실패했습니다. 추천하지 않습니다.');
  best=proposal;
  $('engineMode').textContent='오프라인 JS 최적화 · 랜 포트 제약 없음 · 실측 미보정';
  $('g3ModeInfo').textContent='배선 제약 없이 벽·중요도·필수영역의 예측 품질로 추천합니다. 실측 보정이 아닙니다.';
  const b=best.best,box=$('recommendBody');box.replaceChildren();
  const pos=document.createElement('div');
  pos.textContent='추천 좌표: X '+fmt(b.x,2)+' m · Y '+fmt(b.y,2)+' m · Z '+fmt(b.z,2)+' m';
  const score=document.createElement('div');
  score.textContent='품질 지수: '+fmt(best.currentStats.qualityScore)+' → '+fmt(best.bestStats.qualityScore)+' · 개선 '+fmt(best.improvementPoints)+'점';
  const count=document.createElement('div');
  count.textContent='후보 '+best.candidates+'개 평가 · '+(best.weightsUsed?'중요도 반영':'전체 공간 동일 가중치');
  const note=document.createElement('div');
  note.textContent='랜 포트·랜선 길이 조건 없이 계산했습니다. 벽을 고려한 RSSI 모델 예측값입니다.';
  note.style.cssText='font-weight:650;margin-top:8px';
  const warning=document.createElement('div');
  warning.textContent='17개 표본점/핀을 검사하며, 원 전체의 연속적 품질이나 실측 무선 성능을 보장하지 않습니다.';
  warning.style.color='#a34a35';
  box.append(pos,score,count,note,warning);
  if((L.requiredPins||[]).length){
   const passed=document.createElement('div');
   passed.style.cssText='font-weight:750;color:#168060;margin-top:8px';
   passed.textContent='필수영역 '+L.requiredPins.length+'곳 · 총 '+best.requiredAreaSampleCount+
     '개 표본점 전부 예상 품질 70점 이상 · 최저 '+fmt(best.requiredAreaMinimumQualityScore,1)+'점';
   box.append(passed);
  }
  $('recommendation').hidden=false;
  $('statusLine').textContent='필수영역 70점 조건을 지키는 위치 추천 완료 (미보정 모델 예측).';
  renderHeat();renderRequiredStatus();
  if(!result)toast('추천 완료. Apply를 눌러 히트맵도 확인하세요.');
 }catch(e){
  best=null;$('recommendation').hidden=true;
  renderHeat();renderRequiredStatus();
  $('statusLine').classList.add('error');
  $('statusLine').textContent='추천 실패: '+e.message;
 }finally{setBusy(false)}
};
"""
source=source[:start]+handler+source[end:]

# Retired API settings should never be required for pin placement or import.
source=source.replace("$('g3Mode').value='local';","")
source=source.replace("  if(requiredPins.length)$('g3Mode').value='local';","")
source=source.replace('Wi-Fi Placement Studio | 배치 시뮬레이터 v1.6',
                      'Wi-Fi Placement Studio | 필수영역 70점 · 배선 무관')
source=source.replace('Wi-Fi Placement Studio v1.6 · Offline + Python API',
                      'Wi-Fi Placement Studio · 오프라인 필수영역 70점')
source=source.replace('추천하려면 4번 Python 로컬 API 실행과 LAN 포트·랜선 길이 입력이 필요합니다.',
                      '추천은 로컬 RSSI 모델로 실행되며 별도 배선 정보 입력은 필요하지 않습니다.')


# Point-only mandatory pins: every pin tests exactly its X/Z coordinate.
# Keep the pre-existing wall/importance tools and 70-point hard feasibility.
def replace_section(begin: str, finish: str, replacement: str, label: str) -> None:
    global source
    first=source.find(begin)
    assert first>=0, f"{label}: beginning anchor not found"
    last=source.find(finish,first+len(begin))
    assert last>first, f"{label}: end anchor not found"
    source=source[:first]+replacement+source[last:]


replace_section(
    '<details class="palette-drawer" id="requiredDrawer">',
    '<details class="palette-drawer" id="elementsDrawer">',
    """<details class="palette-drawer" id="requiredDrawer">
    <summary><span>◎ 필수영역 · 지정 점 예상 품질 70점 이상</span><span class="summary-meta">위치 핀</span></summary>
    <div class="drawer-content">
      <p>필수영역은 <b>정확히 지정한 점 1곳</b>에서 예상 Wi-Fi 품질 70점 이상을 요구합니다. 반경이나 면적 검사는 없습니다.</p>
      <p>도면에서 핀을 클릭해 추가하고 중심을 드래그해 이동할 수 있습니다. 기존 핀을 여러 개 지정할 수도 있습니다.</p>
      <div id="requiredPinPicker" hidden style="border-top:1px solid #dce5ef;padding-top:10px;margin-top:10px">
        <label class="field-label" for="requiredPinSelect">편집할 필수영역 핀</label>
        <div class="required-picker-row"><select id="requiredPinSelect" aria-label="편집할 필수영역 핀 선택"></select><button type="button" id="requiredNextPin" class="secondary" aria-label="다음 필수영역 핀 선택">다음 핀</button></div>
        <p id="requiredSelectionStatus" role="status" aria-live="polite" class="required-selection-hint">핀을 드래그해 이동하세요. 겹친 핀은 반복 터치하거나 목록에서 선택할 수 있습니다.</p>
      </div>
      <div id="requiredSelectedControls" hidden style="border-top:1px solid #dce5ef;margin-top:12px;padding-top:12px">
        <strong id="requiredSelectedName">선택된 필수영역</strong><p id="requiredSelectedHint" style="font-size:11px">선택 핀의 좌표를 드래그·방향키로 변경할 수 있습니다.</p>
      </div>
      <p>기존 벽과 중요도 브러시는 그대로 반영합니다. 별도의 랜 포트·랜선 정보는 필요하지 않습니다. 최대 12개.</p>
    </div>
  </details>
  """,
    "required pin drawer")

replace_section(
    'function requiredSamples(pin){',
    'function qualityPoint(rssi)',
    """function requiredSamples(pin){return [{x:pin.x,z:pin.z}];}
""", "single exact location")

replace_section(
    "function drawRequiredPin(ctx,pin,sx,sy,passed=null){",
    "function renderRequiredStatus(){",
    """function drawRequiredPin(ctx,pin,sx,sy,passed=null){
 const x=pin.x*sx,y=pin.z*sy;
 const color=passed===true?'#138b66':passed===false?'#c85448':'#6949c6';
 ctx.save();
 ctx.beginPath();ctx.arc(x,y,15,0,Math.PI*2);
 ctx.fillStyle='rgba(255,255,255,.85)';ctx.fill();
 ctx.strokeStyle=color;ctx.lineWidth=1.6;ctx.stroke();
 ctx.beginPath();ctx.arc(x,y-5,7,Math.PI,0);
 ctx.lineTo(x,y+10);ctx.closePath();ctx.fillStyle=color;ctx.fill();
 ctx.beginPath();ctx.arc(x,y-5,2.5,0,Math.PI*2);
 ctx.fillStyle='#fff';ctx.fill();
 ctx.font='bold 11px Malgun Gothic,sans-serif';ctx.fillStyle=color;
 ctx.fillText('70+',x+15,y-14);
 if(pin.id&&pin.id===selectedRequiredId&&ctx===eCtx){
  ctx.beginPath();ctx.arc(x,y,19,0,Math.PI*2);
  ctx.strokeStyle='#fff';ctx.lineWidth=4;ctx.stroke();
  ctx.beginPath();ctx.arc(x,y,21,0,Math.PI*2);
  ctx.strokeStyle='#3c228e';ctx.lineWidth=2.5;ctx.stroke();
 }
 ctx.restore();
}
""", "visible point pin without radius circle")

replace_once(
    """ $('selectedRequiredRadius').value=String(pin.radiusM);
 $('selectedRequiredRadius').setAttribute('aria-valuetext',fmt(pin.radiusM)+'미터');
 $('selectedRequiredRadiusValue').textContent=fmt(pin.radiusM)+' m';
 $('requiredSelectedHint').textContent='선택된 필수영역 '+n+'의 반경을 수정합니다. 키보드 방향키로도 조절할 수 있습니다.';""",
    """ $('requiredSelectedHint').textContent='선택한 핀의 정확한 좌표가 품질 70점 이상인지 검증합니다. 방향키로 이동할 수 있습니다.';""",
    "remove selected pin radius state")

replace_once(
    " $('requiredStatus').textContent='필수영역 없음 · 반경의 17개 표본점당 예상 품질 ≥70';",
    " $('requiredStatus').textContent='필수영역 없음 · 지정한 각 점의 예상 품질 ≥70';",
    "point-only status")
replace_once(
    "  name.textContent='◎ 필수영역 '+(i+1)+' · 반경 '+fmt(pin.radiusM)+'m';",
    "  name.textContent='◎ 필수영역 '+(i+1)+' · X '+fmt(pin.x,2)+'m / Z '+fmt(pin.z,2)+'m';",
    "per-point result title") if "  name.textContent='◎ 필수영역 '+(i+1)+' · 반경 '+fmt(pin.radiusM)+'m';" in source else None
source=source.replace(
    "name.textContent='◎ 필수영역 '+(i+1)+' · 반경 '+fmt(pin.radiusM)+'m';",
    "name.textContent='◎ 필수영역 '+(i+1)+' · X '+fmt(pin.x,2)+'m / Z '+fmt(pin.z,2)+'m';")
source=source.replace(
    "caveat.textContent='핀당 17개 표본점의 RSSI 모델 예측이며, 원형 전체나 실측 품질 보장이 아닙니다.';",
    "caveat.textContent='각 핀의 정확한 한 좌표에 대한 미보정 RSSI 예측값입니다. 실제 측정 품질은 다를 수 있습니다.';")
source=source.replace(
    "textContent='필수영역 없음 · 기준은 반경 17개 표본점의 예상 품질 ≥70점입니다.'",
    "textContent='필수영역 없음 · 기준은 지정한 각 좌표의 예상 품질 ≥70점입니다.'")
source=source.replace(
    "· 반경 '+fmt(item.radiusM)+'m'",
    "") if False else source
replace_once(
    "item.type==='required'?'X '+fmt(item.x,2)+' · Z '+fmt(item.z,2)+' · 반경 '+fmt(item.radiusM)+'m'",
    "item.type==='required'?'X '+fmt(item.x,2)+' · Z '+fmt(item.z,2)+' · 정확한 점 1곳'",
    "element summary without radius")

replace_once(
    "if(tool==='required'&&hoverPoint&&!start&&!requiredDrag&&!hitRequiredPin(hoverPoint))drawRequiredPin(eCtx,{x:hoverPoint.x,z:hoverPoint.y,radiusM:Number($('requiredRadius').value)},sx,sy);",
    "if(tool==='required'&&hoverPoint&&!start&&!requiredDrag&&!hitRequiredPin(hoverPoint))drawRequiredPin(eCtx,{x:hoverPoint.x,z:hoverPoint.y},sx,sy);",
    "pointer hover no radius")
replace_once(
    "const x=clamp(point.x+drag.offsetX,pin.radiusM,L.width-pin.radiusM);",
    "const x=clamp(point.x+drag.offsetX,0,L.width);",
    "drag x bounds")
replace_once(
    "const z=clamp(point.y+drag.offsetZ,pin.radiusM,L.depth-pin.radiusM);",
    "const z=clamp(point.y+drag.offsetZ,0,L.depth);",
    "drag z bounds")
replace_once(
    "const x=+clamp(pin.x+d[0]*step,pin.radiusM,L.width-pin.radiusM).toFixed(3);",
    "const x=+clamp(pin.x+d[0]*step,0,L.width).toFixed(3);",
    "keyboard x bounds")
replace_once(
    "const z=+clamp(pin.z+d[1]*step,pin.radiusM,L.depth-pin.radiusM).toFixed(3);",
    "const z=+clamp(pin.z+d[1]*step,0,L.depth).toFixed(3);",
    "keyboard z bounds")
replace_section(
    "  const radius=Number($('requiredRadius').value);",
    "  changed('키보드로 필수영역 핀을 도면 중앙에 추가했습니다.');",
    """  const x=L.width/2,z=L.depth/2;
  pushUndo();const pin={id:uid('required'),x,z,minQualityScore:PIN_MIN_QUALITY};
  L.requiredPins.push(pin);selectedRequiredId=pin.id;
""", "keyboard pin creation")
replace_section(
    "   pointerId=null;const place=snapped(raw),radius=Number($('requiredRadius').value);",
    "   changed('필수영역 추가 · 핀 중심을 드래그해 이동하거나 목록에서 선택하세요.');",
    """   pointerId=null;const place=snapped(raw);
   if((L.requiredPins||[]).length>=PIN_MAX_COUNT){toast('필수영역은 최대 12개입니다.');return;}
   pushUndo();L.requiredPins=L.requiredPins||[];
   const pin={id:uid('required'),x:clamp(place.x,0,L.width),z:clamp(place.y,0,L.depth),minQualityScore:PIN_MIN_QUALITY};
   L.requiredPins.push(pin);selectedRequiredId=pin.id;
""", "pointer pin creation")
replace_section(
    "$('requiredRadius').oninput=e=>",
    "$('brushSize').oninput=e=>",
    "", "remove both radius sliders")
replace_once(
    "  const requiredPins=rawPins.map((pin,i)=>{const x=val(pin.x,w),z=val(pin.z,depth),radius=Number(pin.radiusM);\n   if(!Number.isFinite(radius)||radius<0.3||radius>3||x-radius<0||x+radius>w||z-radius<0||z+radius>depth)throw Error('필수영역 핀의 좌표 또는 반경이 유효하지 않습니다.');\n   return {id:String(pin.id||'required-'+i),x,z,radiusM:radius,minQualityScore:PIN_MIN_QUALITY};});",
    """  // Earlier layouts may have a radiusM field. Ignore it and retain only
  // the exact point coordinates so old drawings can be opened safely.
  const requiredPins=rawPins.map((pin,i)=>({id:String(pin.id||'required-'+i),
    x:val(pin.x,w),z:val(pin.z,depth),minQualityScore:PIN_MIN_QUALITY}));""",
    "legacy radius import ignored")

# Floor size editing must scale the point coordinate, NOT an old radius.
replace_once(
    "for(const pin of (L.requiredPins||[])){pin.x*=sx;pin.z*=sy;pin.radiusM*=Math.sqrt(sx*sy);}",
    "for(const pin of (L.requiredPins||[])){pin.x*=sx;pin.z*=sy;}",
    "resizing point-only pins")
source=source.replace(
    "필수영역 없음 · 기준은 반경 17개 표본점의 예상 품질 ≥70점입니다.",
    "필수영역 없음 · 각 지정 좌표의 예상 품질이 70점 이상이어야 합니다.")
# No radius controls or informational wording should be left in the shipped UI.
source=source.replace("핀마다 중심·안쪽·둘레의 17개 표본점", "핀마다 지정한 단 하나의 좌표")
source=source.replace("핀당 17개 표본점", "핀당 지정 좌표 1개")
# Ensure even historical explanatory strings do not claim a radius or 17 samples.
source=source.replace("17개 표본점", "정확한 한 좌표")


# ---------------------------------------------------------------------------
# Remove ceiling/wall-height input and ceilings from the *release* only.
# Keep independent, non-negative router/receiver Y settings for 3D distance.
# Walls are plan-view obstacles: an XZ ray crossing blocks irrespective of Y.
# ---------------------------------------------------------------------------
replace_once(
    '<input type="range" id="routerY" min="0" max="2.7" step="0.1" value="1.2">',
    '<input type="number" id="routerY" min="0" step="0.1" value="1.2" inputmode="decimal" aria-label="공유기 Y 위치, 천장 제한 없음">',
    "router Y uncapped numeric control")
replace_once(
    '<input id="receiverY" type="number" value="1.0" min="0" max="10" step="0.1">',
    '<input id="receiverY" type="number" value="1.0" min="0" step="0.1" inputmode="decimal">',
    "receiver Y uncapped numeric control")
replace_once(
    '<label>천장·벽 높이 (m)<input id="roomHeightM" type="number" value="2.7" min="1" max="10" step="0.1"></label>',
    "",
    "remove ceiling and wall height settings")
replace_once(
    '벽은 기본적으로 천장 높이까지 연장됩니다.',
    '벽은 별도 높이 제한 없이 XZ 평면에서 신호를 차단합니다. 공유기·수신기 Y는 각각 입력합니다.',
    "explain vertical modeling")

replace_once(
    '   L.roomHeightM??=2.7;L.receiverY??=1;',
    '   L.receiverY??=1;',
    "legacy engine layout no ceiling")
replace_once(
    """ function wallHit(L,x,z,wall,receiverY){
   const r=L.router,t=wallFraction(r.x,r.z,x,z,wall);
   if(t===null)return false;
   const atY=r.y+t*(receiverY-r.y);
   return atY>=0&&atY<=(wall.heightM??L.roomHeightM??2.7);
 }""",
    """ function wallHit(L,x,z,wall,receiverY){
   // Height-independent full-height plan-view concrete barrier.
   // A wall that crosses the XZ line always attenuates the model signal.
   return wallFraction(L.router.x,L.router.z,x,z,wall)!==null;
 }""",
    "remove wall height attenuation limit")
replace_once(
    'roomHeightM:2.7,receiverY:1.0,areaPyeong,',
    'receiverY:1.0,areaPyeong,',
    "remove room ceiling from new layout")
replace_once(
    "$('routerY').max=String(L.roomHeightM);$('routerY').value=String(L.router.y);",
    "$('routerY').value=String(L.router.y);",
    "sync unlimited router Y")
replace_once(
    "$('receiverY').value=String(L.receiverY);$('roomHeightM').value=String(L.roomHeightM);",
    "$('receiverY').value=String(L.receiverY);",
    "sync no ceiling input")
replace_section(
    "$('routerY').oninput=e=>",
    "$('frequencySelect').onchange=e=>",
    """$('routerY').onchange=e=>{
 const n=Number(e.target.value);
 if(e.target.value.trim()===''||!Number.isFinite(n)||n<0){
  toast('공유기 Y 높이는 0 이상의 유효한 숫자를 입력해 주세요.');syncLayout();return;
 }
 L.router.y=n;changed('공유기 Y 높이를 변경했습니다. 천장 높이 제한은 적용하지 않습니다.');
};
$('receiverY').onchange=e=>{
 const n=Number(e.target.value);
 if(e.target.value.trim()===''||!Number.isFinite(n)||n<0){
  toast('수신기 Y 높이는 0 이상의 유효한 숫자를 입력해 주세요.');syncLayout();return;
 }
 L.receiverY=n;changed('수신기 Y 높이를 변경했습니다. 천장 제한은 적용하지 않습니다.');
};
""",
    "replace vertical handlers without ceiling")
replace_once(
    '  const roomHeightM=clamp(cleanNum(converted.roomHeightM,2.7),1,10),receiverY=clamp(cleanNum(converted.receiverY,1),0,roomHeightM);',
    """  const nonnegativeY=(value,name)=>{const n=Number(value);
   if(!Number.isFinite(n)||n<0)throw Error(name+' Y 높이는 0 이상의 유효한 숫자여야 합니다.');
   return n;};
  // Older roomHeightM is deliberately ignored, not imported.
  const receiverY=nonnegativeY(converted.receiverY??1,'수신기');""",
    "import unlimited Y, ignore legacy ceiling")
replace_once(
    "material:'concrete',...(q.heightM==null?{}:{heightM:clamp(cleanNum(q.heightM,roomHeightM),.1,roomHeightM)})",
    "material:'concrete'",
    "discard legacy wall height, keep concrete")
replace_once(
    "width:w,depth,roomHeightM,receiverY,areaPyeong",
    "width:w,depth,receiverY,areaPyeong",
    "layout save without ceiling")
replace_once(
    "y:val(r.y,roomHeightM)",
    "y:nonnegativeY(r.y,'공유기')",
    "import unlimited router Y")

# Do not ship hidden state or legacy ceiling limits.
for obsolete in ("id=\"roomHeightM\"", "$('roomHeightM')", "L.roomHeightM",
                 "wall.heightM", "q.heightM", "roomHeightM,receiverY",
                 "max=\"2.7\" step=\"0.1\" value=\"1.2\"",
                 "max=\"10\" step=\"0.1\""):
    assert obsolete not in source, f"Retired height limit persists: {obsolete}"


# All references to radiusM left in the app must be unrelated brush/eraser settings.
assert 'id="requiredRadius"' not in source
assert 'id="selectedRequiredRadius"' not in source
assert "$('requiredRadius')" not in source
assert "$('selectedRequiredRadius')" not in source
assert "pin.radiusM" not in source
assert "17개 표본점" not in source
assert "반경 설정" not in source
assert "필수영역 핀의 좌표 또는 반경" not in source


# Build-time checks protect the full no-LAN interaction and original drawing tool set.
for marker in ('data-tool="required"','id="requiredPinSelect"','minQualityScore',
               'function requiredSamples','function optimize(layout','data-tool="brush"',
               'data-tool="sketch"','data-tool="erase"'):
    assert marker in source, marker
for marker in ('id="requiredRadius"','id="selectedRequiredRadius"',
               'id="g3LanX"','id="g3LanZ"','id="g3LanY"','id="g3Cable"',
               'id="g3Mode"','id="g3Settings"','async function g3LocalOptimize',
               "api('/candidate-locations'", "api('/optimize'",
               'data-tool="zone"','id="roomDrawer"'):
    assert marker not in source, marker
assert '<script>' in source and '</script>' in source

output=Path("release_preview/stage3.html")
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(source,encoding="utf-8")
dist=Path("dist")
dist.mkdir(parents=True,exist_ok=True)
name="WiFi_Placement_RequiredPoint_70_NoLAN.html"
(dist/name).write_text(source,encoding="utf-8")
print("NO_LAN_HTML_GENERATED",output.stat().st_size,dist.joinpath(name).stat().st_size)
