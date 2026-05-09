# Design Review: 2026-05-09-warning-registry-and-gate-escalation-design

> Source: docs/2026-05-09-warning-registry-and-gate-escalation-design.md
> Date: 2026-05-09 10:06
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [High] `approval-gate.md` link assumes workspace location, but current code writes gates under `doc_root`
   - Section: "`approval-gate.md 자체가 workspace 하위(`<workspace>/...projects/.../approval-gate.md` 등)에 있으므로, 링크 해석 시 workspace 루트 기준으로 `<workspace>/runtime/warnings/<slug>/_decision.md`를 가리킨다`"
   - Issue: This is false for `target_path`. `core/work_item_generator.py:959-1061` computes `doc_root` from absolute `project_brief["target_path"]` and calls `ApprovalGate(doc_root, slug)`. `PreparedProject.gate()` also uses `_effective_doc_root()` in `core/project_pipeline.py:87-95`. A plain `gate_decision_report: runtime/warnings/<slug>/_decision.md` inside an external target directory will not resolve to `<workspace>/runtime/warnings/...`.
   - Suggestion: Extend `ApprovalGate` to accept both `doc_root` and `runtime_workspace`, or inject an absolute path / correctly relativized path from gate file to warning file. Add a `target_path` test where `approval-gate.md` lives outside the AF workspace.

2. [High] CLI contract contradicts “workspace required, no cwd fallback”
   - Section: "`API 시그니처 ... WarningRegistry(workspace: str)`" and "`cwd fallback 금지`" vs "`python -m core.warning_registry summary --slug=<slug>`"
   - Issue: The CLI has no `--workspace` argument, but the registry explicitly forbids cwd/doc_root fallback. In frozen builds and multi-PC use, `cwd` is especially unreliable. Acceptance #2 and #10 cannot be implemented deterministically from only `--slug`.
   - Suggestion: Make CLI require `--workspace`, or define a single approved resolver such as `AF_WORKSPACE` with an explicit error when absent. Update acceptance to `python -m core.warning_registry summary --workspace=<workspace> --slug=<slug>`.

3. [High] Partial-write recovery is underspecified for project/global/index writes
   - Section: "`<project_slug>/<rule_id>.jsonl`, `_global/<rule_id>.jsonl`, `_index.json`, `_summary.json`" and "`registry record 호출은 try/except로 감싸 fire-and-forget`"
   - Issue: `record()` appears to update multiple files. If project jsonl append succeeds but global append, `_index.json`, or summary update fails, escalation data diverges. The design says `_global` is used for cross-project escalation 판단 and `_summary` for phase-aware decisions, but does not define which file is authoritative or how repair/rebuild works.
   - Suggestion: Declare `<slug>/<rule_id>.jsonl` as the source of truth, make `_summary.json` and `_global` rebuildable caches, and add a `repair/rebuild` path. Include an idempotency key such as `record_id` if retry can duplicate appends.

4. [Medium] `.gitignore` policy is not implementable as written for dynamic slugs plus committed `_index.json`
   - Section: "`runtime/warnings/<slug>/` — gitignore", "`runtime/warnings/_global/` — gitignore", "`runtime/warnings/_index.json` — commit 대상"
   - Issue: `.gitignore` cannot literally ignore `<slug>`. Current `.gitignore` has no `/runtime/` rule. A broad `/runtime/warnings/*` rule would also ignore `_index.json` and `.gitkeep` unless explicitly unignored.
   - Suggestion: Specify exact rules, for example:
     ```gitignore
     /runtime/warnings/*
     !/runtime/warnings/
     !/runtime/warnings/.gitkeep
     !/runtime/warnings/_index.json
     /runtime/warnings/_global/
     ```
     Then add a test or review checklist item that `_index.json` remains trackable.

5. [Medium] `detect_owner_drift()` return-shape change loses useful mismatch detail unless specified
   - Section: "`detect_owner_drift(...) -> list[tuple[str,str]]`로 변경 (mismatched task_id, task_owner 페어 목록 반환)"
   - Issue: The tuple omits expected module owner, so downstream records only show the wrong owner, not the expected owner. Current function in `core/project_task_board.py:227-249` has both `mod_owner` and `task_owner`; the design’s `affected_ids` also drops the pair structure.
   - Suggestion: Return `list[dict]` or `list[tuple[task_id, expected_owner, actual_owner]]`, and put structured mismatches in `extra["mismatches"]`. Keep `affected_ids` for quick task lookup only.

### Missing from Design

- A concrete path resolution test for `target_path` where work-item docs are outside the AF workspace.
- A rebuild/repair command for `_summary.json` and `_global` after partial registry failures.
- Required CLI workspace resolution for source mode and frozen `dist/af/af.exe`.
- Exact `.gitignore` patterns preserving committed `_index.json`.
- Tests covering Windows absolute paths and path separators for `source_path`, `gate_decision_report`, and `WarningRegistry(workspace=...)`.

### Positive Observations

- The design correctly grounds `affected_phase` in `core/project_task_board.py:_PHASE_ORDER`, avoiding silent policy drift from invented phases.
- The `evidence_quality_warn` migration was placed at `core/project_pipeline.py` instead of `core/research_verifier.py`, which matches the current caller context where `slug` and `target_workspace` are available.