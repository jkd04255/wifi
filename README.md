# 와이파이 — 실측 보정형 Wi-Fi 배치 시뮬레이터

**4인 팀 프로젝트 · 4번 담당 개발: 최적 공유기 배치 알고리즘·백엔드**  
기준일: 2026-11-09

## 현재 단계

**GATE 2 — Python 최적 배치 알고리즘·백엔드 독립 구현 및 테스트 완료.** [PR #1](https://github.com/jkd04255/wifi/pull/1) `feat/optimizer-stage2` 브랜치에서 유지 중이며 **아직 main에 병합하지 않았습니다.** 최신 PR CI 21/21 성공: https://github.com/jkd04255/wifi/actions/runs/42629821844 . API 사용법은 [backend/README.md (개발 브랜치)](https://github.com/jkd04255/wifi/blob/feat/optimizer-stage2/backend/README.md)을 참조하세요.

**다음 단계 GATE 3:** 기존 UI와 API 최소 연동, 2번 예측/3번 보정 계약 확인, 전체 통합 QA 후 PR 병합. GitHub Pages는 Python API를 실행하지 않으며 현재 시연 사이트는 v1.6 그대로입니다.


**GATE 1 — 완료 (2026-11-09 사용자 시연 정상 확인)**

- [x] GitHub 저장소 `jkd04255/wifi` 생성
- [x] ChatGPT GitHub 앱 쓰기 접근 권한 확인
- [x] 기존 v1.6 HTML과 계획·인수인계 문서 업로드 및 원본/시연 SHA 일치 검증
- [x] GitHub Pages 활성화 및 Actions 배포 성공
- [x] 사용자 직접 시연 사이트 접속 및 정상 작동 확인 (사용자 보고, 별도 자동 브라우저 검증 아님)
- [x] 사용자 시연 정상 동작 확인 (세부 버튼별 자동 회귀 테스트는 미실시)

**주의:** 정적 GitHub Pages는 Python 백엔드 API를 직접 실행할 수 없습니다. 현 HTML은 기존 오프라인 모델이 있는 프론트엔드 시연본이며, 2번 RSSI 서버와 4번 최적화 API의 라이브 통합본으로 주장하지 않습니다.

## 파일 위치

- [브라우저 진입 파일](index.html) — v1.6을 수정하지 않은 정적 시연 복사본
- [원본 보관](legacy/WiFi_Placement_Studio_v1.6_offline.html) — **수정 금지**
- [3단계 작업 계획](docs/PLAN.md) — GATE 1/2/3 및 범위 통제
- [다음 대화 인수인계](docs/HANDOFF.md) — 기술/좌표/연동 계약 및 진행 방법
- [개발 규칙](AGENTS.md) — 팀 영역 변경 금지와 QA 지침

## GitHub Pages 설정 (필요한 경우 수동 1회)

저장소 **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: main → /(root) → Save**를 선택합니다. 배포되면 예상 주소는 https://jkd04255.github.io/wifi/ 입니다. **GitHub Actions 배포 성공 및 사용자 직접 웹 시연 정상 확인 (자동 브라우저 E2E는 별도 미실시).**

## 분담과 범위

| 번호 | 담당 |
|---|---|
| 1번 | 공간 구조 입력, 벽·문·공유기 도구, 프론트엔드 및 히트맵 UI |
| 2번 | Wi-Fi 전파 예측 및 2.4 / 5 GHz RSSI 모델 |
| 3번 | 스마트폰 RSSI 측정 및 실측값 보정 |
| **4번** | **후보 공유기 위치 탐색, 랜선 길이 제약, 중요도 기반 평가, 최적 위치 및 증설/AP 필요 판단, `/optimize` API** |

**작업 순서 고정:** GATE 1 (기존 파일 보존·시연) → GATE 2 (최적화 알고리즘/API 독립 구현 및 테스트) → GATE 3 (기존 UI 최소 연동 및 통합 검증). 이전 GATE 완료 전 다음 단계의 구현 금지.

## 기술 계약 (현재 잠정)

- 바닥 평면은 **x–z**, 공유기 높이는 **y**. 2D 히트맵 `values[row][col]`의 축과 명시적으로 매핑해야 함.
- 벽은 콘크리트, 중요도 `+100 / 0 / -100`. `-100`은 낮은 우선순위이며 신호를 약화시키라는 의미가 아님.
- 기존 2번 작업 기록: `POST http://localhost:8000/simulate`, 반환 `values[row][col]`. 정확한 JSON 계약은 담당 코드에서 재검증 전까지 동결하지 않음.
- 정적 UI의 '최적 위치 찾기' 버튼은 이미 존재하는 로컬 기능일 수 있으므로, 4번은 이를 보존하고 확장·분리해야 함.

## 다음 대화 이어가기

> GitHub `jkd04255/wifi`의 `README.md`, `AGENTS.md`, `docs/PLAN.md`, `docs/HANDOFF.md`를 읽고 4번 최적 배치 작업을 이어 주세요. 최신 main과 현재 GATE를 먼저 확인하고 원본 v1.6을 변경하지 마세요. 단계별 완료 조건을 통과하지 않은 변경은 다음 단계에 섞지 마세요.

---
이 저장소에 **실제 커밋된 파일과 확인된 배포만** 완료로 표시합니다.


## 최근 진행 현황 — GATE 2

- **GATE 1 완료**: 기존 v1.6 GitHub Pages 배포 성공, 사용자가 정상 시연 확인.
- **GATE 2 독립 최적화 백엔드 구현·검증 완료** (2026-11-09): `feat/optimizer-stage2` 브랜치, [PR #1](https://github.com/jkd04255/wifi/pull/1) **검토 대기 / main 미병합**.
- **자동 CI 성공**: Python 3.11 및 3.12 각각 21/21, 총 42/42 테스트 성공. [실제 기록](https://github.com/jkd04255/wifi/actions/runs/42629894652).
- 백엔드 코드: [backend/optimizer/core.py](https://github.com/jkd04255/wifi/blob/feat/optimizer-stage2/backend/optimizer/core.py), [backend/optimizer/api.py](https://github.com/jkd04255/wifi/blob/feat/optimizer-stage2/backend/optimizer/api.py).
- **GATE 3 대기**: 2번 RSSI 엔진과 3번 보정 결과 형식을 확인한 후 기존 1번 UI와 최소한으로 연동하고 회귀 테스트. 사용자 다음 단계 버튼 승인 시 진행.
- 현 [GitHub Pages 시연](https://jkd04255.github.io/wifi/)은 **기존 v1.6 정적 버전**이며 2단계 Python API 연동본이 아닙니다.

> 다음 대화에서는 먼저 PR #1과 그 브랜치의 `docs/GATE2_QA.md`, `docs/HANDOFF.md`를 읽으세요. GATE 2 백엔드를 다시 구현하지 말고, GATE 3 계약 확인과 최소 연동에 집중하세요. 원본 `legacy/` 파일은 수정 금지.
