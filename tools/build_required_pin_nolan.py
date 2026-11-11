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
   for(const pin of pins){
     mandatory.push({x:pin.x,z:pin.z,minimum:70});
     for(const scale of [0.5,1])for(let i=0;i<8;i++){
       const a=2*Math.PI*i/8;
       mandatory.push({x:pin.x+Math.cos(a)*pin.radiusM*scale,
                       z:pin.z+Math.sin(a)*pin.radiusM*scale,minimum:70});
     }
   }
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

# Build-time checks protect the full no-LAN interaction and original drawing tool set.
for marker in ('data-tool="required"','id="requiredRadius"','minQualityScore',
               'function requiredSamples','function optimize(layout','data-tool="brush"',
               'data-tool="sketch"','data-tool="erase"'):
    assert marker in source, marker
for marker in ('id="g3LanX"','id="g3LanZ"','id="g3LanY"','id="g3Cable"',
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
name="WiFi_Placement_RequiredPin_70_NoLAN.html"
(dist/name).write_text(source,encoding="utf-8")
print("NO_LAN_HTML_GENERATED",output.stat().st_size,dist.joinpath(name).stat().st_size)
