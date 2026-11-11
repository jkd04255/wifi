# 실측 보정형 Wi-Fi 배치 시뮬레이터 — 4번 개발 3단계 계획

작성일: 2026-11-09 · 담당: 4번 — 최적 공유기 배치 알고리즘/백엔드

## 목표와 범위 동결
실내 도면, 벽, 공유기 높이/위치, 랜 포트, 중요도 및 2번 엔진의 예상 RSSI를 이용하여 **현실적으로 설치 가능한 공유기 위치 1곳**을 추천한다. 추천 근거·예상 케이블 길이·기존 대비 개선 점수·추가 AP 필요 여부를 설명한다. **1번 UI, 2번 예측 엔진, 3번 측정 앱을 대신 만드는 프로젝트가 아니다.**

## 1단계 (GATE 1): 기준본 보존 및 GitHub 시연

목표: 수정·알고리즘 개발 전에 이미 만든 결과를 그대로 재현 가능한 기준점으로 보존.

- [x] GitHub jkd04255/wifi 저장소 생성 및 공개 여부 확인
- [x] ChatGPT GitHub 앱의 저장소 쓰기 권한 확인
- [x] v1.6 HTML 원본을 legacy/에 보존, 같은 소스를 index.html에도 업로드
- [x] README·PLAN·HANDOFF·AGENTS 등 작업 연속성 문서 커밋
- [x] GitHub Pages 활성화 및 GitHub Actions 빌드·배포 성공 확인
- [x] 사용자 직접 URL 화면 및 시연 정상 작동 확인 (HTTP 200 독립 계측은 미실시)
- [x] 사용자 직접 시연 정상 작동 확인 (세부 기능별 자동 회귀 및 모바일 별도 검증 미실시)
- [x] 정적 HTML 내부 계산과 Python/실측 데이터 미연동 상태를 README에 기록

**완료 조건:** GitHub URL + 실제 접속 가능한 GitHub Pages URL + 검증된 v1.6 기준 동작 목록. 중 하나라도 확인 안 되면 GATE 2로 넘어가지 않음.

**GATE 1 판정: 완료 (2026-11-09) — 사용자 시연 정상 확인, Pages 배포 성공. 세부 자동 E2E는 수행하지 않음.**

## 2단계 (GATE 2): 독립 최적화 알고리즘 및 백엔드

목표: 기존 입력·전파 예측·측정 보정 결과를 활용하여 4번 담당 모듈만 개발.

1. 1번 LayoutData / 2번 예측 응답 / 3번 보정 출력의 최신 데이터 계약을 확인한다. 현재 확인된 과거 기록은 POST localhost:8000/simulate 및 values[row][col]이며 변경 가능성이 있다.
2. 도면 평면 x-z와 수직 y의 좌표계를 유지하고, 2D grid row/col을 명시적으로 변환한다.
3. 실내 유효 영역에서만 후보를 생성한다. 집 밖, 벽 위, 지울 수 없는 금지 구역을 배제하고 공유기 높이를 반영한다.
4. 랜 포트와 공유기 후보 사이 경로를 계산하여 사용자 제공 랜선 길이 이하인 후보만 통과시킨다. 통과 여부 불확실 시 '검증불가'로 표시한다. 단순 직선 거리를 무조건 경로 길이로 간주하지 않는다.
5. 각 후보의 2번 엔진 예상 RSSI를 평가해 중요도 +100 우선 / 0 보통 / -100 낮은 우선순위 점수를 계산한다. -100 구역의 신호를 의도적으로 줄이는 최적화는 금지한다.
6. 현재 대비 품질이 높은 추천 1개를 결과로 제시하고 위치/점수 차/주요 공간 커버리지/선정 사유를 설명한다.
7. 최적 위치에서도 주요 위치 품질이 기준 미달이면 추가 AP 검토 권고를 반환한다. 확정 설치 진단처럼 표현하지 않는다.
8. POST /optimize 독립 API를 제안하고 JSON 계약/단위(m,dBm)/오류 조건을 문서화한다. /simulate는 변경하지 않는다.

제안 응답: recommendedPosition(x,z,y), estimatedCableLengthM, scoreBefore, scoreAfter, criticalCoverage, additionalApAdvised, reason, feasibilityWarnings.

자동 테스트 최소 5종: 실외·벽 위 후보 제외, 케이블 제약 준수, 중요도 +100 우선, 개선 점수 비교, AP 권고 기준. 유효 후보 없을 경우 '추천 불가 + 이유' 반환.

**완료 조건:** 정확한 API 계약 및 자동 테스트 통과. 임의 상수·예측 미검증을 실제 정확도로 표현하지 않음.

**GATE 2 판정: 독립 Python 백엔드 구현 및 자동 테스트 완료 (2026-11-09).** `feat/optimizer-stage2` 기능 브랜치 및 PR #1에 반영. Python 3.11/3.12 각각 21개 테스트 통과(총 42개), [실행 기록](https://github.com/jkd04255/wifi/actions/runs/42629894652). 실제 2번/3번 데이터 연동과 웹 화면 연결은 3단계에서 수행하며, 이번 단계에서 완료로 표현하지 않음.

## 3단계 (GATE 3): UI 최소 연동, 비교 결과, 최종 시연

- [ ] 기존 '최고의 위치 찾기' 버튼을 별도 최적화 API와 최소 연동. 현재 로컬 기능은 백업 및 비교 대상으로 유지.
- [ ] 도면에서 추천점 표시; 현재↔추천 위치, 예상 케이블 길이, 중요 구역 커버리지, AP 권고를 간결하게 비교.
- [ ] 2.4/5 GHz, 중요도 3종, 실내 밖 후보, 벽, 케이블 부족, API 오류/지연, 실측 보정 유무 검증.
- [ ] feat/optimizer-* 기능 브랜치 + 테스트 + PR + 회귀 검토 + main 병합.
- [ ] GitHub Pages 정적 시연 재검증. Python API가 라이브로 배포되지 않았다면 '정적 데모/로컬 실행'이라고 정확히 표기.
- [ ] 재현 절차, 테스트 증거, 남은 한계를 README와 docs/HANDOFF.md에 갱신.

**완료 조건:** 도면 → 유효 후보 → 최적 위치 → 비교 출력이 재현되고, 테스트·저장소·시연 URL을 검증하여 공유할 수 있어야 함.

## 범위 이탈 방지 (변경 불가)

1. 담당 4번 바깥의 UI/예측/측정 코드를 재구현하지 않는다.
2. 로그인, 회원 시스템, DB, GPS, CSI 분석, 맵, 클라우드 비용 유발 서비스, 디자인 전면 개편을 추가하지 않는다.
3. 원본 v1.6 파일은 수정하지 않는다.
4. GATE 1 검증 전 알고리즘 개발 단계로, GATE 2 검증 전 UI 연동 단계로 넘어가지 않는다.
5. 실제 측정으로 보정되지 않은 RSSI는 예측값으로 표기한다.
6. 사용자에게 결과를 보고할 때 완료와 미검증을 구분한다.

## 사용자 다음 행동
- 즉시: GitHub Pages를 Settings → Pages → Deploy from a branch → main → /(root)로 설정 (자동 설정되지 않았을 경우).
- GATE 2 전: 최신 2번/3번 팀원 데이터 계약 파일을 제공하거나 저장소에 업로드.


## GATE 3 현재 진행 상태 (2026-11-09)

- [x] 별도 `preview/stage3.html` (기존 UI 최소 변경) 및 로컬 동일 출처 Uvicorn 시연 서버 구현.
- [x] 기존 v1.6 최적화 기본값 유지; 사용자 명시적 4번 API 시연 선택에 한해 후보/케이블/비교/AP 권고 표시.
- [x] 2·3번 계약 미확정 확인, v1.6 예측값을 '실측 미보정 시연'으로 구분.
- [ ] Chromium/WebKit 통합 자동 QA 통과 확인.
- [ ] 2·3번 실제 팀원 계약 및 실제 예측/실측 보정 데이터로 교차 검증.
- [ ] 1번 실제 집 외곽 footprint/LAN 포트 정보 계약 확보.
- [ ] 통합 QA 후 PR review·main 병합·Pages 재배포 검증.

**판정: GATE 3 HOLD** — 로컬 시연이 통과해도 확정 계약 없는 상태에서는 정식 통합 완료나 배포로 표현하지 않음. Draft PR #2: https://github.com/jkd04255/wifi/pull/2.

### GATE 3 중간 QA 기록
- [x] 코드로 검증된 로컬 API 시연 및 원본 v1.6 유지.
- [x] Chromium API 모드 및 모바일, WebKit 기존 모드, 설정 누락 예외 확인.
- [x] Python 21 + 브라우저 4 = 25개 자동 테스트 GitHub Actions 성공 ([run #42633059037](https://github.com/jkd04255/wifi/actions/runs/42633059037)).
- [ ] **실제** 2·3번 팀원 데이터 계약 기반 연동 및 실내 외곽 지도 제약 최종 확인.
- [ ] 정식 API WebKit 검증, 전 대역/브러시/벽/케이블 추가 회귀와 PR 리뷰.
- [ ] PR 병합 및 Pages 배포 — **계약 미확정으로 HOLD**.


### GATE 3 추가 테스트 검증 (2026-11-09)

- [x] WebKit 로컬 API 최적화/추천 적용 E2E.
- [x] 2.4/5GHz에서 예측 RSSI 페이로드가 달라짐을 E2E 확인.
- [x] 중요도 +100/0/-100 브러시 JSON 도면 import → backend priority 배열 검증.
- [x] 벽/랜선 제한에 따른 후보 탐색 차이 확인.
- [x] API 장애 HTTP 503 및 네트워크 실패 시 명확한 오류와 기존 추천값 지우기 확인.
- [x] Python 21개 + Chromium/WebKit 9개 = **30/30 자동 테스트 성공** ([Actions #42634218483](https://github.com/jkd04255/wifi/actions/runs/42634218483)).
- [x] [1·2·3번 팀원 데이터 계약 요청 템플릿](TEAM_CONTRACT_TEMPLATE.md) 작성 (미확정으로 명시).
- [ ] 실제 팀원 소스/계약 확보, 실제 데이터 기반 통합 및 실내 외곽선 검증; 정식 Gate 3 **HOLD**.


### 합성 계약 준비 및 접근 검증 (2026-11-09)

- [x] 기존 파일 트리와 Draft PR #2 확인 — 1·2·3번 최신 확정 계약 부재.
- [x] 합성 전용 RSSI X-Z 좌표·주파수·배열·보정 상태 검증 및 API 요청 어댑터 작성, 테스트 fixture 추가.
- [x] Python 86/86 및 browser 9/9 = **95/95 테스트 성공** ([CI](https://github.com/jkd04255/wifi/actions/runs/42635704295)).
- [x] Public 저장소 `jkd04255/wifi` 확인, 열람과 push 권한 차이 기록.
- [ ] 팀원 1·2·3 계약/데이터 수신 및 실데이터 교차검증.
- [ ] GATE 3 정식 통합 판정 및 PR 병합·Pages 재배포 — **HOLD**.


### GATE 3 UI 교체: 필수영역 핀 (2026-11-11)

- [x] 방 용도 지정 UI 제거, 필수영역 핀 추가 (반경 0.3–3m, 70/100 최소 예측 품질, 최대 12개).
- [x] 필수 품질 제약이 전체 중요도 평균보다 우선하도록 4번 Python optimizer 기능 구현; 조건 미달 후보는 추천 불가.
- [x] Preview JSON import/export, Undo, 개별 삭제, 도면 크기 조정 및 최소품질 현황 UI.
- [x] Python 94/94 + Chromium/WebKit 12/12 총 106/106 검증 [Actions #42977957957](https://github.com/jkd04255/wifi/actions/runs/42977957957).
- [ ] 후속 문구 보완 HEAD 전체 회귀 CI 확인.
- [ ] 실측 데이터 계약, 실제 외곽, 연속 원판 범위의 정확성 검증.
- [ ] 본 Draft PR #3 및 기반 Draft PR #2의 병합/Pages 배포 — **HOLD**.


### Required pin QA finalized (2026-11-11)
- [x] Final code commit `68b5622b85192cad4ef49a94f49859b7a01e3f51` Python 94/94 + browser 13/13 = **107 PASS** ([Actions #42978598628](https://github.com/jkd04255/wifi/actions/runs/42978598628)).
- [x] JSON round-trip pin survival and imported legacy room-purpose removal.
- [ ] Full GATE 3 approval and public deployment — **HOLD**.


### GATE 3 필수영역 핀 후속 UI/UX 작업 (2026-11-11)
- [x] 기존 핀을 직접 드래그해 이동, Undo 1회 복구 및 도면 밖 이동 제한.
- [x] 선택한 핀만 반경(0.3–3m) 수정 및 잘못된 반경 거부.
- [x] 결과 화면의 핀별 현재/추천 최소 예측 품질, 70점 충족/미달 배지 표시; 수정·API 실패 시 오래된 추천 제거.
- [x] Python 94 + Chromium/WebKit 17 = **111/111 PASS** ([GitHub Actions #42982663205](https://github.com/jkd04255/wifi/actions/runs/42982663205), code SHA `18c998114a194bf040af002c9dbaf678f6c5a0ef`).
- [ ] 실제 팀원 1·2·3 계약, 예측/실측 보정 비교, 연속 면적 품질 및 실기기 검증.
- [ ] Draft PR #3/#2 main 병합 및 GitHub Pages 배포 — **GATE HOLD**.


### GATE 3 모바일 필수영역 핀 조작성 / 접근성 (2026-11-11)

- [x] 터치 드래그 허용 범위 확장, 터치 손떨림 오동작 방지, 한 번의 Undo / 취소 동작.
- [x] 겹친 핀 반복 터치 선택 순환, 핀 목록과 다음 핀 버튼, 선택 테두리 표시.
- [x] 선택 핀 반경의 키보드·스크린리더 설명, 터치 목표 크기 개선.
- [x] 모바일 Chromium/WebKit 테스트 4종 추가; 전체 Python 94 + browser 21 = **115 PASS** ([Actions #42984403224](https://github.com/jkd04255/wifi/actions/runs/42984403224)).
- [ ] 1/2/3팀 데이터 계약, 예측/실측 정합성, 실제 iPhone Safari 터치 동작 및 실내 외곽 정확성 검증.
- [ ] GATE 3 완료, PR #2/#3 병합 및 Pages 재배포 — **HOLD**.


### GATE 3 모바일 멀티터치·드래그 취소·키보드 접근성 검증 (2026-11-11)

- [x] 현재 PR/브랜치/파일 점검: 정식 1/2/3번 계약 부재 재확인 (템플릿/합성 샘플만 존재).
- [x] 보조 터치 간섭 차단, 터치 드래그 취소 시 원위치·Undo 복구.
- [x] 겹친 핀의 선택 링을 가장 위에 표시, 삭제/불러오기 후 선택 목록 정합성 회복.
- [x] 캔버스 키보드 접근: Enter/Space 새 필수 핀, 방향키 ±0.1m / Shift ±0.5m, 경계 제한 및 Undo.
- [x] 신규 Chromium/WebKit 모바일 회귀 4개; Python 94/94 + 브라우저 25/25 = **119/119 PASS** ([Actions #42986058154](https://github.com/jkd04255/wifi/actions/runs/42986058154), code SHA `edd06870fe22c2b55945dd873f5a0e909c7b2017`).
- [ ] 실제 iPhone Safari 및 VoiceOver, 팀 1/2/3 계약·보정 데이터 정합성, 실제 외곽, 70점 실측 검증.
- [ ] PR #2/#3 정식 병합과 Pages 재배포 — **GATE 3 HOLD**.


### GATE 3 Undo history and keyboard boundary follow-up (2026-11-11)

- [x] Fix full 30-entry Undo history eviction when a required-pin touch drag is cancelled: stage snapshot during drag, commit only on pointerup, pointercancel restores X-Z without mutating history.
- [x] Add regression for 30-entry Undo history preservation after cancellation (Chromium/WebKit).
- [x] Add exact right/lower pin-radius boundary test; no-op keyboard movement must not create Undo entry.
- [x] Latest CI [#42987876155](https://github.com/jkd04255/wifi/actions/runs/42987876155): Python 94/94 + Chromium/WebKit browser 27/27 PASS; HEAD `ee542b751b9eda123fe13d3bfefb41a3ec3ca928`.
- [ ] Actual iPhone Safari/VoiceOver, real RF measurements and team 1/2/3 signed-off schemas.
- [ ] PR #2/#3 merge and Pages deployment — **GATE 3 HOLD**.
