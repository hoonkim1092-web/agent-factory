# Design Review: 2026-05-14-question-router-detailed-design

> Source: docs/2026-05-14-question-router-detailed-design.md
> Date: 2026-05-14 14:41
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] `paused_hitl` cannot stop Stage 1-3 where the design inserts Stage 0
   - Section: "`generate_work_items()` 반환 타입은 **`dict[str, str]` 그대로 유지**. paused 상태는 **`ApprovalGate.is_execution_open()` 채널**로 흘림."
   - Issue: The proposed insertion point is `core/work_item_generator.py:1094`, before Stage 1, but `ApprovalGate` is not created until `core/work_item_generator.py:1238`, after Stage 1-3 have already generated plan/spec/tasks. `core/project_pipeline.py:963-1020` also runs `plan_verifier` and structural gate immediately after `generate_work_items()` returns, before any `gate.is_execution_open()` check. The design claims paused HITL skips plan/structural/cross-review, but the current caller path does not support that.
   - Suggestion: Make Stage 0 return a typed status to `generate_work_items()` and stop Stage 1-3 on `paused_hitl`/`block`, or move approval-gate initialization before Stage 0 and add an explicit `project_pipeline` check immediately after `generate_work_items()`.

2. [High] LLM adapter code does not match the real `CliChatRequest` API
   - Section: "`req = CliChatRequest(provider_id=self._provider, messages=[...], timeout_sec=int(timeout_sec), response_format={\"type\": \"json\"})`"
   - Issue: `core/providers/cli.py:31-39` defines `CliChatRequest(provider_id, model, system_prompt, task_input, workspace, run_id='', timeout_sec=0, auto_approve=False)`. There is no `messages` field and no `response_format` field. Implementing the design literally will raise `TypeError`.
   - Suggestion: Rewrite §6.1 to use the actual constructor: `model`, `system_prompt`, `task_input`, `workspace`, and `timeout_sec`. If JSON output is required, encode it in `system_prompt`/`task_input` or extend `CliChatRequest` explicitly and update all providers/tests.

3. [High] ApprovalGate matrix is internally inconsistent and still references invalid blast-radius tokens
   - Section: "`v2 보정: isolated|module|cross_module|system_wide`" and later "`unit test: NEEDS_ADR × {local, module, system_wide, security, data} 5케이스`"
   - Issue: The design correctly says valid tokens are `isolated`, `module`, `cross_module`, `system_wide`, matching `core/control/change_impact.py:16,35` and tests in `tests/test_approval_gate_domain_review.py`. But §9.8 still requires tests for `local`, `security`, and `data`, which existing tests explicitly forbid. This will create contradictory implementation targets.
   - Suggestion: Replace §9.8 with `NEEDS_ADR × {isolated, module, cross_module, system_wide}` plus separate `BlockCause` tests for `POLICY_VIOLATION`/`SAFETY`.

4. [High] Proposed `cross_module` domain gate is not fully specified against the current outer condition
   - Section: "`NEEDS_ADR` ... `cross_module`/`system_wide` pause" and code says add logic around `core/approval_gate.py:240~250`.
   - Issue: Current `core/approval_gate.py:233` only enters the domain-review gate when `blast_radius == "system_wide"`. The design snippet changes verdict handling inside that block but does not explicitly change the outer condition to include `cross_module`. If implemented as written, `NEEDS_ADR + cross_module` will still skip the domain gate.
   - Suggestion: Specify the outer condition as `blast_radius in ("cross_module", "system_wide")`, then define whether `PASS` also requires `domain-review.md` for `cross_module`.

5. [Medium] Schema hash meaning conflicts between artifacts and drift detection
   - Section: "`artifact 4종 dataclass ... schema_version + schema_hash 필수`" and "`ContextScanArtifact.schema_hash: raw markdown SHA-256`" versus "`AssumptionLedgerEntry.schema_hash: QuestionRouter.schema_hash`"
   - Issue: §4.2 drift detection compares previous question-schema hash to current question-schema hash. But §5.1 defines artifact `schema_hash` as rendered markdown hash, not question schema hash. That makes the same field name mean two different things and will break resume/drift logic if consumers treat it uniformly.
   - Suggestion: Split fields: `question_schema_hash` for router schema drift and `content_hash` for rendered artifact integrity.

6. [Medium] RunLedger helper design omits fields required by later scenarios
   - Section: "`append_paused_hitl(... metadata={\"event\":\"paused_hitl\", \"question_ids\":..., \"work_dir\":..., \"report_required\": True})`" and later "`run_ledger: {\"event\":\"paused_hitl\", ..., \"schema_hash\":...}`"
   - Issue: §8.3 requires `schema_hash` for resume drift detection, but §7.3 helper does not write it. Also `append_assumption()` takes `AssumptionLedgerEntry`, but `core/control/run_ledger.py` currently has no dependency on Stage 0 artifact types; this new import direction should be stated.
   - Suggestion: Add `schema_hash`, `work_kind`, `blast_radius`, and `question_schema_version` to paused/assumption metadata. Keep `RunLedger` accepting plain dicts or define event payload types in `run_ledger.py` to avoid hidden coupling.

### Missing from Design

- Exact `ProjectPipeline` resume hook location. The doc says "`start_run()` 또는 동등한 진입 메서드", but current code path shown around `core/project_pipeline.py:963` needs a concrete method and branch.
- How `ApprovalGate` is created before Stage 0 if `paused_hitl` uses gate state.
- Real `CliChatRequest` constructor compatibility.
- Tests proving `plan_verifier` and structural gate are skipped during `paused_hitl`.
- Clear ownership for ADR auto-creation: §10.2 says `work_item_generator` triggers it, but the current `ApprovalGate.approve()` is where verdict decisions happen.

### Positive Observations

- The design correctly verifies the real blast-radius taxonomy from `core/control/change_impact.py`.
- It explicitly includes `af.spec` hiddenimports and frozen-build smoke testing for the new `core/control/*.py` modules, which matches Agent Factory deployment constraints.