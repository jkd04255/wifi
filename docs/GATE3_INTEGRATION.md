# GATE 3 — UI 최소 연동 (로컬 시연, 계약 미확정)

2026-11-09 / branch: `feat/optimizer-stage3-integration`

## 1. 팀 인터페이스 점검

- 1번 UI: 기존 `index.html` v1.6 (schemaVersion `1.1`, 바닥 X-Z·수직 Y; 벽 `walls:[{x1,z1,x2,z2,material}]`, 중요도 `importanceStrokes` 및 `zones`).
- 2번 RSSI 예측: 과거 메모의 `POST localhost:8000/simulate`, `values[row][col]`만 확인됐습니다. **현재 2번 코드와 정확한 요청/응답 스키마가 이 저장소에 없어 계약 확정 불가.**
- 3번 실측 보정: 측정점 X-Z·RSSI·대역·측정 시 공유기 위치가 필요하다는 과거 기록은 있지만 **현재 3번 코드/보정 결과 스키마는 저장소에 없음**.
- **정식 2/3번 연동 성공이라고 주장하지 않음.** GATE3의 정식 통합·main 병합 조건은 아직 충족되지 않았습니다.

## 2. 현재 구현된 로컬 시연

- 변경 금지 원본: `legacy/WiFi_Placement_Studio_v1.6_offline.html`.
- 기존 배포본: `index.html` — 수정하지 않음.
- 시험 UI: `preview/stage3.html` — 기존 화면 복사본에만 4번 설정(로컬 API 모드, 사용자가 입력하는 LAN X/Z/Y, 랜선 최대 길이)과 비교 문구 추가.
- 로컬 서버: `backend/dev_server.py`, `http://127.0.0.1:8001/preview/stage3.html`; 동일한 origin으로 `/candidate-locations` 및 `/optimize` 요청.
- '기존 v1.6'이 **기본 선택**이고, 사용자가 명시적으로 '4번 Python API (로컬 시연)'을 선택해야 새 경로 사용.
- `/candidate-locations`: 물리적 후보와 예상 케이블 길이를 받음.
- 각 후보의 평가 점 RSSI는 기존 브라우저 `WifiEngine.value()`로 생성 (기존 오프라인 모델 기반, **2번 엔진 / 3번 보정값이 아님**).
- `/optimize`: 후보와 RSSI를 받아 최적 위치/비교 점수/추가 AP 검토 권고 반환.
- 기존 `best` 마커·`useBestBtn` 위치 적용 메커니즘 그대로 활용.
- 서버가 없으면 새 API 모드에서 오류를 표시하고 **묵시적으로 레거시로 전환하지 않음**.
- 유효 후보가 없으면 추천 실패로 표시하고 이전 추천을 재사용하지 않음.

## 3. 실행

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn dev_server:app --host 127.0.0.1 --port 8001
```

브라우저: `http://127.0.0.1:8001/preview/stage3.html`

도면을 그리거나 기존 도면을 불러오고 → Apply → 4번 설치 제약 펼치기 → 로컬 API 모드 → 실제 LAN X/Z/Y 및 최대 랜선 입력 → '최고의 위치 찾기'.

### 자동 QA

```bash
cd backend
python -m unittest discover -s tests -v
# Playwright를 설치한 환경에서:
python -m pip install playwright
python -m playwright install chromium webkit
python tests_browser/test_preview.py
```

GitHub Actions: `.github/workflows/stage3-ci.yml`에서 Python unittest와 Chromium / WebKit 시연 동작 검증 예정.

## 4. 알려진 한계 · 필수 남은 조건

- **집의 정확한 외곽 폴리곤을 제공하는 도면 계약이 없음.** 현재는 X-Z 직사각형을 실내로 근사하므로 불규칙한 주택의 실제 집 밖 후보 방지에 충분하지 않음. 예시 시연 및 검증 외 실설치 추천 금지.
- LAN 위치와 최대 케이블 길이는 사용자가 직접 입력. 케이블은 장애물 없는 수평 직선 또는 벽 회피 격자 최단 + 수직 높이차 **추정치**로, 실제 시공 길이가 아닙니다.
- 중요도 브러시를 `WifiEngine.weight()`의 샘플값으로 +100/0/-100으로 이산화하는 **임시 어댑터**. 1번 담당의 최종 중요도 스키마를 확보해야 정식 확정 가능.
- 팀원 2번/3번의 실제 코드·모델 제공 전, API 수신 RSSI를 실측 보정이나 검증된 예측이라고 표시하지 않음.
- GitHub Pages에서는 Python API를 실행하지 못함. 이 통합 시연은 **로컬 Uvicorn 서버**에서 동작. 공개 배포 서버/유료 서비스 설치는 승인·설계되지 않았습니다.
- 정식 병합·배포를 위해 실제 2/3번 계약 확인, 외곽 지도 계약, 통합 QA, 보안/성능 검증 및 리뷰가 필요.

## 5. 현재 Gate 판정

**GATE 3 로컬 시연 구현 및 QA 가능 단계. 정식 통합 GATE 3 HOLD / main 병합 금지.** 기존 GitHub Pages는 계속 v1.6 배포본을 유지합니다.


## 6. 보강 테스트 및 팀원 계약 인수인계 (2026-11-09)

- [브라우저/백엔드 30개 자동 테스트 통과](https://github.com/jkd04255/wifi/actions/runs/42634218483) — Python 21/21 + Chromium/WebKit 9/9.
- 신규 테스트: WebKit 로컬 API 모드, 2.4/5GHz RSSI 입력 비교, 중요도 3종 전달, 벽·랜선 제약, API 네트워크/503 장애 복구.
- [팀원 1·2·3 확정 계약 요청 템플릿](TEAM_CONTRACT_TEMPLATE.md) — **PROPOSED/UNVERIFIED**, 팀원의 실서명이나 실제 데이터 계약 아님.
- 정식 연동 차단 요인: 1번 실내 외곽 footprint, 2번 최신 /simulate 입력·출력, 3번 보정 결과 스키마/실측 데이터. 이들을 확보하기 전에는 v1.6 예측값만 이용한 로컬 시연이며 공개 Pages 변경 없음.
