# Wi-Fi Placement Studio — 필수영역 70점 / 랜 포트 미고려 (경량 배포)

Status: **GATE 3 개발 시연용 파일 · 정식 배포 승인 아님**  
Branch: `feat/optimizer-required-pin-distribution` (Draft PR #5), based on the unmerged Draft PR #3 `feat/optimizer-required-pin`.  
Build: Windows GitHub Actions `Package tiny no-LAN mandatory-pin EXE and HTML`.

## 배포 파일

- `WiFi_Placement_RequiredPin_70_NoLAN.exe`: **작은 네이티브 Win32 EXE**. 오프라인 HTML을 실행 파일 내부에 포함하고, 실행하면 설치된 Microsoft Edge 또는 Chrome을 주소창 없는 **앱 전용 창**으로 엽니다. Python, FastAPI, pywebview, .NET 패키지 또는 별도 로컬 서버를 설치하거나 실행할 필요가 없습니다.
- `WiFi_Placement_RequiredPin_70_NoLAN.html`: 같은 UI의 **완전한 오프라인 HTML**. HTML 하나만 실행해도 도면, RSSI, 필수영역 핀, **70점 조건을 적용한 최적 공유기 배치 계산**까지 작동합니다.
- 두 파일 중 하나만 사용해도 됩니다. Windows에서는 EXE가 앱 형태로 열리고, macOS/Linux/태블릿에서는 HTML을 지원 브라우저에서 열 수 있습니다.

과거에 제공한 18MB대 EXE는 Python 최적화 API와 WebView .NET 라이브러리를 통째로 포함했고, 초기 경량 EXE도 같은 핵심 라이브러리를 갖고 있었습니다. **이번 버전은 해당 패키지를 제거한 별도 빌드**입니다. HTML과 EXE 결과는 같은 로컬 RSSI 모델을 사용합니다.

## 기능 / 알고리즘

- 예전 **방 용도 그리기·지정 UI 삭제**. 벽 그리기, 선/사각형, 영역 부분 지우개, +100/0/−100 중요도 브러시는 보존했습니다.
- 도면에 **필수영역** 핀을 찍고 0.3–3m 반경 지정/선택/드래그/삭제 가능.
- 핀 하나당 중심 1 + 안쪽 고리 8 + 바깥 고리 8 = **17개 표본점**에서 각각 **예상 품질 ≥70/100**이어야 공유기 후보로 인정합니다.
- 점수 변환: `clamp((predicted RSSI dBm+90)/55*100,0,100)`. 이 모델에서 70점은 대략 **−51.5 dBm**입니다.
- 전체 평균 점수가 좋아도 필수영역 표본점이 하나라도 70점 미만이면 해당 후보는 **배제**합니다.
- 공유기 위치는 **실내 직사각형 범위에서 벽 바로 위와 도면 가장자리 0.2m 이내는 제외**하고 탐색합니다.
- **랜 포트 위치, LAN 연결 가능 위치, 랜선 길이, 케이블 시공 경로는 전혀 입력받거나 제약으로 사용하지 않습니다.**
- 유효 후보가 없으면 추천 불가를 명시하고 과거 BEST 마커도 남기지 않습니다.

**한계:** 실제 1·2·3 팀원 확정 데이터 계약 및 실측 보정은 미연결. 모델은 기존 v1.6의 RSSI *예측*을 사용합니다. 유한한 17개 표본점이 원형 영역의 모든 점과 실제 Wi-Fi 속도를 보장하지 않으며, 격자 탐색 결과가 수학적 전역 최적해임을 보장하지도 않습니다.

## 빌드 구조

- `tools/build_required_pin_nolan.py`: Draft PR #3의 `preview/stage3.html`에서 랜 포트 설정과 Python API 의존을 제거한 배포용 독립 HTML을 생성. 기존 PR #3 원본은 변경하지 않습니다.
- `tools/required_pin_nolan_win32.c`, `tools/required_pin_nolan.rc`: Windows 네이티브 PE 앱 런처. HTML을 실행 파일에 `RCDATA`로 포함하고 `%LOCALAPPDATA%\WiFiRequiredPin70\app.html`에 추출한 뒤 Edge/Chrome `--app=file:///...` 모드로 실행합니다.
- `tools/test_required_pin_nolan.cjs`: 실제 내장 RSSI 엔진 코드의 정상 통과, 70점 미달 후보 거부, 2개 핀, 벽 위 공유기 후보 배제, LAN 값 무시, 도면 내부 20cm 이격을 검증.
- `tools/test_required_pin_nolan_browser.py`: Chromium·WebKit에서 `file://` 배포 HTML의 핀 추가→도면 적용→공유기 추천→필수영역 상태 UI 검증.
- Windows Actions에서 실제 PE 헤더, 내장 HTML, EXE `--self-test`와 브라우저 테스트를 실시합니다.

## 실행 안내

1. 최신 성공한 Windows Actions의 `WiFi_RequiredPin_70_NoLAN_EXE_HTML` ZIP을 다운로드해 압축 해제합니다.
2. `.exe`를 실행하면 Edge/Chrome 앱 창이 뜨고, `.html`을 더블클릭하면 브라우저로 직접 실행됩니다.
3. **필수영역** 핀 추가 → 반경 조절 → **Apply** → **최고의 위치 찾기**. 랜 포트 위치나 랜선 길이는 입력하지 않습니다.

EXE는 서명되지 않은 자체 빌드이므로 Windows SmartScreen 경고가 나타날 수 있습니다. 실제 사용자 Windows PC의 GUI 및 설치 환경은 수동으로 검증해야 합니다.

## 승인 제한

배포용 파일은 별도 Draft PR #5의 GitHub Actions artifact이며 **main, GitHub Pages, 원본 v1.6 HTML, Draft PR #3 또는 #2를 병합·수정·배포하지 않습니다**. 공식 1·2·3 계약/실측 검증이 미확정이므로 **GATE 3 HOLD**입니다.
