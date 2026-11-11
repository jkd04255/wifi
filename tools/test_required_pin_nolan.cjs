// No-LAN release behavior verification, using the exact embedded v1.6 RSSI engine.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const file = process.argv[2];
if (!file) throw new Error("HTML file path required");
const html=fs.readFileSync(file,"utf8");
for(const marker of ['data-tool="required"','id="requiredRadius"','requiredSamples','minQualityScore'])assert(html.includes(marker),marker);
for(const marker of ['id="g3LanX"','id="g3LanZ"','id="g3LanY"','id="g3Cable"','id="g3Mode"','data-tool="zone"','id="roomDrawer"',"async function g3LocalOptimize"]){
 assert(!html.includes(marker), "Unexpected deleted UI: "+marker);
}
const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map(m=>m[1]);
assert(scripts.length>=2,"Expected inline engine and main script");
for(const js of scripts)new vm.Script(js);
const window={};
vm.runInNewContext(scripts[0],{window});
const engine=window.WifiEngine;
assert(engine&&typeof engine.optimize==="function");
const standard=()=>({
 schemaVersion:"1.1",
 coordinateSystem:{plane:"XZ",verticalAxis:"Y"},
 width:6,depth:4,roomHeightM:2.7,receiverY:1,
 router:{x:3,y:1.2,z:2,frequency:2.4,txPowerDbm:30,antennaGainDbi:0},
 walls:[],zones:[],importanceStrokes:[],
 requiredPins:[{id:"needed",x:3,z:2,radiusM:0.8,minQualityScore:70}]
});
const samples=(pin)=>[{x:pin.x,z:pin.z},...[0.5,1].flatMap(scale=>Array.from({length:8},(_,i)=>{
 const a=2*Math.PI*i/8;return {x:pin.x+Math.cos(a)*pin.radiusM*scale,z:pin.z+Math.sin(a)*pin.radiusM*scale};
}))];
const calcQ=dbm=>Math.max(0,Math.min(100,(dbm+90)/55*100));
const good=standard();
const found=engine.optimize(good,0.35,0.75,true);
assert.equal(found.status,"ok",JSON.stringify(found));
assert.equal(found.requiredAreaSatisfied,true);
assert.equal(found.requiredAreaSampleCount,17);
assert(found.best && typeof found.best.x==="number");
const trial={...good,router:{...good.router,...found.best}};
const min=Math.min(...samples(good.requiredPins[0]).map(p=>calcQ(engine.value(trial,p.x,p.z))));
assert(min>=70-1e-8, "Recommended point violates mandatory pin: "+min);
assert(Math.abs(found.requiredAreaMinimumQualityScore-min)<.02);
const withoutLan={...good,lanPort:{x:-999,z:-999,y:999,maxCableLengthM:0}};
const r2=engine.optimize(withoutLan,.35,.75,true);
assert.equal(r2.status,"ok","No-LAN optimizer must not inspect LAN fields");
assert(Math.abs(found.best.x-r2.best.x)<1e-8);
assert(Math.abs(found.best.z-r2.best.z)<1e-8);
const impossible=standard();
impossible.router.txPowerDbm=-100;
const noResult=engine.optimize(impossible,.35,.75,true);
assert.equal(noResult.status,"no_feasible_candidate");
assert.equal(noResult.best,null);
assert.equal(noResult.requiredAreaSatisfied,false);
const two=standard();
two.requiredPins.push({id:"other",x:3.1,z:2.1,radiusM:.6,minQualityScore:70});
const passBoth=engine.optimize(two,.35,.75,true);
assert.equal(passBoth.status,"ok");
assert.equal(passBoth.requiredAreaSampleCount,34);
const withWall=standard();
withWall.walls=[{x1:3,z1:0,x2:3,z2:4,material:"concrete"}];
const wallResult=engine.optimize(withWall,.35,.75,true);
if(wallResult.status==="ok")assert(Math.abs(wallResult.best.x-3)>=.2-1e-6,
 "Router should not be placed on concrete wall");
console.log("NO_LAN_HTML_AND_HARD70_ENGINE_PASS",{
 scripts:scripts.length,htmlBytes:Buffer.byteLength(html),successMinimum:+min.toFixed(2),
 failedCandidatesAreRejected:!noResult.best,extraLanIgnored:true,wallCandidateBlocked:true
});
