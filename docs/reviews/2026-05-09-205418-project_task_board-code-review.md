# Code Review: project_task_board

> Source: core/project_task_board.py
> Date: 2026-05-09 20:54
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### Findings

1. [High] Owner drift details are returned but never recorded
   - File: `core/project_pipeline.py:1402`
   - Code: `if board_module and detect_owner_drift(board_module, board, task_map=task_map):`
   - Issue: `detect_owner_drift()` now returns `(task_id, expected_owner, actual_owner)` tuples, but the only caller still treats it as a boolean and discards the details. This fails the warning-registry migration described in `docs/2026-05-09-warning-registry-and-gate-escalation-design.md`: `owner_role_mismatch` should be recorded with `count=len(mismatches)`, `affected_ids`, and `extra["mismatches"]`.
   - Suggestion: Change the caller to assign `mismatches = detect_owner_drift(...)`; when non-empty, call `WarningRegistry(workspace=workspace).record(...)` with `rule_id="owner_role_mismatch"` before continuing.

2. [Medium] Warning registry write failure is silently downgraded to debug
   - File: `core/work_item_generator.py:1084`
   - Code: `except Exception as _e2e_exc:`
   - Issue: The new `e2e_command_missing` registry path catches all failures and only logs at debug. In normal runs, registry import/write/schema failures disappear, leaving only the old human log. This repeats the known “silent fallback hides real errors” pattern from the checklist.
   - Suggestion: Log this at warning level with context, or narrowly catch expected non-fatal exceptions. At minimum, make registry failure visible because it affects escalation data.

3. [Medium] New core modules are missing from frozen-build hiddenimports
   - File: `af.spec:33`
   - Code: `hiddenimports=[`
   - Issue: The change introduces `core/warning_registry.py` and `core/escalation_evaluator.py`, but `af.spec` was not updated. The project checklist explicitly calls out “af.spec missing: new core/*.py file not added to hiddenimports,” and the design doc also requires these two modules in hiddenimports.
   - Suggestion: Add `'core.warning_registry'` and `'core.escalation_evaluator'` to the `hiddenimports` list and verify a PyInstaller build.

### Comparison with Known Issues

- `docs/code_review/code-review.md` currently has no completed review for this warning-registry change; the latest entry says review was skipped.
- The change repeats two known checklist patterns: silent fallback around warning recording, and missing `af.spec` hiddenimports for new `core/*.py` files.
- The `detect_owner_drift()` helper change partially addresses the known owner-drift issue, but the caller migration is incomplete.

### Positive Observations

- `detect_owner_drift()` preserves truthiness compatibility: `[]` is falsy, so existing boolean-style callers do not crash.
- The returned tuple keeps useful diagnostic context: `task_id`, expected module owner, and actual task owner.