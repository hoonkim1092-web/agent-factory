# QA Build Report

## 문서 목적
- QA Engineer `build` 단계에서 준비한 검증 자산의 실행 결과를 기록하는 템플릿이다.
- 실제 검증 수행 후 PASS/FAIL 상태와 재현 절차를 채운다.

## 실행 메타데이터
- 실행 일시:
- 실행자:
- 기준 작업: `qa_engineer_module_7_build_2`
- 결과 JSON: `artifacts/qa/qa-report.json`

## 실행 명령
```bash
python3 scripts/run_qa_checks.py \
  --report-json artifacts/qa/qa-report.json \
  --report-markdown docs/work-items/동행복권-api에서-최근-500회차-로또-당첨번호를-수집-통계-분석하여-가중-랜덤-기반-1등-후보-5조합을/qa-build-report.md \
  --fetch-cmd "<fetch command>" \
  --analyze-cmd "<analyze command>" \
  --recommend-cmd "<recommend command>"
```

## 슬라이스별 결과
| 슬라이스 | 상태 | 실패 분류 | 메모 |
| --- | --- | --- | --- |
| 사전 조건 점검 | PENDING | - | |
| 모듈 계약 검증 | PENDING | - | |
| 종단간 회귀 검증 | PENDING | - | |

## 재현 절차
1. CLI 엔트리포인트와 캐시 경로를 확정한다.
2. 상단 실행 명령의 placeholder를 실제 값으로 대체한다.
3. 실행 후 생성된 JSON 보고서와 표준 출력 로그를 함께 검토한다.

## 잔여 리스크
- 실제 Backend Dev 산출물이 아직 연결되지 않았으면 실행 결과는 `환경 문제`로 분류될 수 있다.
- 네트워크 의존 `fetch` 검증은 외부 API 상태에 따라 불안정할 수 있다.
