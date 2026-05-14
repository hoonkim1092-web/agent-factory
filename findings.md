# Findings

## Document Set

- Target folder: `docs/codex_논의`
- Files analyzed: 6 markdown documents dated 2026-05-11 to 2026-05-13.
- Main arc: pipeline/AST review -> AST revival -> graph/memory evolution -> Graphify diagnosis -> market/competitor synthesis -> provider-neutral knowledge layer.

## Verified Observations

- `core/ast_engine.py` is only used through `core/review_bundle.py` in the searched code paths. It is not exposed as a normal agent execution tool.
- `core/ast_memory_hub.py` has `subscribe()` and `publish()`, but searched production calls show no `AstMemoryHub.subscribe(...)` consumer. Generic `.subscribe()` hits include unrelated message broker code.
- `dynamic_orchestrator.py` currently does update AST state with real changed file paths via `_git.diff_files_since(_pre_task_sha)` on normal success and FSA success. This means the older "fake filepath only" diagnosis has been partially fixed in the current code.
- `update_ast_state()` still defaults to `parsed_ast_data or "AST_TREE_MOCK"`, and current calls do not pass parsed AST data.
- Graphify wrapper exists, but metadata still marks `last_test_ok: false` and requires Python `<3.14`; docs also describe graphify as needing Python 3.13 isolation.
- Provider session bridge has provider configs for codex, claude, and gemini sessions, but the provider-neutral canonical memory layer described in the latest design is still a design target rather than a completed layer.

## Judgment

- The document set's diagnosis is directionally strong: AF has many advanced subsystems, but several are not wired into decision-time context.
- The biggest practical leverage is not adding more tools; it is closing loops: observe -> score -> consolidate -> retrieve.
- The latest provider-neutral Knowledge Operating Layer is the right north-star, but it is too broad to implement as one feature. It should be cut into narrow, measurable phases.

## Superpowers / GSD Follow-up

- Read 10 named workflow skills: brainstorming, systematic-debugging, verification-before-completion, writing-plans, test-driven-development, requesting-code-review, receiving-code-review, using-git-worktrees, finishing-a-development-branch, dispatching-parallel-agents, subagent-driven-development.
- `docs/codex_논의/2026-05-13-superpowers-11-skills-quality-verification.md` is useful but currently BLOCKed by its own design review. Major issues: wrong file references (`core/project_planning_director.py` absent; `ProjectPlanningDirector` is in `core/bootstrap_roles.py`), wrong AgentSpecializer cap claim (8, not 12), stale memory wire-up claim, and missing contracts for `domain-review.md` and verification wiring.
- Current AF has many GSD/Superpowers primitives already: `context_fork.py`, `semantic_embedder.py`, `skill_eval_harness.py`, `skill_preflight.py`, `mcp_adapter.py`, `parallel_critique.py`, `approval_gate.py`, `review_gate.py`, `AgentSpecializer`.
- The real GSD gap is not primitives; it is explicit workflow contract: PlanChecker, Goal-backward Verifier, UAT.md, and gap-replan loop.
- Recommended absorption split: implement/strengthen brainstorming, systematic-debugging, verification-before-completion, TDD-red checks, worktree isolation policy; do not import Superpowers directly. Keep AF-native review/orchestration, but expose them as named phases.
