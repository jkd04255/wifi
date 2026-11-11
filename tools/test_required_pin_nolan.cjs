// Point-only mandatory-pin contract in the exact fully offline HTML RSSI engine.
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const html=fs.readFileSync(process.argv[2],"utf8");
for(const key of ['data-tool="required"','id="requiredPinSelect"','function requiredSamples','minQualityScore'])assert(html.includes(key),key);
for(const key of ['id="requiredRadius"','id="selectedRequiredRadius"','data-tool="zone"','id="roomDrawer"',
                  'id="g3LanX"','id="g3LanZ"','id="g3LanY"','id="g3Cable"','id="g3Mode"',
                  '17개 표본점','반경 설정',"async function g3LocalOptimize"]){
  assert(!html.includes(key),"Retired UI/calculation still present: "+key);
}
const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map(m=>m[1]);
assert(scripts.length>=2);
for(const js of scripts)new vm.Script(js);
const window={};
vm.runInNewContext(scripts[0],{window});
const engine=window.WifiEngine;
assert.equal(typeof engine.optimize,"function");
const layout=()=>({
 schemaVersion:"1.1",coordinateSystem:{plane:"XZ",verticalAxis:"Y"},
 width:6,depth:4,roomHeightM:2.7,receiverY:1,
 router:{x:3,y:1.2,z:2,frequency:2.4,txPowerDbm:30,antennaGainDbi:0},
 walls:[],zones:[],importanceStrokes:[],
 requiredPins:[{id:"point-one",x:3,z:2,minQualityScore:70}],
});
const quality=dbm=>Math.max(0,Math.min(100,(dbm+90)/55*100));
const a=layout(),found=engine.optimize(a,.35,.75,true);
assert.equal(found.status,"ok",JSON.stringify(found));
assert.equal(found.requiredAreaSatisfied,true);
assert.equal(found.requiredAreaSampleCount,1,"One mandatory pin must mean exactly ONE point");
assert(found.best && Number.isFinite(found.best.x));
assert(found.best.x>=.2&&found.best.x<=a.width-.2);
assert(found.best.z>=.2&&found.best.z<=a.depth-.2);
const trial={...a,router:{...a.router,...found.best}};
const expected=quality(engine.value(trial,a.requiredPins[0].x,a.requiredPins[0].z));
assert(expected>=70-1e-8,"Point must pass 70, got "+expected);
assert(Math.abs(expected-found.requiredAreaMinimumQualityScore)<.02);
const obsoleteRadius=layout();obsoleteRadius.requiredPins[0].radiusM=2.3;
const withOld=engine.optimize(obsoleteRadius,.35,.75,true);
assert.equal(withOld.status,"ok");
assert.equal(withOld.requiredAreaSampleCount,1);
assert.deepEqual([withOld.best.x,withOld.best.z],[found.best.x,found.best.z],
 "Legacy radius must have absolutely NO influence on recommended location");
const phantomLan=layout();phantomLan.lanPort={x:-100,z:100,y:99,maxCableLengthM:0};
const ignoringLan=engine.optimize(phantomLan,.35,.75,true);
assert.equal(ignoringLan.status,"ok");
assert.deepEqual([ignoringLan.best.x,ignoringLan.best.z],[found.best.x,found.best.z]);
const bad=layout();bad.router.txPowerDbm=-100;
const fail=engine.optimize(bad,.35,.75,true);
assert.equal(fail.status,"no_feasible_candidate");
assert.equal(fail.best,null);
assert.equal(fail.requiredAreaSatisfied,false);
assert.equal(fail.requiredAreaSampleCount,1);
const two=layout();
two.requiredPins.push({id:"point-two",x:3.1,z:2.2,minQualityScore:70});
const goodTwo=engine.optimize(two,.35,.75,true);
assert.equal(goodTwo.status,"ok");
assert.equal(goodTwo.requiredAreaSampleCount,2,"Two mandatory pins must mean TWO points");
const concrete=layout();
concrete.walls=[{x1:3,z1:0,x2:3,z2:4,material:"concrete"}];
const w=engine.optimize(concrete,.35,.75,true);
if(w.status==="ok")assert(Math.abs(w.best.x-3)>=.2-1e-6,"No router on wall");
// Ceiling height, low partition height and >10m Y values must never limit model output.
assert(!html.includes('id="roomHeightM"'));
assert(!html.includes("L.roomHeightM"));
assert(!html.includes("wall.heightM"));
const tall=layout();
tall.router={...tall.router,x:1.5,z:2,y:12};
tall.receiverY=11;
tall.roomHeightM=0.4; // Historical ceiling metadata must not affect RSSI.
const rx=4.5,rz=2;
const noWall=engine.value({...tall,walls:[]},rx,rz);
const shallow={id:"short-partition",x1:3,z1:0,x2:3,z2:4,material:"concrete",heightM:0.01};
const crossed=engine.value({...tall,walls:[shallow]},rx,rz);
assert(Number.isFinite(noWall)&&Number.isFinite(crossed),"Unlimited Y must return finite prediction");
assert(crossed<noWall-1,"A concrete wall must attenuate even when stored heightM is tiny");
const tallCeiling=engine.value({...tall,roomHeightM:1000000,walls:[shallow]},rx,rz);
assert(Math.abs(tallCeiling-crossed)<1e-8,"Changing old ceiling height must have no effect");
const actualNoHeight=engine.value({...tall,walls:[{...shallow,heightM:undefined}]},rx,rz);
assert(Math.abs(actualNoHeight-crossed)<1e-8,"Low historical wall height must be ignored");

console.log("POINT_ONLY_70_EXACT_COORDINATES_PASS",{
 htmlBytes:Buffer.byteLength(html),
 singlePointCount:found.requiredAreaSampleCount,
 multiplePinCount:goodTwo.requiredAreaSampleCount,
 minimumQuality:+expected.toFixed(2),
 ignoresLegacyRadius:true, ignoresLan:true,
 infeasibleHardConstraint:true,concreteWallExcluded:true, unlimitedVerticalY:true, lowWallHeightIgnored:true,
});
