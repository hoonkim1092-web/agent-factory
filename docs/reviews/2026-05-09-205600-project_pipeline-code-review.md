# Code Review: project_pipeline

> Source: core/project_pipeline.py
> Date: 2026-05-09 20:56
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### Findings

1. [High] Split-root approval checks are not propagated to maintenance execution
   - File: `core/control/maintenance_pipeline.py:310`
   - Code: `gate = ApprovalGate(self._workspace, slug)`
   - Issue: `ApprovalGate` now supports separate document root and runtime workspace, and `PreparedProject.gate()` passes `runtime_workspace=self.workspace`. This maintenance caller still assumes the gate lives under `self._workspace`. For work-items generated with `project_brief["target_path"]`, the gate is under `doc_root/docs/work-items/...`, so maintenance approval checks will look in the wrong directory and block valid approved work.
   - Suggestion: Derive `doc_root` from `prepared["doc_root"]` / `prepared.doc_root` when available, and call `ApprovalGate(doc_root, slug, runtime_workspace=self._workspace)`.

2. [High] `gate_decision_report` is duplicated on every approval/invalidation render
   - File: `core/approval_gate.py:355`
   - Code: `f"{review_notes}\n{decision_report_line}"`
   - Issue: `_parse()` returns the entire Review Notes body, including the previous `- gate_decision_report: ...` line. `approve()`, `invalidate()`, and `apply_verification_verdict()` pass that back into `_render()`, which appends another decision report line. Repeated edit/reapprove cycles will accumulate duplicate links and noisy gate files.
   - Suggestion: Normalize review notes before rendering: remove existing `gate_decision_report:` lines, then append exactly one current link.

3. [Medium] New owner-drift details are still discarded by the only caller
   - File: `core/project_pipeline.py:1402`
   - Code: `if board_module and detect_owner_drift(board_module, board, task_map=task_map):`
   - Issue: `detect_owner_drift()` now returns `list[tuple[str, str, str]]`, but the caller still treats it as a boolean and throws away the mismatch details. This leaves the warning-registry migration incomplete: no `owner_role_mismatch` record gets written with `count`, `affected_ids`, or `extra["mismatches"]`.
   - Suggestion: Assign `mismatches = detect_owner_drift(...)`; when non-empty, record `WarningRegistry(workspace=workspace).record(rule_id="owner_role_mismatch", ...)` before continuing.

4. [Medium] Approval gate links to a report file that is never produced
   - File: `core/approval_gate.py:350`
   - Code: `self.runtime_workspace, "runtime", "warnings", self.slug, "_decision.md"`
   - Issue: The rendered gate now points reviewers to `_decision.md`, but `WarningRegistry` writes JSONL records and `_summary.json`; I found no writer for `_decision.md`. The approval gate can therefore advertise a non-existent decision report, weakening the review workflow.
   - Suggestion: Either render the existing `_summary.json` path, or add an atomic `_decision.md` writer in `WarningRegistry.summarize()` / a dedicated report generator.

### Comparison with Known Issues

- The change partially addresses the known split `doc_root` vs runtime workspace issue described in the warning-registry design notes.
- It also repeats a known pattern from prior reviews: caller migration is incomplete after changing helper semantics (`detect_owner_drift()` now returns details, but `project_pipeline` still uses boolean-only behavior).
- `docs/code_review/code-review.md` also calls out approval-gate correctness as an important control-plane area; this change touches that path but lacks idempotency and cross-caller coverage.

### Positive Observations

- `PreparedProject.gate()` now preserves the correct split-root intent by using `_effective_doc_root()` for work-item files and `self.workspace` for runtime warnings.
- `ApprovalGate.__init__` keeps the existing `workspace=` keyword compatible and adds `runtime_workspace` as keyword-only, avoiding the earlier documented rename breakage.