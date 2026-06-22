---
name: feedback_workflow_agent_review_gate_gap
description: Workflow/Agent 도구로 spawn한 3-Tier는 review-gate state 미기록 → 커밋 시 stale-review BLOCK
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 67073823-e684-4b49-ba89-a793d035ec09
---

Workflow 도구나 Agent 도구로 af-critic/af-cross-review/af-test-runner를 spawn하면 검증은 실질적으로 수행되지만, 정식 `enqueue_agent_review` hook 경로를 거치지 않아 `pending_agent_review.json` review-gate state에 기록되지 않는다. 그 결과 `core/*.py`(Tier 2/3) 커밋 시 pre-commit hook이 `BLOCK: stale-review`로 막는다. (2026-06-01 고리③ 배선 수리 커밋에서 발생.)

**Why:** review-gate는 hook 기반 enqueue→record 흐름으로 3-Tier 완주를 추적한다. 직접 spawn한 agent는 이 흐름 밖이라 게이트 입장에선 "review 없음 = stale".

**How to apply:** Tier 2/3 파일을 Workflow/Agent로 3-Tier 돌려 커밋할 때 — (a) 실질 완주(BLOCK 0)를 근거로 `AF_SKIP_REVIEW_GATE=1 git commit` 우회(hook_events.log에 감사 기록됨), 또는 (b) 정식 게이트 경로로 재실행해 state 기록. 검증이 실제로 끝났고 이후 변경이 기능 무변(dead-code/문서)이면 (a)가 합리적. 또 Workflow/Agent에 구현을 위임할 때 "Blueprint 건드리지 말 것" 지시를 줘도 agent가 어기고 수정+`git add`할 수 있으니 커밋 전 `git status`로 staged 정확성·환각 기록을 반드시 검수. [[feedback_review_gate_hook]] [[feedback_commit_staging_hygiene]] 참조.
