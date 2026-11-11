# Wi-Fi Placement Studio — 필수영역 단일 좌표 70점 · 랜 포트 미고려 (경량 배포)

작성일: 2026-11-11 (KST)  
상태: **GATE 3 기능 시연, 정식 배포 HOLD**  
Branch: `feat/optimizer-required-pin-distribution` (Draft PR #5; 기존 Draft PR #3 기반)

## 이번 변경: 반경이 아닌 점 하나

- 필수영역 도구로 클릭한 **단일 X/Z 좌표**에 핀을 배치합니다.
- 각 핀은 정확히 그 좌표 **1곳**의 RSSI 모델 예상 품질이 **70/100 이상**이어야 합니다.
- 두 개 이상 핀을 배치하면 **모든 핀 좌표**가 70점을 넘어야 합니다. 한 점이라도 부족한 공유기 후보는 최적화에서 배제합니다.
- 예전 반경(0.3~3m), 원형 표시, 반경 편집 슬라이더, 핀당 17개 표본점은 **완전히 삭제**했습니다.
- 기존 JSON의 `requiredPins[].radiusM` 필드는 **무시**하고 `id,x,z,minQualityScore`만 가져옵니다. 새로 내보내는 JSON에는 핀의 반경 값이 없습니다.
- 좌표의 점수는 기존 `clamp((RSSI_dBm+90)/55*100,0,100)`이며, 이 모델에서 70점은 약 −51.5dBm입니다.
- LAN 포트 위치, 랜선 길이, 연결 지점, 케이블 배선을 **입력받지 않고 제약으로 사용하지 않습니다**.
- 이전의 콘크리트 벽, 스케치/직사각형, 지우개, 중요도 +100/0/−100 브러시, 히트맵, Undo 등은 보존합니다.

## 배포용 파일

- `WiFi_Placement_RequiredPoint_70_NoHeightLimit.exe`: 약 **247KB** Windows 네이티브 EXE. HTML을 내부에 포함하고 설치된 Edge/Chrome을 별도 앱 창(`--app=file://`)으로 엽니다. Python 서버는 필요 없습니다.
- `WiFi_Placement_RequiredPoint_70_NoHeightLimit.html`: 약 **109KB** 독립 오프라인 HTML. 브라우저에서 핀 위치 변경·히트맵·70점 강제 최적화가 동작합니다.
- 두 파일을 포함한 GitHub Actions artifact `WiFi_RequiredPoint_70_NoHeightLimit_EXE_HTML`. 새 파일명으로 기존 **반경형 EXE/HTML과 구분**합니다.

## 검증

- `tools/build_required_pin_nolan.py`에서 기존 PR #3의 도면/중요도 코드를 유지하면서 **배포용 HTML만** 점 중심 70점 제약으로 변환합니다. 원본 `preview/stage3.html`이나 `main`을 변경하지 않습니다.
- `tools/test_required_pin_nolan.cjs`: 정확히 **핀 1개 → 검사 1점**, 핀 2개 → 검사 2점, 이전 반경값 영향 없음, LAN 입력 영향 없음, 70점 미달 후보 거부, 콘크리트 벽 위 배치 차단.
- `tools/test_required_pin_nolan_browser.py`: Chromium/WebKit `file://` HTML에서 도면에 핀 배치→JSON 저장→반경이 포함된 구형 JSON 불러오기→반경이 없는 JSON 확인→70점 추천 결과 검증.
- Windows CI에서는 실제 PE 헤더 및 내장 필수영역 기능과 EXE `--self-test`를 검증합니다.

## 사용법

ZIP 압축 해제 후 EXE 또는 HTML을 실행합니다. 도면을 그린 뒤 **필수영역** 핀을 지정하고 Apply → **최고의 위치 찾기**를 누르시면 됩니다. 반경이나 LAN 포트 관련 입력은 없습니다.

**한계:** 70점은 실제 측정이나 Wi-Fi 속도 보장이 아니라 기존 v1.6 RSSI 모델의 예측 점수입니다. 확정된 1/2/3팀 데이터 계약과 실측 보정은 연결되지 않았습니다. 공유기 후보 탐색은 격자와 주변 위치 평가를 사용하므로 전역 최적을 수학적으로 보증하지 않습니다. Windows EXE는 서명되지 않았으며 사용자 실제 PC에서 화면 실행까지 검증한 것은 아닙니다.

**배포 제한:** Draft PR #5 별도 브랜치의 GitHub Actions artifact만 전달합니다. PR #2/#3, `main`, GitHub Pages, 원래 v1.6 HTML에는 병합·반영하지 않았고 **GATE 3 HOLD**를 유지합니다.

## 2026-11-11: 천장/벽 높이 입력과 제한 제거

- 천장·벽 높이 입력(`roomHeightM`)을 배포 UI에서 **삭제**했습니다. 기존 도면의 `roomHeightM`와 `walls[].heightM`는 가져올 때 무시하고 새 JSON에도 저장하지 않습니다.
- 콘크리트 벽은 **평면 XZ 상의 선분 차폐벽**으로 취급합니다. 공유기와 수신기 사이의 평면 신호 경로가 벽을 통과하면 Y 높이에 무관하게 콘크리트 감쇠를 적용합니다. 따라서 실제 낮은 칸막이 위로 전파가 돌아가는 상황은 이 단순 모델에서 표현하지 못합니다.
- 공유기·수신기 Y좌표 입력은 **유지**합니다. 두 좌표의 값은 각각 0 이상의 유한한 숫자를 입력할 수 있으며 별도의 천장 최대 높이로 잘리지 않습니다. 3차원 직선거리에 따른 RSSI 감쇠 계산은 계속 적용합니다.
- 기존 사용자의 필수영역 핀은 **정확한 단일 XZ 위치에서 예상 품질 70점 이상**이라는 필수 제약을 유지합니다. 중요도 브러시, 도면 벽, 히트맵과 랜 포트 무시 규칙도 유지합니다.
- 빌드/테스트: `tools/test_required_pin_nolan.cjs`는 높이가 0.01m로 저장된 기존 벽도 평면 경로를 차폐하는지와 Y=12~13m에서도 값이 유한한지 검사합니다. `tools/test_required_pin_nolan_browser.py`는 Chromium·WebKit에서 Y=12.5m/13.5m 입력, 구형 도면 천장/벽 높이 제거와 저장 여부를 검사합니다.
- **버전 구분:** 배포 파일 이름은 `WiFi_Placement_RequiredPoint_70_NoHeightLimit.exe`, `WiFi_Placement_RequiredPoint_70_NoHeightLimit.html`, ZIP `WiFi_RequiredPoint_70_NoHeightLimit_EXE_HTML`입니다. 이전 높이 제한 버전과 혼동하지 마세요.
- 사용자 Windows PC의 직접 조작 및 실측 RSSI 비교는 여전히 미검증이며, Draft PR #5는 별도 브랜치로만 유지합니다. **GATE 3 HOLD, main/Pages 미변경**.
