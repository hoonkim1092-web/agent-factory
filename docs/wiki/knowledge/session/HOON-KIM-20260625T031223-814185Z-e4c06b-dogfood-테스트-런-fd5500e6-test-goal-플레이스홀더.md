---
id: "session/HOON-KIM-20260625T031223-814185Z-e4c06b-dogfood-테스트-런-fd5500e6-test-goal-플레이스홀더.md"
type: "session"
scope: "project"
title: "dogfood 테스트 런 fd5500e6: 'test goal' 플레이스홀더 입력 → work-item 생성"
author: "HOON-KIM\\HOON"
source_machine: "HOON-KIM"
created_commit: "e245fb14"
created_at: "2026-06-25T12:12:23+09:00"
visibility: "private"
links: []
---

dogfood 테스트 런 fd5500e6: 'test goal' 플레이스홀더 입력 → work-item 생성기가 WI-0 BLOCKER를 올바르게 발화했고, af-critic이 사실검증 역할로 해당 아티팩트를 평가함. HEAD는 e245fb14(STAGE R 설계 완료, 구현 대기).

## 결정 (Decisions)
- WI 생성 시 goal='test goal' 플레이스홀더를 감지하면 WI-0을 BLOCKER로 첫 번째 항목으로 삽입하는 방어 패턴을 유지한다 — 하위 WI들은 WI-0 sign-off 전까지 blocked_on_WI-0 상태로 고정됨.
- af-critic을 fact-checker 역할로 work-item 아티팩트에 투입하는 구성을 dogfood 테스트 fd5500e6에서 실행했다.
- dogfood 테스트 worktree 경로는 tests/_tmp/af-test-fd5500e6 (HEAD e245fb14 기준) — PC 로컬 저장, git 동기화 대상 아님.
- HEAD e245fb14: STAGE R(retrieval) 상세 설계 + cross-review 흡수 완료. 다음 단계는 STAGE R 구현(Sonnet).

## 기각 (Rejections)
- requested_role='' (빈 문자열) 상태로 WI-1 이하 진입 허용하지 않음 — WI-0 acceptance_criteria에 명시적 차단 조건으로 기록됨.
- route={} (빈 객체) 상태로 implementation 단계 진입 허용하지 않음 — 최소 1개 유효 route entry 필수 조건 하드게이트.
- Windows R1 11차 dogfood run 1779867851-3611529e 는 PC 핸드오프 식별자 미기록으로 산출물 회수 불가 — 해당 사례를 반복하지 않기 위해 Dogfood Run PC 핸드오프 규칙 유지.

## 패턴 (Patterns)
- 플레이스홀더 감지 → BLOCKER WI 자동 삽입: goal이 평가 불가능한 문자열이면 하위 작업 전체를 blocked 체인으로 직렬화하고 3영업일 타임박스 + 취소 조건을 명시하는 패턴.
- dogfood 테스트는 tests/_tmp/af-test-<short_hash> 경로에 격리 worktree로 실행 — 커밋 `e245fb14`, `e3c0fca7`, `a02e109d`, `c1d5ecb7`, `eacd67dc`(`d75f3c49` 참조) 모두 해당 브랜치의 최근 이력.
- af-critic은 시스템 프롬프트를 fact-checker(evidence grounding / unsupported claims / alternatives / recency) 형식으로 받아 JSON 점수 산출 — 설계 문서·work-item 양쪽에 동일 패턴 적용 가능.
- STAGE R 설계(ADR `20260513` 명명 규칙 기반)는 cross-review 흡수 후 `e245fb14`에 확정 커밋 — 구현 진입 전 설계 동결 패턴.

## 정밀 참조 (verbatim, INV-K5)
- `fd5500e6`
- `1779867851`
- `3611529e`
- `20260513`
- `e245fb14`
- `e3c0fca7`
- `a02e109d`
- `c1d5ecb7`
- `eacd67dc`
- `d75f3c49`

## raw 포인터 (§3.3 — 원문은 originating PC 에만)
- originating_pc: HOON-KIM
- session_file: D:/hoonProJect/worktrees/agent-factory/tests/_tmp/af-test-fd5500e6/.af_runtime/codex_home/sessions/2026/06/25/rollout-2026-06-25T12-11-27-019efcc2-d3e5-7253-a2df-3983a7dadb65.jsonl
- lines: 3-5
