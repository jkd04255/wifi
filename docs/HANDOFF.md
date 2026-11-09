# HANDOFF — 와이파이 프로젝트 4번 최적 배치 담당

업데이트: 2026-11-09 · 저장소: https://github.com/jkd04255/wifi

## 가장 먼저 할 일
1. README.md, AGENTS.md, docs/PLAN.md를 읽는다.
2. 실제 GitHub main의 파일/커밋과 Pages 상태를 확인한다.
3. legacy/WiFi_Placement_Studio_v1.6_offline.html을 읽고 현재 optimize() 함수와 UI 버튼의 실제 동작을 먼저 파악한다.
4. docs/PLAN.md에서 아직 통과하지 못한 GATE만 진행한다.
5. 수정은 기능 브랜치에서만 시작한다.

## 팀 분담 고정
- 1번: 집 구조 도면(선·사각형·부분 지우개), 공유기/벽 UI, 중요도 입력, 히트맵 화면
- 2번: RSSI 예측 엔진, 주파수 2.4 GHz/5 GHz, 벽·거리 손실
- 3번: 스마트폰 RSSI 측정, 측정 위치/공유기 위치 수집, 오차 보정
- **4번(현재): 후보 탐색·유효 영역 및 랜선 제약·중요도 기반 점수·최적 위치 비교·증설/AP 필요 권고·/optimize API**
1~3번 담당 기능을 재구현하거나 무단 변경하지 않는다.

## 기준 소스
- 정적 웹 진입점: index.html
- 수정 금지 원본: legacy/WiFi_Placement_Studio_v1.6_offline.html (기존 v1.6 오프라인 HTML)
- 기존 로컬 UI에 optimize 함수와 optimizeBtn 버튼이 들어 있으므로 기존 기준 동작과의 차이를 확인한 뒤 4번 역할을 분리한다.
- Windows EXE v1.6은 프로젝트 파일 목록에서 확인됐지만 이 GitHub 저장소의 업로드 대상은 우선 웹 HTML. EXE는 현재 업로드/검증하지 않았다.

## 연동·좌표
- 시뮬레이터 평면 x-z, 수직 높이 y. 과거 2번 API 결과는 values[row][col] (row=y, col=x라는 과거 2D 화면 축 명칭 사용). x-z와 2D 화면의 y는 별개이다. 명시적 변환 필요.
- 과거 예측 서버 기록: POST http://localhost:8000/simulate. 프론트 5173에서도 CORS 접근 허용했다고 보고됨. 팀 최신 소스로 정확한 계약을 재확인하기 전까지는 잠정이다.
- 측정 정보: 측정 지점 좌표(미터), RSSI dBm, 2.4/5GHz, 당시 공유기 위치.
- 중요도: 빨강 +100, 초록 0, 파랑 -100; -100은 품질 저하의 목표가 아니라 낮은 평가 우선순위이다.
- 벽 재질: 콘크리트로 고정. 평수→미터 스케일 정확히 유지.
- 최적화 API 제안: POST /optimize. 기존 /simulate API를 임의로 대체하지 않는다.

## GATE 관리
- GATE 1: GitHub 기준 소스 보존, 정적 시연 URL, 주요 화면 동작 검증. GitHub에 소스가 있어도 Pages가 실제 열리지 않으면 GATE 1 미통과.
- GATE 2: 알고리즘/API 작성, 후보 유효성·케이블·우선순위·AP 권고 자동 테스트 모두 통과.
- GATE 3: 기존 버튼과 UI에 최소한으로 연동, 전체 회귀·브라우저 검증·PR 병합.

## 4번 결과(계획안)
- 권장 위치 {x,z,y}, 필요한 케이블 길이(m), 현재/추천 점수, 핵심 공간 커버리지, 추가 AP 권고(bool), 사유, 불가능/검증불가 경고.
- 도면 밖/벽 위/케이블 제약 위반 시 무리하게 추천하지 않고 '가능한 후보 없음' 반환.
- 최적 위치가 좋더라도 주요 공간 기준 RSSI를 못 맞추면 추가 AP 필요 여부를 별도 제안.

## 공개 시연에 관한 유의
- GitHub Pages는 정적 HTML/CSS/JS만 배포 가능하며 Python 서버를 직접 실행하지 못한다.
- 웹 시연본의 로컬 계산과 실제 2번/3번 실측 연동은 분리해서 표기해야 한다.
- GitHub 주소가 존재한다는 사실만으로 Pages 배포 완료라고 할 수 없다.

## 다음 대화에 그대로 붙여넣을 요청
> GitHub jkd04255/wifi의 README.md, AGENTS.md, docs/HANDOFF.md, docs/PLAN.md와 최신 main 코드를 확인한 후 4번 최적 공유기 배치 알고리즘 개발을 이어 주세요. GATE 완료 여부를 먼저 검증하고, 기존 v1.6 원본을 보존하며 1~3번 팀원의 모듈을 임의로 재작성하지 마세요.

## GitHub Pages 배포 상태 (2026-11-09 KST)
- GitHub API `has_pages=true`: 사용자가 Pages 활성화 설정을 완료한 것으로 확인됨.
- Actions run: https://github.com/jkd04255/wifi/actions/runs/42626968444
- `build` 및 `deploy` 잡 모두 최종 완료: GitHub Actions run `completed / success` (2026-11-09 13:38:20 UTC).
- **Pages 배포 자체는 성공 확인. 실제 브라우저 렌더링 및 클릭 테스트는 미실시.**
- 예상 접속 URL: https://jkd04255.github.io/wifi/
- **2026-11-09 사용자 웹 시연 정상 동작 확인으로 GATE 1 완료 처리.** HTTP 응답 별도 계측 및 자동 브라우저 E2E는 미실시. 다음은 GATE 2 독립 Python 최적화 API 구현.

## GATE 2 최신 인수인계 (2026-11-09 KST)

- **GATE 1 완료**: 사용자가 https://jkd04255.github.io/wifi/ 시연 정상 작동 확인.
- **GATE 2 독립 백엔드 구현·테스트 완료 (main에는 아직 미병합)**.
- 개발 브랜치: [feat/optimizer-stage2](https://github.com/jkd04255/wifi/tree/feat/optimizer-stage2)
- PR: [#1 — GATE 2 independent optimizer](https://github.com/jkd04255/wifi/pull/1) (**open**, 통합 QA 전 병합 금지).
- GitHub CI: [run #42629821844](https://github.com/jkd04255/wifi/actions/runs/42629821844), **completed / success**, unittest 21/21 성공.
- 구현 API: `POST /candidate-locations` (물리적으로 가능한 좌표 탐색), `POST /optimize` (2번 예측 RSSI 입력→중요도/케이블 평가), `GET /health`. 실행은 [backend/README.md](https://github.com/jkd04255/wifi/blob/feat/optimizer-stage2/backend/README.md).
- 별도 QA 기록: [docs/GATE2_QA.md](https://github.com/jkd04255/wifi/blob/feat/optimizer-stage2/docs/GATE2_QA.md).
- **다음 진행 GATE 3:** 우선 PR #1 및 최신 CI 확인. 2번 /simulate 최신 JSON 계약과 3번 실측 보정 데이터 연동 방식 검증. 기존 v1.6의 `optimize()` 및 버튼은 보존하고 UI 최소 연동에 한정. Python API는 GitHub Pages에서 직접 실행할 수 없음. 계약이 불명확하면 모의연동과 실연동을 구분하고 사용자에게 요청.
- 기존 원본 `legacy/WiFi_Placement_Studio_v1.6_offline.html` 파일 직접 수정 금지.
- 다음 단계 버튼 메시지: "jkd04255/wifi PR #1의 GATE 2 자동 테스트 상태를 재확인하고, docs/PLAN.md의 GATE 3을 진행해 주세요. 원본 v1.6과 1~3번 팀원 모듈을 보존하고 2/3번 최신 API 계약을 검증한 뒤 최소 UI 연동·통합 QA·PR 병합을 진행하세요. 실제 연동 미검증은 명시하세요."

## GATE 2 재검증 및 충돌 해결 (2026-11-09)
- [Python 3.11·3.12 CI](https://github.com/jkd04255/wifi/actions/runs/42629894652): 각 21/21, 총 42/42 통과.
- 검토용 [PR #1](https://github.com/jkd04255/wifi/pull/1)은 open이며, 통합 전 main에 코드를 병합하지 않음.
- 새 CI는 `.github/workflows/optimizer-ci.yml` 한 개로 유지.
- GATE 3는 실제 2번 RSSI 예측 데이터 계약을 검증해야 시작할 수 있음. 기존 웹 v1.6과 3번 실측 모듈을 임의로 고치지 않음.


## GATE 3 진행 기록 (2026-11-09 · 로컬 시연 브랜치)

- 브랜치: `feat/optimizer-stage3-integration`, Draft PR #2 (base=`feat/optimizer-stage2`): https://github.com/jkd04255/wifi/pull/2
- **기존 index.html·legacy 원본은 수정하지 않음.** 별도 `preview/stage3.html`만 추가.
- `backend/dev_server.py`: `127.0.0.1:8001` 동일 출처로 API+시연 HTML 실행. 실행법 `docs/GATE3_INTEGRATION.md`.
- 기존 UI '최고의 위치 찾기'를 4번 `/candidate-locations` + `/optimize`와 연결하는 선택 모드 구현. 기본 모드는 원래 v1.6.
- API 모드는 **v1.6 JavaScript 모델 예측값 (실측 미보정)**으로만 시연. 2번/3번 엔진이 실제 연동된 것은 아님.
- 랜 포트 X/Z/Y, 케이블 길이 직접 입력. 직사각형 외곽 가정 등의 한계 경고 표시.
- API 연결 실패 시 묵시적 JS fallback 금지.
- 기존 백엔드 테스트 및 Chromium/WebKit E2E: `.github/workflows/stage3-ci.yml` 확인 필요.
- **계약 미확정 HOLD**: 2번 /simulate 정확한 JSON, 3번 보정 출력, 1번 도면 외곽 footprint 미확정. 따라서 PR #2 Draft·main 병합 금지, GitHub Pages 변경 없음.
- 다음 대화는 PR #2와 `docs/GATE3_INTEGRATION.md`를 먼저 읽고 CI 결과 확인. 팀원의 실제 계약이 확인될 때 정식 연결을 시도.

## GATE 3 로컬 CI 확정 결과 (2026-11-09)

- [GATE3 QA 보고서](docs/GATE3_QA.md): [GitHub Actions #42633059037](https://github.com/jkd04255/wifi/actions/runs/42633059037) `completed/success`; Python 21/21 + Chromium/WebKit 브라우저 4/4 = 총 25개 테스트 통과.
- 실패했던 초기 HTML 삽입 오류는 본래 v1.6을 기준으로 재생성하여 해결. 인라인 JS 스크립트 4개 모두 구문 검사 통과.
- 로컬 데모는 `python -m uvicorn dev_server:app --host 127.0.0.1 --port 8001` (backend 디렉터리에서) → `http://127.0.0.1:8001/preview/stage3.html`.
- **GATE3 정식 통합 HOLD**, PR #2 Draft 및 2번/3번 계약 미확정 상태. 1번 실내 footprint도 공식 계약 필요. main/기존 Pages는 그대로 유지.


## 최신 GATE 3 추가 회귀 결과 및 다음 대화 지시 (2026-11-09)

- 개발 브랜치 `feat/optimizer-stage3-integration` / [Draft PR #2](https://github.com/jkd04255/wifi/pull/2).
- 최신 검증: [Actions #42634218483](https://github.com/jkd04255/wifi/actions/runs/42634218483) Python 21/21, Playwright Chromium·WebKit 9/9, 합계 **30/30 성공**.
- WebKit 신규 로컬 API, 2.4/5GHz, +100/0/-100 브러시, 콘크리트 벽과 케이블 제한, API 장애 시 묵시적 폴백 방지 모두 테스트.
- 검증 로그와 한계는 `docs/GATE3_QA.md`, 실행 방법은 `docs/GATE3_INTEGRATION.md`.
- 팀원 API 확정 계약은 여전히 없음. `docs/TEAM_CONTRACT_TEMPLATE.md`는 제안/요청 양식이므로 실제 2·3번 연동된 것으로 보고하지 말 것.
- `main/index.html` 및 `legacy/WiFi_Placement_Studio_v1.6_offline.html` 변경 금지, PR #1·#2는 보류. 정식 GATE 3 **HOLD**, GitHub Pages 재배포 금지.
- **다음 액션:** 1·2·3번 팀원에게 계약 템플릿을 전달하고 소스·JSON 샘플·외곽선 좌표를 받은 뒤 검증·어댑터/통합 테스트. 미제공 시 HOLD 유지.
