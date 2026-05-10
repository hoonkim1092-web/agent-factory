# Code Review: work_item_generator

> Source: core/work_item_generator.py
> Date: 2026-05-09 20:57
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### Findings

1. [High] Unknown task phases are coerced into `build`, causing false escalation
   - File: `core/work_item_generator.py:1069`
   - Code: `if _ph not in _e2e_phase_order:`
   - Issue: Any malformed or future phase from the task board is rewritten to `build` at line 1070. P2 policy treats `build` `e2e_command_missing` as blockable, so a typo like `buld` or a future phase can become a false build-phase BLOCK instead of an unknown-phase diagnostic.
   - Suggestion: Do not pre-coerce here. Pass the raw phase to `WarningRegistry.record()` and preserve unknowns in `extra={"original_phase": _ph}`; or record unknown phases with `affected_phase=""` / a dedicated non-escalating rule.

2. [High] Warning persistence failures are hidden from the prepare flow
   - File: `core/work_item_generator.py:1084`
   - Code: `except Exception as _e2e_exc:`
   - Issue: Import, lock, path, JSONL, and filesystem failures are all swallowed and only logged at debug level. That means the user still gets work items, but the P1/P2 warning registry can silently miss `e2e_command_missing`, making escalation blind.
   - Suggestion: Catch only expected optional-path errors, log at warning level with `exc_info=True`, and surface a degraded warning in the returned files/telemetry. If registry persistence is required for this path, fail the prepare stage.

3. [Medium] Dynamic import is not covered by frozen-build hiddenimports
   - File: `core/work_item_generator.py:1062`
   - Code: `from core.warning_registry import WarningRegistry as _WR`
   - Issue: `af.spec` includes `core.work_item_generator` but not `core.warning_registry`; the project checklist explicitly flags new `core/*.py` modules missing from hiddenimports. In PyInstaller builds, this dynamic import can fail only in `dist/af/af.exe`, and finding #2 will hide it.
   - Suggestion: Add `'core.warning_registry'` and related evaluator modules used by this package, such as `'core.escalation_evaluator'`, to `af.spec` hiddenimports and run a frozen smoke test.

4. [Medium] Approval gate points to a decision report that has no writer
   - File: `core/approval_gate.py:350`
   - Code: `decision_report_path = os.path.join(`
   - Issue: The changed generator now passes `runtime_workspace` into `ApprovalGate`, which causes every gate to render `runtime/warnings/<slug>/_decision.md`. I found JSONL and `_summary.json` writers in `WarningRegistry`, but no `_decision.md` writer. Reviewers will be directed to a non-existent report.
   - Suggestion: Either render the existing `_summary.json` path, or add an atomic `_decision.md` report writer and call it before `approval-gate.md` is initialized.

### Comparison with Known Issues

- This change partially addresses the known warning-registry direction by recording `e2e_command_missing` per phase instead of only logging it.
- It repeats known AF patterns: hidden frozen-build imports, silent fallback around warnings, and phase normalization that can distort escalation behavior.
- The `ApprovalGate(doc_root, slug, runtime_workspace=workspace)` call correctly addresses the known doc-root/runtime-root split, but the linked report target is not yet produced.

### Positive Observations

- The warning records are grouped by phase, which is the right shape for phase-aware escalation.
- The generator uses `runtime_workspace=workspace`, preserving external `target_path` work-item placement while keeping runtime warnings under the AF workspace.