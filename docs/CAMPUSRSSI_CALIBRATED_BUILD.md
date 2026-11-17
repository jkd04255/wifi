# Wiplan CAMPUSRSSI 연구값 적용 — 보정판 빌드 검증 메모

**근거:** 사용자가 제공한 `Wiplan_CampusRSSI_Research_분석 보고서.docx` (38쪽 연구노트). 이 문서는 보고서 숫자와 현재 Draft PR #6의 기능을 대응시킨 개발 메모입니다. 논문의 외부 표준 계수로 오인하지 않습니다.

## 적용 방식

| 모델 | 경로손실지수 n | 콘크리트 벽 1회 통과 손실 | 용도 |
|---|---:|---:|---|
| OPEN | 1.6538 | 6.28 dB | 낙관적 거리감쇠 민감도 |
| GENERAL | 2.0011 | 6.8491 dB | **2.4GHz 히트맵 기본값** |
| DENSE | 2.3784 | 7.21 dB | 보수적 공간 민감도 |

- 모델: `RSSI = P0 - 10*n*log10(d) - alpha_c*Nc`. Wiplan 엔진의 d는 공유기 및 수신기 높이를 포함한 3차원 거리(최소 0.5 m)입니다. 데이터셋 회귀에서 사용한 2차원 거리(최소 0.3 m)와 정의가 다릅니다.
- 벽: 사용자 도면의 콘크리트 선분을 proper-crossing할 때 손실을 차감하고, 동일 경로교차 위치를 중복 차감하지 않습니다. 2회 이상 벽교차는 0/1회 측정 기반 외삽입니다.
- 절대 기준세기 P0: CAMPUSRSSI 각 AP의 회귀 절편을 일반 가정에 강제 적용하지 않고 기존 공유기 송신전력·안테나·P0 설정을 사용합니다.
- 2.4GHz: GENERAL을 중앙 히트맵에 사용합니다. `최고의 위치 찾기`는 세 프로파일 각각에서 모든 신호 세기 핀 기준을 하드 제약으로 검증한 후 공통 feasible 후보를 대상으로 worst-case 목적함수 maximin으로 추천합니다.
- 추천 불가능: `CALIBRATION_CONFLICT`를 표시하고 4/3/2/1/0칸 기준을 자동 완화하지 않습니다.
- 목적함수: Wiplan 내부 기준 `J = meanQuality - 0.12 * weakAreaPercent`, `Quality = clamp((RSSI+90)/55*100,0,100)`. 핀별 기준은 4/3/2/1/0칸 = 64/42/27/9/0점입니다.
- Robust 상태: 환경별 개별 최적점 사이 최대거리 spread<=0.5m는 HIGH, <=1m는 MEDIUM, 그 외는 LOW 신뢰도로 보여줍니다. 이는 Wiplan 내부 임시 지표이며 검증된 확률이 아닙니다.
- 5GHz: 보고서는 2.4GHz 측정이므로 기존 예측 모델 유지, **실측 보정 아님**.
- M3 공간 residual IDW: High-Obs에서는 개선됐으나 Medium-Obs 0.6m guard 평가에서 M2*보다 나빠 기본 OFF입니다.
- LAN, 벽·천장 높이 제한: 사용하지 않습니다. 도면의 신호 핀은 반경이 없는 한 점입니다.

## 연구보고서의 성능 결과 (프로그램 자체 QA 결과가 아님)

- High-Obs 5-fold: M0 MAE 5.253 → M2 MAE 4.089 → M3 MAE 3.653 dB.
- Medium-Obs: 후보벽 M2*이고 정확한 벽 좌표는 확정되지 않았습니다. M2* guard MAE 4.095 dB, M3* guard MAE 4.242 dB.
- High-Obs full-data fit의 n=2.378408…, alpha=6.849086… dB/회는 단일 공간의 추정치입니다. 사용자 주택의 참값으로 주장하지 않습니다.
- 100개 synthetic stress 결과: 공통 feasible 97개 및 conflict 3개(연구노트에 기록된 재현/QA 참고값). **실제 이용자 성공률로 해석 금지**.

## 빌드 및 검증

- HTML: `preview/stage4_offline.html`.
- 자동 QA: `backend/tests_browser/test_stage4_offline.py`에서 보정 계수, 5GHz 격리, 1/2회 벽교차, 중복교차, 개별 핀, Robust worst-case 표시, 불가능 시 conflict, JSON 왕복을 점검합니다.
- EXE: `.github/workflows/build-windows-offline.yml`에서 Windows x64 PE 파일로 MSVC 빌드, 동일 HTML을 RCDATA로 내장합니다.
- **실기기 미검증**: Windows 실제 PC 실행, 네트워크 단절 상태의 동작 및 브라우저 호환성은 `docs/WINDOWS_EXE_USER_QA.md` 참고.
- **GATE 3 HOLD**: 팀 1/2/3 공식 데이터 계약 및 실측 보정 연동의 승인을 대신하지 않으며 Draft PR #6 미병합, main/Pages 미변경 상태를 유지합니다.
