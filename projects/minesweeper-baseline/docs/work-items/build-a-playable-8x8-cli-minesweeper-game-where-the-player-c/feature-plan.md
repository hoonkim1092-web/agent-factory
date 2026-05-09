`feature-plan.md`를 `/Users/hoon/workTree/agent-factory/projects/minesweeper-baseline/feature-plan.md`에 생성했습니다. 배경·목표·범위·리스크·증거·승인 체크리스트를 한국어로 구조화했으며, 역할별 인터페이스 모호 문제와 safe-first-click 리스크를 명시적으로 포함했습니다.
## Episode Hints

_과거 유사 프로젝트에서 학습된 주의사항:_

- stub-only 테스트는 실제 기능 존재를 보장하지 않는다 — e2e_command 필수
- e2e_command가 `needs_backfill`인 태스크는 PASS 처리 불가
- 테스트 작성 시 최소 1개의 실제 실행 경로(비mock)를 포함해야 한다
- approval-gate `status=completed` = 파일 존재 + 금지토큰 0 + e2e exit 0 모두 충족
- 라이브러리 함수명 발명 금지: 항상 공식 문서에서 확인된 API만 사용한다
- mock 전용 테스트는 실제 import 오류를 잡지 못한다 — 최소 1개 실행 테스트 필요
- Level 1 retry에서 같은 패턴이 반복되면 pivot(Level 2)으로 즉시 에스컬레이션
- 존재하지 않는 심볼 사용 시도가 감지되면 작업 전 경고 로그를 주입한다
