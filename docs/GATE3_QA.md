# GATE 3 — 로컬 통합 QA 및 공식 배포 HOLD

일자: 2026-11-09 (KST)
PR: https://github.com/jkd04255/wifi/pull/2 (Draft; base: feat/optimizer-stage2)
검증된 기능 코드 SHA: `dc49f0d1ead124eb30815664bbe28ea773647254`

## 실제 검증 (GitHub Actions)

CI: https://github.com/jkd04255/wifi/actions/runs/42633059037
상태: `completed / success`.

| 작업 | 결과 | 테스트 범위 |
|---|---|---|
| Python 3.12 백엔드 `unittest` | **21/21 통과** | 실내/외·벽 위·케이블 경로·중요도·AP 권고·API |
| Chromium — 로컬 API 시연 | **통과** | 후보 생성 → Optimize → 예상 케이블/신호 비교 → 기존 적용 버튼 |
| Chromium — 설정 누락 처리 | **통과** | LAN 미입력 오류, 묵시적 폴백 금지, 오래된 추천 지움 |
| Chromium — 모바일 | **통과** | 390px 화면에서 기존 최적화 및 결과 표시 |
| WebKit — 기존 v1.6 | **통과** | 기본 선택 기존 모델, 기존 추천 결과 표시, 콘솔 JS 오류 없음 |

총 **Python 21 + 브라우저 4 = 25개** 자동 테스트 통과.

### 실패를 확인하고 해결한 내용

- 초기 HTML 복사 수정본에 함수 본문 삽입 위치 오류가 발생해 브라우저 테스트 4개가 실패했습니다.
- 문제를 처음부터 원본 HTML 기준으로 재생성하여 해결했고, 이후 4개 인라인 JS 스크립트의 구문 검사가 모두 통과했습니다.
- 실패 기록이 아닌 수정된 최종 코드에 대한 GitHub Actions 실행 결과를 위에 연결했습니다.

## 변경 범위 검토

- 추가: `preview/stage3.html`, `backend/dev_server.py`, `backend/tests_browser/test_preview.py`, `.github/workflows/stage3-ci.yml`, 문서.
- 변경하지 않음: `index.html`, `legacy/WiFi_Placement_Studio_v1.6_offline.html`, 기존 2번/3번 업무 코드.
- 기존 정적 사이트 https://jkd04255.github.io/wifi/ 는 여전히 v1.6이며 4번 Python API 연결 화면이 아닙니다.

## 아직 미검증

1. WebKit에서 **4번 로컬 API 시연 모드**의 최적화 요청 경로 (기존 모드 회귀만 수행함).
2. 실제 2번 예측 엔진의 최신 입력/응답 JSON과 3번 실측 데이터 보정 결과에 대한 통합.
3. 집의 실제 외곽 폴리곤 및 LAN 포트 설치 경로 정확도.
4. 실제 Python 백엔드 외부 배포·보안/운영 검증.
5. 미보정 RSSI 예측값의 실제 공간 측정치 대조.

## 판정

**로컬 동작 시연 구현 및 검증 통과. GATE 3의 정식 통합·main 병합·공개 Pages 재배포는 HOLD.**

2번/3번 팀원의 최신 계약과 실제 외곽선 계약이 확인되면 별도 테스트를 추가하고 사용자 승인 범위 내에서 통합을 완료합니다.


## GATE 3 추가 회귀 검증 — 2026-11-09

테스트 코드 커밋: `fe544896cf6a47997f58ae318c688e21a4a5ca07`  
GitHub Actions: https://github.com/jkd04255/wifi/actions/runs/42634218483
상태: **completed / success**.

| 신규 브라우저 테스트 | 결과 | 검증 내용 |
|---|---|---|
| `test_webkit_local_api_full_flow` | 통과 | Safari 엔진의 4번 로컬 API 모드 → 최적화 → 위치 적용 |
| `test_24_and_5_ghz_send_different_predictions` | 통과 | 2.4/5 GHz 변경 후 `/optimize`로 전달되는 예측 RSSI 차이 및 주파수 반영 |
| `test_imported_importance_brushes_all_three_priorities` | 통과 | 사용자 도면 JSON의 +100/0/-100 브러시가 `probes[].priorityPct`로 각각 전달 |
| `test_wall_and_cable_restrict_browser_generated_candidates` | 통과 | 콘크리트 벽의 좌표 전송, 짧은 랜선에서 벽 건너 후보 배제, 긴 랜선에서 후보 증가 |
| `test_api_errors_never_silently_fallback_or_reuse_stale_result` | 통과 | `/optimize` 네트워크 차단 및 `/candidate-locations` HTTP 503 처리, 과거 추천 제거, 자동 레거시 전환 금지 |

기존 4개 브라우저 테스트도 모두 통과. **Python 21/21 + Chromium/WebKit 브라우저 9/9 = 전체 30/30 통과.**

**실측/외부 계약 상태:** GitHub 기능 브랜치 파일 목록에는 2번 전파 예측 모듈의 확정 `/simulate` JSON 계약과 3번 실측 보정 출력/실제 데이터 파일, 1번 실제 `footprint` 계약이 없습니다. 팀원 승인 전의 제안 서식은 [TEAM_CONTRACT_TEMPLATE.md](TEAM_CONTRACT_TEMPLATE.md)에 따로 정리했습니다. 데이터 예시는 실제 신호 측정치가 아닌 합성 값입니다.

**검증 한계:** 자동 테스트는 로컬 `dev_server` + v1.6 예측 RSSI 기반이며, 실제 2번/3번 신호 데이터 통합이나 실내 외곽선·배선 시공 적합성, 실서비스 공개 배포는 검증하지 않았습니다. WebKit은 Playwright 엔진 기반 시험이지 실제 iPhone Safari 실기기 QA는 아닙니다.

**GATE 3 판정 유지: 정식 통합 HOLD.** 초안 PR #2 및 원본/Pages 보호. 실제 계약 확인 전 `main` 병합·GitHub Pages 배포 금지.
