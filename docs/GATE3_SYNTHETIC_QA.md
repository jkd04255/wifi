# GATE 3 — 합성 계약 어댑터 검증 결과

**2026-11-09 / 기능 브랜치 전용 / 정식 GATE 3 HOLD**

## 실제 실행된 QA

[GitHub Actions 실행 #42635704295](https://github.com/jkd04255/wifi/actions/runs/42635704295) — `completed/success`.

| 검증 | 통과 |
|---|---:|
| 기존 최적화 엔진 및 독립 합성 계약 Python unittest | **86/86** |
| Chromium·WebKit 로컬 시연 브라우저 테스트 | **9/9** |
| 합계 | **95/95** |

GitHub Actions 로그에서 `Ran 86 tests / OK` 및 `Ran 9 tests / OK` 확인. 이 검증은 실제 2번/3번 시스템의 데이터 통합 테스트가 아닙니다.

## GitHub에 추가된 독립 파일

- `backend/optimizer/synthetic_adapter.py` — 명시적인 가상 그리드 단일 프레임의 X-Z 좌표를 `probes` 순서로 뽑아 `Prediction` 형식에 적합하도록 검사. `isSynthetic:true`, `UNVERIFIED_SYNTHETIC`, `rowAxis:Z`, `columnAxis:X`, `verticalAxis:Y`, 수신점 `Y`와 셀 중심 좌표가 필수. **가상 보정 예시만** 처리하며 상태 missing/failed/provided 테스트가 포함됨. 미확인 보정 API에 연결한 것이 아님.
- `backend/optimizer/synthetic_contract.py` — 테스트용 여러 후보 그리드를 합쳐 `/optimize` 요청을 생성. 합성 신호만 허용하고 보정 결과가 실제 적용됐다는 주장은 **fail-closed 거부**. 중요도 그리드 `[-100,0,100]`과 응답 출처를 명시.
- `backend/fixtures/synthetic_grid_handoff.json` — 첫 번째 어댑터 전용 합성 그리드 및 보정 유무/실패 예시. 실측 자료 **아님**.
- `backend/fixtures/synthetic_gate3_case.json` — 두 번째 어댑터 전용 합성 후보 RSSI/우선순위 예시. 실측 자료 **아님**.
- `backend/tests/test_synthetic_adapter.py` — 단일 격자와 좌표·보정 예외 검증.
- `backend/tests/test_synthetic_contract.py` — 후보 배열, 행·열 일치, RSSI 범위/주파수, 보정 누락, 실외 후보 및 /optimize API 요청 경계 검증.

두 모듈은 **실제 팀원에게 받은 별도의 확정 스키마가 아니라** 서로 보완하는 임시 합성 계약 검증 도구입니다. 실제 2번 `/simulate` 응답을 임의로 이 형식에 맞추지 않습니다.

## 실연동 차단 조건

1. **1번** `LayoutData` 최종 `footprint` 다각형, 문/케이블 경로 및 LAN 포트와 중요도 샘플 정의가 아직 미확정.
2. **2번** `POST /simulate` 실제 요청/응답 JSON, 격자 좌표 기준, 주파수, RSSI 모델 버전, 후보별 계산 방식이 아직 미확정.
3. **3번** 실측 샘플/보정 출력 스키마, 적용 범위와 오류·결측 처리 규칙이 아직 미확정.
4. 실제 iPhone Safari 실기기, 실제 측정값과 예측값의 차이, 외부 Python 서버 배포/운영은 미검증.

확정 계약 요청 및 필수 샘플: [TEAM_CONTRACT_TEMPLATE.md](TEAM_CONTRACT_TEMPLATE.md).

## 외부 접근 / 협업

- GitHub 저장소 https://github.com/jkd04255/wifi 의 공식 API `private=false`, `visibility=public` 확인. **누구나 읽기/복제 가능**.
- 다른 GitHub 계정이 원격 브랜치에 **직접 쓰기**하려면 소유자가 해당 사용자를 협업자로 별도 초대해야 합니다. 계정명이나 동의가 없으므로 초대를 생성하지 않았음.
- 권장 절차: GitHub의 `Settings → Collaborators and teams`에서 팀원 ID별 초대 → 개인 브랜치/PR → 코드 리뷰. 중요한 데이터·토큰은 공개 저장소에 올리지 않기.

## Gate 판정

**단위 계약·모의 통합 품질 검증 완료 / 정식 GATE 3 HOLD.**
`main/index.html`, `legacy/WiFi_Placement_Studio_v1.6_offline.html` 수정 금지, PR #2 Draft, main 병합 및 Pages 배포 금지.
