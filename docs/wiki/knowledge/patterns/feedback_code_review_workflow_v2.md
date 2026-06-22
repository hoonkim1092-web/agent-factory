---
name: Code Review Workflow v2 (2026-05-13)
description: Review-first pattern — af-critic → af-cross-review → af-test-runner for .py files. Max 5 rounds auto fix-loop.
type: feedback
originSessionId: 9ba41419-7b0d-44f3-ba7f-8f5a3641f82f
---
## 새 워크플로우 순서 (2026-05-13 확정)

**코드 (.py) 수정 시**:
1. af-critic (중간) → BLOCK이면 수정
2. af-cross-review (가벼움) → BLOCK이면 수정
3. af-test-runner (비쌈) → BLOCK이면 수정

**자동 fix-loop**: 각 단계에서 최대 5라운드까지 자동으로 반복. 5라운드 후 계속 BLOCK이면 사용자 결정.

**설계문서 (.md) 시**:
- af-cross-review만 실행
- BLOCK 반복 시 **무조건 사용자에게 안내** (자동 고정 금지)

**Why**: 
- Review-first가 수정 사이클을 리뷰에 묶어서 테스트는 마지막 1번만 실행 (효율)
- "옳은 코드인가" 먼저 확인 → 사람 PR 워크플로우와 정합
- Hook 레벨에서 이미 py_compile 체크하므로 fail-fast 여전히 보장
- 5라운드는 일반적인 코드 수정 반복 범위 (과한 자율 방지)

**How to apply**:
- 코드 수정 후 commit하면 hook이 자동으로 3-tier 순서 실행
- CLAUDE.md § "Review-Gate 규칙" 참조
