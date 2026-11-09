# 4번 — 공유기 최적 배치 API (GATE 2)

1번 도면 UI, 2번 RSSI 예측 엔진, 3번 실측 보정 모듈과 **분리된** Python 백엔드입니다. 기존 GitHub Pages HTML은 이 단계에서 변경하지 않습니다.

## 실행

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn optimizer.api:app --host 127.0.0.1 --port 8001
# 로컬 API 문서: http://127.0.0.1:8001/docs
```

```bash
cd backend
python -m unittest discover -s tests -v
```

## 계약 — POST /optimize

요청은 다음 네 가지를 반드시 포함합니다.

- `floor`: `widthM`, `depthM`, `heightM`(선택), `walls`(`x1,z1,x2,z2`), 비직사각형인 경우 `footprint` 다각형
- `lanPort`: `x,z,y,maxCableLengthM`
- `probes`: 신호 품질을 평가할 샘플 위치 `x,z,priorityPct,targetDbm` 배열
- `candidates`: **2번 엔진이 각 공유기 후보 위치에서 예측한 RSSI**(`position:{x,y,z},rssisDbm:[...]`) 배열. 배열은 `probes`와 같은 순서.
- `current`는 선택 사항. 제공되면 기존 위치의 `rssisDbm`을 이용해 전후 점수 비교. 미제공 시 `scoreBefore`, `deltaScore`는 `null`.
- 좌표는 **바닥 X-Z 미터, 수직 Y 미터**. 기존 그리드 `values[row][col]`에서 행은 z, 열은 x이며 셀 중심은 `x=origin.x+(col+0.5)*gridStep`, `z=origin.z+(row+0.5)*gridStep`로 변환한 뒤 probes에 넣습니다. 예전 코드의 2D y축과 수직 Y를 혼동하면 안 됩니다.

### 최소 JSON 예시

```json
{
  "floor": {"widthM": 4, "depthM": 3, "walls": []},
  "lanPort": {"x": 0.5, "z": 0.5, "y": 0.3, "maxCableLengthM": 10},
  "probes": [{"x": 1, "z": 1, "priorityPct": 100, "targetDbm": -67}],
  "candidates": [
    {"position": {"x": 1, "z": 1, "y": 1.2}, "rssisDbm": [-55]},
    {"position": {"x": 3, "z": 2, "y": 1.2}, "rssisDbm": [-80]}
  ],
  "current": {"position": {"x": 2, "z": 1, "y": 1.2}, "rssisDbm": [-65]}
}
```

응답: `status`(`ok` / `no_feasible_candidate`), `recommendedPosition`, `estimatedCableLengthM`, `scoreBefore`, `scoreAfter`, `deltaScore`, `criticalCoveragePct`, `additionalApAdvised`, `evaluatedCandidatesCount`, `feasibleCandidatesCount`, `reason`, `feasibilityWarnings`, `signalSource`.

## 알고리즘 한계 및 안전 장치

1. **RSSI 예측값은 절대 자체 생성하지 않습니다.** 2번 엔진의 후보별 데이터 제공/변환 어댑터는 해당 팀원의 최종 API 계약이 확보되는 GATE 3에 연결할 예정입니다. 현재 `signalSource=caller_supplied_predictions`.
2. `+100` 중요도는 2배, `0`은 1배, `-100`은 0배로 평가합니다. `-100` 위치에서 신호를 낮추는 목표는 없습니다.
3. 직사각형 또는 단순 다각형 `footprint` 내부만 허용하며 벽 위/외부/높이 초과 후보는 제외합니다. 벽은 콘크리트의 **물리적 통과 불가 경계**로 가정합니다.
4. 케이블 경로는 격자 탐색 및 시야 내 직선 연결로 **수평 최소 추정 길이 + 수직 높이 차**를 계산합니다. 벽 통과 거리는 사용하지 않지만 실제 전선 몰딩·시공 경로를 반영한 보장값은 아닙니다. 계단/문/케이블 관통로/장애물 높이 등은 모델링하지 않습니다.
5. 모든 유효 후보가 목표 RSSI에 미달하면 `additionalApAdvised=true`를 반환합니다. 이는 **검토 권고**이지 AP 설치의 확정 진단이 아닙니다.
6. API는 후보 RSSI 배열 길이/위치/단위/필드 범위를 검증하며 유효 후보가 없으면 명시적으로 `no_feasible_candidate` 반환합니다. 1~3번 팀원의 로직을 덮어쓰지 않습니다.
7. 배포: 정적 GitHub Pages에서 Python API는 실행되지 않습니다. 현재 로컬 8001 포트 테스트 전용이며, GATE 3에서 통합 여부를 결정합니다.

## 다른 대화에서 계속

`jkd04255/wifi`의 docs/HANDOFF.md, docs/PLAN.md를 확인하고 **feat/optimizer-stage2** 브랜치의 이 모듈 및 테스트를 먼저 읽습니다. 자동 테스트 결과/PR 확인 후 GATE 3에 진입하고, 실제 API 연동 전에 2번 엔진의 현재 JSON 계약을 확보합니다.
