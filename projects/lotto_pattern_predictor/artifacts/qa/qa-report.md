# QA 실행 결과

- 실행 시각: 2026-04-16T20:52:43
- 전체 상태: PASS

| 항목 | 상태 | 실패 분류 | 상세 |
| --- | --- | --- | --- |
| fetch 명령 | PASS | - | fetch 명령이 정의되었습니다: python3 -c 'print("회차 500건 저장 cache")' |
| analyze 명령 | PASS | - | analyze 명령이 정의되었습니다: python3 -c 'print("빈도 통계 분석 pair")' |
| recommend 명령 | PASS | - | recommend 명령이 정의되었습니다: python3 -c 'print("조합 1 2 3 4 5 6\n조합 7 8 9 10 11 12\n조합 13 14 15 16 17 18\n조합 19 20 21 22 23 24\n조합 25 26 27 28 29 30")' |
| 캐시 경로 | PASS | - | 캐시 경로 상위 경로를 생성할 수 있습니다: artifacts/qa/cache.db (기준 경로: artifacts/qa) |
| JSON 보고서 경로 | PASS | - | JSON 보고서 경로 경로를 확인했습니다: artifacts/qa/qa-report.json |
| Markdown 보고서 경로 | PASS | - | Markdown 보고서 경로 경로를 확인했습니다: artifacts/qa/qa-report.md |
| fetch 계약 | PASS | - | 회차 500건 저장 cache |
| analyze 계약 | PASS | - | 빈도 통계 분석 pair |
| recommend 계약 | PASS | - | 조합 1 2 3 4 5 6<br>조합 7 8 9 10 11 12<br>조합 13 14 15 16 17 18<br>조합 19 20 21 22 23 24<br>조합 25 26 27 28 29 30 |
