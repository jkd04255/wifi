# Windows EXE 실기기 QA — GATE 3 HOLD

- 대상: Draft PR #6의 `feat/point-pin-heightless-offline-exe` 브랜치. GitHub Actions `Lightweight standalone HTML and Windows EXE` 성공 실행의 Artifacts `wifi-studio-real-exe-and-html` ZIP을 다운로드합니다.
- 이 문서는 사용자 실기기 검증용 계획서입니다. Windows 10/11 실제 PC 실행 여부는 **미검증**이며, 체크 결과가 제출되기 전에는 배포 적합 판정을 하지 않습니다.
- EXE는 MSVC 컴파일된 Windows x64 PE GUI 실행 파일로 HTML을 내장합니다. 실행하면 `%LOCALAPPDATA%\\WiFiPlacementStudio\\studio_offline.html`에 HTML을 풀어 Edge 앱 창 또는 기본 브라우저로 엽니다. Python·Node·localhost 서버는 불필요하며, 브라우저 자체는 필요합니다.
- 실행 파일은 **서명되지 않았으며**, Windows SmartScreen 경고는 파일 안전성이 입증되지 않았다는 의미입니다. 출처를 신뢰할 수 없는 EXE는 실행하지 않습니다.

## 수행 체크리스트 (사용자가 직접 수행해야 함)

| 항목 | 수행 방법 | 합격 기준 | 실측 상태 |
| --- | --- | --- | --- |
| W01 압축/출처 | GitHub Actions 아티팩트 ZIP을 내려받아 압축 해제 | EXE 및 동일 버전 HTML 두 파일이 존재 | 미실시 |
| W02 실행 | 정상 Windows 10/11 x64 PC에서 EXE를 직접 열기 | Edge 앱 창 또는 기본 브라우저가 실제로 열림, 오류·빈 화면 없음 | 미실시 |
| W03 네트워크 독립 | Wi-Fi/유선 네트워크를 끊고 EXE 다시 실행 | 새 도면 작성, 분석, 최적화 가능; localhost/API 접속 요구 없음 | 미실시 |
| W04 핀 기본값 | ‘신호 세기’로 핀 2개를 서로 다른 위치에 추가 | 각 핀 기본 4칸(64점), 반경 없음 | 미실시 |
| W05 원터치 독립 편집 | 팔레트에서 첫 핀 3칸, 둘째 1칸, 첫 핀 다시 선택 | 각각 42점·9점 유지, 버튼 선택 상태와 드롭다운 일치 | 미실시 |
| W06 삭제/복구 | 둘째 핀을 선택하여 삭제 후 실행 취소 | 다른 핀 설정은 변경되지 않고 선택 핀만 복구 | 미실시 |
| W07 JSON 왕복 | JSON 저장 → 새 도면 → 불러오기 | 핀 수·X/Z 위치·칸수·점수·벽·공유기 높이 보존 | 미실시 |
| W08 높이/벽 | 공유기 Y=20m, 수신기 Y=15m 후 계산 | 천장·벽 높이 상한으로 잘리지 않고 오류 없이 계산 | 미실시 |
| W09 최적화 | 다른 신호 요구치 핀을 추가하고 추천 위치 계산 | 충족 조건 없는 후보는 거부, 성공 시 모든 핀 기준 충족 | 미실시 |
| W10 HTML 비교 | 같은 JSON을 단독 HTML에서 다시 열기 | EXE 화면과 계산 결과가 동일(동일 브라우저 조건) | 미실시 |

## 결과 기록

기기 OS/버전, 브라우저 종류/버전, 사용한 GitHub Actions run ID와 SHA, 성공/실패 체크항목, 스크린샷 또는 오류 메시지, ZIP 및 EXE SHA256을 기록합니다. 개인 정보·실내 주소·계정 비밀번호 등 민감한 내용은 기록하지 않습니다.

**보류 규칙:** 하나라도 실패 또는 확인되지 않은 항목이 있으면 실기기 QA는 미통과입니다. GATE 3 HOLD, Draft PR 미병합, main/Pages 변경 금지는 계속 유효합니다.

## 자동 CI와의 관계

- `html-check`는 JS 문법 및 필수 신호 점수 조건을 검사합니다.
- `browser-smoke`는 Chromium 오프라인 UI·JSON·단일점 최적화 회귀 테스트를 실행합니다.
- `win-exe`는 Windows 빌드 아티팩트가 실제 MZ/PE 파일인지 확인하지만 **Windows GUI 실행 시험은 아닙니다**.
- `stage3-ci.yml`의 Chromium/WebKit local integration QA는 별도 백엔드 계약을 보호하며 팀 1/2/3의 공식 데이터 계약 확인을 대신하지 않습니다.
