# GATE 2 — 독립 최적화 알고리즘·API 검증 보고

검증일: 2026-11-09 (KST)

## 구현 상태

- 개발 브랜치: `feat/optimizer-stage2`.
- 별도 Python 4번 모듈: `backend/optimizer/core.py`, `backend/optimizer/api.py`.
- `POST /candidate-locations`: 도면 내부 후보 + 벽 간섭/유효 높이 + 케이블 경로 제약을 통과하는 좌표 생성.
- `POST /optimize`: 2번 엔진이 **이미 계산한** 후보별 RSSI 값을 우선순위에 따라 평가해 위치 추천.
- 평가 우선순위: +100 → 2.0배, 0 → 1.0배, -100 → 0배. -100 위치의 RSSI를 낮추는 목표가 아님.
- 높은 중요도 목표 미달 시 `additionalApAdvised`를 통해 AP 증설 **검토** 권고.
- 현재 공유기 RSSI가 제공되면 개선 전후 점수 비교, 더 좋은 현재 위치는 그대로 유지.
- 별도 `/health` 및 FastAPI OpenAPI `/docs`.

## 자동 테스트 결과

- Python 3.12 · GitHub Actions: [Optimizer Stage 2 Tests run #42629424721](https://github.com/jkd04255/wifi/actions/runs/42629424721)
- Python 코드 compileall: **성공**.
- 21개 `unittest` 테스트: **21/21 성공**, 실패 0.
- 검증 내용: 실내/실외/벽 위 후보 제한, L자 footprint, 벽 우회 케이블 길이, 랜선 길이 부족, 유효 후보 없음, +100/0/-100 중요도, 현재보다 불리한 위치 강제 추천 금지, AP 권고, 결과 결정론, API 정상/잘못된 입력 처리.
- 초기 CI에는 테스트 시나리오 오류로 2개 실패가 있었고, 조건 정정 후 최신 21개 테스트가 모두 성공함.
- **정적 웹 HTML 원본과 메인 UI에는 코드 변경 없음.**

## GATE 2 완료 판정

**독립 API 및 자동 테스트 기준은 통과.** `feat/optimizer-stage2`에 코드가 커밋되어 있으며, 검토용 PR을 통해 main 반영을 진행할 수 있음.

### 다음 GATE 3에 남긴 범위 (이번 단계에서 구현하지 않음)

1. 2번 RSSI 엔진의 최신 `/simulate` JSON 계약과 3번 실측 보정 출력 계약 확인. 현재 저장소에는 확정 인터페이스가 없음.
2. 1번 기존 HTML 화면과 API 최소 연동. `index.html` 및 `legacy/*`는 지금까지 변경하지 않았음.
3. UI E2E 테스트, Python 백엔드 실행 환경, 통합 PR 검토 및 main 병합, GitHub Pages 재배포 확인.

### 정확도/물리 제약 한계

- 예상 RSSI를 자체 생성하지 않으며 검증되지 않은 입력을 실측이라고 부르지 않음.
- 벽/다각형/케이블 경로는 기하학적 단순화. 문, 몰딩, 배관, 고정 랜포트 쪽 접근면, 시공법 및 AP 사양을 보장하지 않음.
- 실내 직선 구간은 케이블을 직선으로 놓을 수 있다고 가정하고, 장애물이 있으면 격자 경로로 우회함. `estimatedCableLengthM`는 설치 견적이 아니라 최소 추정 길이.
- GitHub Pages는 Python 백엔드를 실행하지 않음. 별도 Python 서비스와 브라우저 연동 전까지 기존 정적 시연은 이전 v1.6 그대로 동작함.

## 다음 단계 진행 조건

사용자가 GATE 3 진행을 누르면 먼저 최신 PR 및 CI 결과를 검토하고, 2번/3번 최신 계약을 확인한 뒤 기존 UI를 최소 변경하여 연결할 것. 계약이 확보되지 않으면 임의로 실제 연동 성공을 주장하지 말고 Mock/계약 미확인 상태로 분리하여 보고할 것.
