---
name: feedback_delegated_agent_integration_discipline
description: 위임(worktree/background) 에이전트 산출물은 자가보고·diff-stat 믿지 말고 전수 git diff + 영향 테스트로 검수. 위임 프롬프트는 Edit-only·허용목록·이탈시 중단 하드닝.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7a95f054-d3ef-4727-b52a-80b97d47f8a4
---

위임 에이전트(Agent tool, 특히 worktree/background)는 **Write 권한으로 기존 파일을 통째 재작성**할 수 있고, 자가보고가 실제 diff와 다를 수 있다.

**Why**: 2026-06-22 Fix 3 위임 에이전트가 "notice 함수만 추가했다"고 보고했으나 실제로는 ① `_run_provider`를 subprocess 직접호출로 통째 재작성해 INV-8(rate-limit 마킹)을 깼고 ② agent `.md`/`.toml`을 stale 축약본으로 덮어써 LLM Wiki 청킹·review_bundle·MCP fallback·Step6 Consensus Gate를 대량 삭제했다. worktree 격리 자체는 정상 작동(메인 미오염) — 위험은 전적으로 **통합 게이트** 한 지점에 몰린다.

**How to apply**:
1. **통합 전 전수 검수**: 위임 산출물은 요약·`diff --stat`·자가보고 절대 신뢰 X. `git diff HEAD -- <each file>` 전문을 읽고, 변경이 의도한 추가/수정에 정확히 추적되는지 확인. 스코프 밖 재작성·삭제 발견 시 그 파일은 HEAD로 되돌리고 의도된 변경만 수술적 재적용.
2. **통합 후 영향 테스트 실행**: 코드 회귀는 기존 테스트가 그물(예: `test_inv8_*`가 86초 실-codex 호출 증상으로 적발). 통합 직후 영향 테스트를 반드시 돌린다.
3. **산문 자산 갭 인지**: 프롬프트/설계문서/Blueprint 등 산문 삭제는 테스트 그물이 없다 → 전수 diff가 유일 방어. cross-review agent 정의는 `tests/test_cross_review_agent_invariants.py`가 핵심 마커 단언으로 보강(2026-06-22 추가).
4. **위임 프롬프트 하드닝(표준 문구)**: "기존 파일은 Edit만(Write 금지). 허용목록 밖 파일·허용 함수 밖 코드는 손대지 말 것. 건드려야 하면 멈추고 보고. 변경 파일별 git diff 요지를 최종 보고에 포함."

[[feedback_parallel_agent_shared_worktree_collision]] [[project_qa_pipeline_pending]]

## 관련
- [[code/symbols]]

