# Design Review: 2026-05-21-af-dogfooding-infrastructure-gap-analysis

> Source: docs/2026-05-21-af-dogfooding-infrastructure-gap-analysis.md
> Date: 2026-05-21 11:58
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: WARN

### Findings

1. [High] Agent order fix is scoped too narrowly
   - Section: “판정 1 (review-first 정책): check_pending_review.py:51,56,60 순서 뒤집기 + _agents_for_tier 시그니처 갱신 + 회귀 테스트”
   - Issue: The design only names `scripts/check_pending_review.py`, but the same test-first order is also hard-coded in `scripts/blast_radius.py:194-207`, `scripts/hook_runner.py:317-320`, `scripts/review_gate.py:535-538`, and `.githooks/pre-commit:65`. If only `_agents_for_tier()` is changed, commit-block messages and helper APIs will still instruct `af-test-runner → af-critic → af-cross-review`.
   - Suggestion: Define one canonical order source, or explicitly update all user-facing/caller sites: `check_pending_review.py`, `blast_radius.required_agents()`, `hook_runner._pre_bash_review_gate()`, `review_gate._cli()`, and `.githooks/pre-commit`. Add regression tests for emitted instruction strings.

2. [High] T3-skip order change has an untested state-transition risk
   - Section: “check_pending_review.py:56 t3_skip 분기 … review-first 채택 시: `af-critic → af-test-runner`”
   - Issue: Current T3 skip depends on `scripts/review_gate.py:_required_tiers_for()`: before `af-critic` records advisory it can require `[1,2]`; after `af-critic` records anything except `t3_required=no`, it can expand back to `[1,2,3]` and `record_review_done()` clears `fired_at`. The design does not specify the expected prompt sequence when `af-critic` runs first and changes the required tier set.
   - Suggestion: Add acceptance tests for all three advisory paths: `t3_required=no`, `yes`, and `unknown`. Verify that `check_pending_review.py` re-prompts for `af-cross-review` when advisory expands the required tiers.

3. [Medium] G2 violates the document’s own “grep proof” rule
   - Section: “G2 | `.codex/hooks.json` cli_hook_bridge 2중 등록 | NEXT_STEPS P2-F memory | 유효 (낮음)”
   - Issue: This row uses stale memory as evidence, while §5 says “메모리/NEXT_STEPS 인용 시 grep 1차 반증 의무”. Current `.codex/hooks.json` does show paired `scripts/run.py cli_hook_bridge` and direct `scripts/hook_runner.py cli_hook_bridge` entries for `PreCompact`, `SessionStart`, `UserPromptSubmit`, and `Stop`, but the design does not distinguish intentional compatibility duplication from a bug.
   - Suggestion: Replace the memory citation with current line evidence and define the invariant: either one bridge command per event, or two allowed commands with documented dedupe behavior.

4. [Medium] Renormalize plan may not be permanent
   - Section: “Step 1 — G6 dirty YAML renormalize … `git add --renormalize projects/agent_factory/` # 1회로 영구”
   - Issue: `.gitattributes` already has `*.yaml text eol=lf`, yet `projects/agent_factory/*.yaml` are dirty. `git diff --check` reports trailing whitespace/embedded CR noise across those files, not just ordinary line-ending normalization. A one-time `git add --renormalize` may stage churn but does not identify the writer that reintroduces CRLF/CR padding on Windows.
   - Suggestion: Add a source investigation step: identify the generator/writer for `projects/agent_factory/{agents/*.yaml,context_schema.yaml,settings.yaml,workflow.yaml}` and enforce LF/trim at write time. Then run a second-session verification.

5. [Medium] R1 self-run experiment lacks rollback and provider-failure handling
   - Section: “Step 3 — R1 .py self-run 실험 설계 … 별도 worktree … AF_DISABLE_REGISTRY_WRITE=1 … allowed_paths=[\"core/utils.py\"] report-only”
   - Issue: The experiment uses real providers and only a report-only scope guard. It does not define what happens if the provider is unavailable, partially edits files outside the allowlist, writes registry/runtime artifacts, or times out. This is exactly the failure mode the Agent Factory context warns about: real repo mutation, multi-PC paths, and provider CLI side effects.
   - Suggestion: Require a pre-run rollback point, post-run `git diff --name-only` allowlist check that fails the experiment on leaks, cleanup rules for `.af_review_queue`/runtime artifacts, and provider-unavailable skip criteria.

### Missing from Design

- Explicit caller/callee update list for Step 0(b), including `scripts/blast_radius.py`, `scripts/hook_runner.py`, `scripts/review_gate.py`, and `.githooks/pre-commit`.
- Windows-specific validation for file locks: `review_gate._state_lock()` is no-op on Windows, so concurrent `check_pending_review`/`record_review_done` behavior needs coverage.
- Frozen build impact statement: likely no `af.spec` update if only `scripts/*.py`/docs change, but the design should say that explicitly.
- Concrete tests: agent order emission, max-round cap behavior, T3-skip expansion, CRLF regression, and R1 scope leak.

### Positive Observations

- The G/R split is useful and maps to real entrypoints: `.githooks/pre-commit → scripts/review_gate.py` vs `agent_launcher.py --workspace`.
- The document correctly rejects the stale `review_gate.py:214 round_count<2` claim and points to the current implementation in `scripts/check_pending_review.py:135`.