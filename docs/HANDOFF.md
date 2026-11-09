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

## GATE 2 확정 개발 상태 (2026-11-09)

- `feat/optimizer-stage2` 기능 브랜치에서 **독립 최적화 엔진 완료**.
- 코어: `backend/optimizer/core.py`. API: `backend/optimizer/api.py`.
- 엔드포인트: `GET /health`, `POST /candidate-locations`, `POST /optimize`.
- 후보 위치는 평면 X-Z/높이 Y, footprint/벽/케이블 길이 제약으로 거르며, 2번 엔진이 제공한 RSSI 배열만 평가함.
- 중요도는 +100=2배, 0=1배, -100=0배(신호를 약화시키지는 않음), 목표 미달 시 추가 AP **검토 권고**.
- 실행/계약/한계: `backend/README.md`. 테스트 증거: `docs/GATE2_QA.md`.
- **최종 CI 검증**: https://github.com/jkd04255/wifi/actions/runs/42629894652 — Python 3.11·3.12 각 21/21 성공(총 42).
- **PR #1**: https://github.com/jkd04255/wifi/pull/1 — 아직 main 병합 전.
- 현재 main의 기존 v1.6 정적 시연은 그대로 유지. Python API는 GitHub Pages에 배포되지 않음.
- **다음 GATE 3**: 실제 2번/3번 연동 계약 확인 → 화면에 최소한 연결 → 회귀 QA → PR 검토/병합/배포. 구체 계약 확보 전 실측·실시간 통합 완료로 표시하지 말 것.
