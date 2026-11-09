# GATE 3 — 미확정 계약을 위한 합성 전용 어댑터

상태: **UNVERIFIED SYNTHETIC ONLY** · 2026-11-09

> 이 파일과 코드는 실제 2번 RSSI 예측 엔진이나 3번 실측 보정 함수의 인터페이스가 아닙니다. 팀원 계약 합의 전 임시 자료를 실제 측정값 또는 공식 API로 사용하지 마세요.

## 저장 위치

- 코드: `backend/optimizer/synthetic_adapter.py`
- 합성 예시: `backend/fixtures/synthetic_grid_handoff.json`
- 검증 테스트: `backend/tests/test_synthetic_adapter.py`
- 팀원 실제 계약 요청 서식: `docs/TEAM_CONTRACT_TEMPLATE.md`
- 기존 최적화 API: `backend/optimizer/api.py` (수정하지 않음)

## 설계 요약

어댑터는 입력받은 **합성** RSSI 행렬의 샘플을 엄격하게 읽어 4번 `Prediction` 데이터 형식 `{position:{x,z,y},rssisDbm:[...]}`로 옮깁니다. RSSI 계산/실측/보정 자체는 **수행하지 않습니다**.

| 필드 | 반드시 지정하는 의미 |
|---|---|
| `schemaVersion` | `synthetic-grid-v1` |
| `contractStatus` | `UNVERIFIED_SYNTHETIC` |
| `isSynthetic` | 반드시 `true` |
| `coordinateSystem` | `XZ`: 도면 바닥 좌표 |
| `verticalAxis` | `Y`: 수직 높이 |
| `rowAxis` / `columnAxis` | `Z` / `X`: `values[row][col]` 방향 |
| `cellAnchor` | `center`: 격자 셀 중심 |
| `originXZ` | `{x,z}`: 그리드의 좌상단 바닥 위치(m) |
| `gridStepM` | 정방격자 셀 크기(m) |
| `receiverY` | RSSI 예측 수신기 높이(m) |
| `frequencyGHz` | 2.4 또는 5 (추정하지 않음) |
| `routerPosition` | 각 공유기 후보 `{x,z,y}` |
| `values` | 행=Z, 열=X, 단위 dBm (-150~30), 직사각형 배열 |

셀 중심 매핑은 `x = originXZ.x + (col+0.5)*gridStepM`, `z = originXZ.z + (row+0.5)*gridStepM`입니다. `receiverY`는 **2D 행 번호가 아닙니다**.

현재는 **정확한 셀 중심만** 샘플링합니다. 위치가 셀 중앙에 일치하지 않으면 조용히 보간하지 않고 오류를 반환합니다. 2번이 공식 보간/좌표 계약을 정하기 전 임의로 추측하지 않습니다. 배열의 행 수, 동일 열 수, RSSI 범위, NaN/Inf, 빈 데이터, 바깥 좌표, 대역과 높이 불일치를 모두 검사합니다.

## 보정 자료가 없는 경우 / 잘못된 경우

선택적 `syntheticCalibration`은 실측 보정 함수가 아니라, **합성된 결과 배열을 안전하게 검증하고 전달하는 테스트용 필드**입니다.

- 보정 자료 미제공 또는 `status=missing`: 원래 RSSI 그대로 전달; `calibrationStatus=missing`, `signalSource=synthetic_grid_unadjusted`. 보정된 것으로 절대 표시하지 않습니다.
- `status=provided`: 같은 공유기 위치·동일 대역·동일 격자 셀 순서가 명시된 **합성 보정 결과 배열**만 그대로 전달; `calibrationStatus=provided_synthetic`. 자체 보정 알고리즘은 수행하지 않습니다.
- `status=failed`: 명시적으로 **오류**를 발생시킵니다. 기존 예상치로 묵시적 폴백하거나 잘못된 결과를 반환하지 않습니다.
- corrected RSSI 벡터 크기·순서·값이 다르면 거부하며, 인증되지 않은 실제 계약이라고 주장하는 데이터를 받을 수 없습니다.

## 합성 예제 사용

```python
import json
from pathlib import Path
from optimizer.synthetic_adapter import adapt_synthetic_grid

fixture = json.loads(Path("fixtures/synthetic_grid_handoff.json").read_text())
result = adapt_synthetic_grid(fixture["grid"], fixture["probes"])
assert result["prediction"]["rssisDbm"] == [-60, -55, -75]
assert result["calibrationStatus"] == "missing"
assert result["isSynthetic"] is True

corrected = adapt_synthetic_grid(
    fixture["grid"], fixture["probes"], fixture["providedSyntheticCalibration"]
)
assert corrected["prediction"]["rssisDbm"] == [-61, -56, -76]
assert corrected["signalSource"] == "synthetic_corrected_fixture"
```

실행:

```bash
cd backend
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

## GATE 3 HOLD 해제에 필요한 조건

1. 1번 확정 실내 `footprint` 및 LAN 포트/케이블 경로 JSON 확보.
2. 2번 실제 `/simulate` 소스 및 요청/응답 실샘플·대역·좌표 규칙 확인.
3. 3번 실측 보정 알고리즘 및 결과 스키마, 비보정/오류 처리 확인.
4. 승인된 실계약에 한해서 **새 명시적 production 어댑터**를 별도 개발·검증.
5. 기존 v1.6 원본 유지, Python/브라우저 회귀 및 실제 예측/실측 통합 시험 통과.

**정식 팀 계약 부재 시: PR #2 Draft·GATE 3 HOLD·main 병합 금지·GitHub Pages 변경 금지.**


## 별도 합성 계약 전체 요청 어댑터와의 차이

현재 저장소에는 `backend/optimizer/synthetic_contract.py`도 있습니다. 이 모듈은 **전체 합성 RSSI 격자와 중요도 배열을 함께 검증하고** 4번 `/optimize` 요청 전체를 구성하며, 보정이 적용됐다는 주장을 승인하지 않습니다. 검증 fixture는 `backend/fixtures/synthetic_gate3_case.json`입니다.

반면 본 문서의 `synthetic_adapter.py`는 특정 수신 지점이 정확히 격자 셀 중심에 있는지 확인하고, 합성 보정 결과가 제공되었을 때 그 **이미 계산된** 값을 순서 검증 후 전달하기만 합니다. 서로 다른 테스트 목적의 **두 임시 모듈**이며 둘 다 실제 팀원 2·3번 API 연동이 아닙니다. 임의로 계약을 혼용하지 마세요.

증거: [Python 86개 + Chromium/WebKit 9개 = 총 95개 성공](https://github.com/jkd04255/wifi/actions/runs/42635704295).
