"""4번 담당 모듈: 외부 RSSI 예측 결과를 이용한 공유기 위치 최적화.

이 모듈은 1~3번의 도면 편집/전파 모델/실측 보정을 구현하거나 변경하지 않는다.
평면 좌표는 X-Z(m), 높이는 Y(m). candidate.rssisDbm은 probes와 같은 순서.
"""
from __future__ import annotations

import heapq
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


EPS = 1e-8


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Position(StrictModel):
    x: float
    z: float
    y: float = Field(default=1.2, ge=0)


class Wall(StrictModel):
    x1: float
    z1: float
    x2: float
    z2: float


class Floor(StrictModel):
    widthM: float = Field(gt=0, le=40)
    depthM: float = Field(gt=0, le=40)
    heightM: float = Field(default=2.7, gt=0, le=10)
    walls: list[Wall] = Field(default_factory=list, max_length=400)
    # 선택 사항. 생략하면 widthM x depthM 직사각형으로 처리.
    footprint: list[tuple[float, float]] | None = Field(default=None, min_length=3, max_length=100)


class LanPort(Position):
    maxCableLengthM: float = Field(gt=0, le=200)


class Probe(StrictModel):
    x: float
    z: float
    priorityPct: Literal[-100, 0, 100] = 0
    targetDbm: float = Field(default=-67, ge=-110, le=-20)


class Prediction(StrictModel):
    position: Position
    rssisDbm: list[float] = Field(min_length=1, max_length=512)


class OptimizeRequest(StrictModel):
    floor: Floor
    lanPort: LanPort
    probes: list[Probe] = Field(min_length=1, max_length=512)
    candidates: list[Prediction] = Field(min_length=1, max_length=250)
    current: Prediction | None = None
    routeGridStepM: float = Field(default=0.25, ge=0.15, le=1)
    wallClearanceM: float = Field(default=0.15, ge=0, le=0.5)

    @model_validator(mode="after")
    def check_prediction_dimensions(self):
        size = len(self.probes)
        for p in self.candidates + ([self.current] if self.current else []):
            if len(p.rssisDbm) != size:
                raise ValueError("rssisDbm must have exactly one value per probe in order")
            if not all(-150 <= r <= 30 for r in p.rssisDbm):
                raise ValueError("RSSI must be in -150..30 dBm")
        if all(p.priorityPct == -100 for p in self.probes):
            raise ValueError("at least one probe must have nonzero evaluation priority")
        return self


def _segment_distance(x: float, z: float, w: Wall) -> float:
    dx, dz = w.x2 - w.x1, w.z2 - w.z1
    t = max(0.0, min(1.0, ((x-w.x1)*dx + (z-w.z1)*dz) / (dx*dx + dz*dz))) if dx*dx + dz*dz > EPS else 0
    return math.hypot(x-(w.x1+t*dx), z-(w.z1+t*dz))


def _cross(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def _segments_intersect(a, b, c, d) -> bool:
    p = _cross(a,b,c)
    q = _cross(a,b,d)
    r = _cross(c,d,a)
    s = _cross(c,d,b)
    if (p > EPS and q < -EPS or p < -EPS and q > EPS) and (r > EPS and s < -EPS or r < -EPS and s > EPS):
        return True
    # 끝점 접촉 및 한 직선 위의 겹침도 통과 불가로 판단
    for x, u, v in ((c,a,b),(d,a,b),(a,c,d),(b,c,d)):
        if abs(_cross(u,v,x)) < EPS and min(u[0],v[0])-EPS <= x[0] <= max(u[0],v[0])+EPS and min(u[1],v[1])-EPS <= x[1] <= max(u[1],v[1])+EPS:
            return True
    return False


def _within_floor(floor: Floor, x: float, z: float) -> bool:
    if not (0 <= x <= floor.widthM and 0 <= z <= floor.depthM):
        return False
    if floor.footprint is None:
        return True
    vs = floor.footprint
    assert vs is not None
    inside = False
    for i in range(len(vs)):
        (ax,az),(bx,bz) = vs[i],vs[(i+1)%len(vs)]
        if abs(_cross((ax,az),(bx,bz),(x,z))) < EPS and min(ax,bx)-EPS <= x <= max(ax,bx)+EPS and min(az,bz)-EPS <= z <= max(az,bz)+EPS:
            return True
        if (az > z) != (bz > z):
            x_intersection = ax + (bx-ax)*(z-az)/(bz-az)
            if x < x_intersection:
                inside = not inside
    return inside


def _valid_position(floor: Floor, pos: Position, clearance: float) -> bool:
    return (0 <= pos.y <= floor.heightM and _within_floor(floor, pos.x, pos.z)
            and all(_segment_distance(pos.x,pos.z,w) >= clearance-EPS for w in floor.walls))


def _clear_segment(floor: Floor, a: tuple[float,float], b: tuple[float,float]) -> bool:
    if not (_within_floor(floor,*a) and _within_floor(floor,*b)):
        return False
    # concave footprint에서 끝점이 내부라고 선분까지 내부인 것은 아님
    if floor.footprint and any(not _within_floor(floor,a[0]+(b[0]-a[0])*t/10,a[1]+(b[1]-a[1])*t/10) for t in range(1,10)):
        return False
    return not any(_segments_intersect(a,b,(w.x1,w.z1),(w.x2,w.z2)) for w in floor.walls)


def _compute_routes(request: OptimizeRequest) -> dict[tuple[int,int],float]:
    """LAN 포트에서 출발하여 벽을 관통하지 않는 8방향 격자 최소경로.
    포트~첫 격자 노드는 실제 비장애물 구간의 길이만큼 별도 가산.
    """
    f, p, h = request.floor, request.lanPort, request.routeGridStepM
    nx, nz = math.ceil(f.widthM/h), math.ceil(f.depthM/h)
    nodes = {}
    for iz in range(nz+1):
        z = min(f.depthM, iz*h)
        for ix in range(nx+1):
            x = min(f.widthM, ix*h)
            if _valid_position(f, Position(x=x,z=z,y=0), request.wallClearanceM):
                nodes[(ix,iz)] = (x,z)
    distances: dict[tuple[int,int],float] = {}
    heap = []
    start = (p.x,p.z)
    # 포트는 벽에 달려 있을 수 있으므로 포트 자체는 clearance 검사하지 않음.
    for key, q in nodes.items():
        step = math.dist(start,q)
        if step <= 1.6*h and _clear_segment(f,start,q):
            distances[key] = step
            heapq.heappush(heap,(step,key))
    while heap:
        dist, key = heapq.heappop(heap)
        if dist > distances[key] + EPS:
            continue
        ix,iz = key
        a = nodes[key]
        for dx,dz in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
            other=(ix+dx,iz+dz)
            if other not in nodes or not _clear_segment(f,a,nodes[other]):
                continue
            # 대각선이 벽 사이를 잘라 지나가는 경우는 반드시 선분 교차 검사
            length = math.dist(a,nodes[other])
            new = dist + length
            if new + EPS < distances.get(other,math.inf):
                distances[other] = new
                heapq.heappush(heap,(new,other))
    return distances


def _route_length(request: OptimizeRequest, pos: Position, distances: dict[tuple[int,int],float]) -> float | None:
    f,p,h=request.floor,request.lanPort,request.routeGridStepM
    if not _valid_position(f,pos,request.wallClearanceM):
        return None
    start=(p.x,p.z)
    end=(pos.x,pos.z)
    # 장애물 없는 직선이면 최단 거리 가능; 벽을 관통하는 유클리드 거리만으로 판정하지 않는다.
    best = math.dist(start,end) if _clear_segment(f,start,end) else math.inf
    nx,nz=math.ceil(f.widthM/h),math.ceil(f.depthM/h)
    ix0,iz0=round(pos.x/h),round(pos.z/h)
    for ix in range(max(0,ix0-2),min(nx,ix0+2)+1):
        for iz in range(max(0,iz0-2),min(nz,iz0+2)+1):
            if (ix,iz) not in distances:
                continue
            q=(min(f.widthM,ix*h),min(f.depthM,iz*h))
            dist = math.dist(end,q)
            if dist <= 1.6*h and _clear_segment(f,q,end):
                best = min(best,distances[(ix,iz)]+dist)
    if not math.isfinite(best):
        return None
    # 수직 포트/공유기 높이 차이는 별도 가산(낙관적 일직선 3D 거리 금지)
    return best + abs(pos.y-p.y)


def _quality(pred: Prediction, probes: list[Probe]) -> tuple[float,float,bool]:
    total=score=0.0
    weak=0.0
    critical_hits=critical_total=0
    for probe, dbm in zip(probes,pred.rssisDbm):
        w=2.0 if probe.priorityPct==100 else 1.0 if probe.priorityPct==0 else 0.0
        if w:
            score += w*max(0.0,min(100.0,(dbm+90.0)/55.0*100.0))
            weak += w*(dbm < -75)
            total += w
        if probe.priorityPct==100:
            critical_total += 1
            critical_hits += (dbm >= probe.targetDbm)
    objective=max(0.0, min(100.0, score/total-12.0*weak/total))
    coverage = 100.0*critical_hits/critical_total if critical_total else None
    # 중요 장소가 없으면 보통 중요 장소 목표 기준의 미달 여부를 본다.
    selected=[(p,v) for p,v in zip(probes,pred.rssisDbm) if p.priorityPct==100]
    if not selected:
        selected=[(p,v) for p,v in zip(probes,pred.rssisDbm) if p.priorityPct==0]
    need_ap=any(value<probe.targetDbm for probe,value in selected)
    return round(objective,2), (round(coverage,1) if coverage is not None else None), need_ap


def optimize(request: OptimizeRequest) -> dict:
    """이미 계산된 (각 후보별) RSSI 데이터를 비교. 2번 엔진 호출/전파 예측은 하지 않음."""
    f,p=request.floor,request.lanPort
    if not _within_floor(f,p.x,p.z) or p.y > f.heightM:
        raise ValueError("LAN port must be located inside the floor")
    for probe in request.probes:
        if not _within_floor(f,probe.x,probe.z):
            raise ValueError("probe must be inside the floor")
    distances=_compute_routes(request)
    valid=[]
    invalid=0
    for candidate in request.candidates:
        cable=_route_length(request,candidate.position,distances)
        if cable is None or cable > p.maxCableLengthM+EPS:
            invalid+=1
            continue
        sc, cov, ap=_quality(candidate,request.probes)
        valid.append((sc,cable,candidate,cov,ap))
    before=None
    current_cable=None
    if request.current:
        before,_,_=_quality(request.current,request.probes)
        current_cable=_route_length(request,request.current.position,distances)
    warnings=[]
    if invalid:
        warnings.append(f"{invalid} candidate(s) rejected (outside, on wall, unreachable, or cable too short)")
    if request.current is None:
        warnings.append("current position RSSI not provided; scoreBefore cannot be calculated")
    if not valid:
        return {"status":"no_feasible_candidate","recommendedPosition":None,
                "estimatedCableLengthM":None,"scoreBefore":before,"scoreAfter":None,
                "deltaScore":None,"criticalCoveragePct":None,"additionalApAdvised":None,
                "evaluatedCandidatesCount":len(request.candidates),"feasibleCandidatesCount":0,
                "reason":"No candidate satisfies the installation and cable constraints.",
                "feasibilityWarnings":warnings,"signalSource":"caller_supplied_predictions"}
    # 큰 점수 우선, 동점일 때 짧은 케이블 우선, 그 뒤 좌표순(결정론)
    valid.sort(key=lambda v:(-v[0],v[1],v[2].position.x,v[2].position.z))
    best_score,cable,best,cov,ap=valid[0]
    if request.current and current_cable is not None and current_cable <= p.maxCableLengthM+EPS and before is not None and before > best_score+EPS:
        best=request.current
        best_score,cov,ap=_quality(best,request.probes)
        cable=current_cable
        warnings.append("current placement outperforms evaluated candidates; recommending no move")
    return {"status":"ok","recommendedPosition":best.position.model_dump(),
            "estimatedCableLengthM":round(cable,2),"scoreBefore":before,
            "scoreAfter":best_score,"deltaScore":round(best_score-before,2) if before is not None else None,
            "criticalCoveragePct":cov,"additionalApAdvised":ap,
            "evaluatedCandidatesCount":len(request.candidates),"feasibleCandidatesCount":len(valid),
            "reason":"Highest predicted weighted coverage among feasible positions; additional AP evaluation is advisory.",
            "feasibilityWarnings":warnings,"signalSource":"caller_supplied_predictions"}
