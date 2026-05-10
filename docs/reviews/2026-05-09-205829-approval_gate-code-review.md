# Code Review: approval_gate

> Source: core/approval_gate.py
> Date: 2026-05-09 20:58
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: WARN

### Findings

1. [Medium] Generated decision-report line is not idempotent
   - File: `core/approval_gate.py:355`
   - Code: `f"{review_notes}\n{decision_report_line}"`
   - Issue: `_parse()` reads the existing generated `- gate_decision_report: ...` line back into `review_notes`, and every re-render path (`approve`, `invalidate`, `apply_verification_verdict`) appends another generated line. A normal initialize → approve → invalidate flow can accumulate duplicate report links.
   - Suggestion: Strip existing `gate_decision_report` lines before appending, or parse/render this as a dedicated field outside user-authored review notes.

2. [Medium] Approval gate links to `_decision.md`, but the registry does not create it
   - File: `core/warning_registry.py:188`
   - Code: `return summary`
   - Issue: `ApprovalGate` now always renders `<runtime_workspace>/runtime/warnings/<slug>/_decision.md`, but `WarningRegistry.summarize()` only writes `_summary.json`. I found no writer for `_decision.md`, so freshly generated gates advertise a dead review artifact.
   - Suggestion: In `summarize()`, write a minimal `_decision.md` atomically next to `_summary.json`, or only render the gate link after that file exists.

3. [High] Verification handoff caller loses the runtime workspace in split-doc mode
   - File: `scripts/verify_handoff_checker.py:104`
   - Code: `gate = ApprovalGate(workspace, slug)`
   - Issue: The new constructor separates document root from runtime workspace, but this caller reconstructs `workspace` from the report’s work-item directory and omits `runtime_workspace`. For target-path/split mode, a verification BLOCK re-render will point `gate_decision_report` under the doc root’s `runtime/warnings`, not the AF runtime workspace where warning records live.
   - Suggestion: Preserve/pass the original runtime workspace when invoking the checker, or teach the checker to recover it from an existing `gate_decision_report` line before calling `ApprovalGate(..., runtime_workspace=...)`.

4. [Medium] Warning-registry recording failure is silently downgraded while the gate still points reviewers at warning output
   - File: `core/work_item_generator.py:1085`
   - Code: `_LOGGER.debug("warning_registry record skip (e2e_command_missing): %s", _e2e_exc)`
   - Issue: The new gate link makes warning output part of the approval workflow, but producer failures are only debug-logged. In normal logs, reviewers get an approval gate link with missing/incomplete warning evidence and no visible indication that recording failed.
   - Suggestion: Log at warning level with slug/rule context, and consider adding a visible review-note warning or returning a recoverable generation warning.

### Comparison with Known Issues

- This change does not directly address the known issues in `docs/code_review/code-review.md`.
- It repeats a known risky pattern from the checklist: silent fallback/error hiding. The `except Exception` around warning-registry recording suppresses an approval-relevant failure.
- The change is otherwise aligned with AF’s documented split between doc root and runtime workspace in `project_pipeline.py` and `work_item_generator.py`, but one caller still violates that split.

### Positive Observations

- `ApprovalGate.__init__` keeps the existing `workspace=` keyword compatible and adds `runtime_workspace` as keyword-only, avoiding the prior rename breakage risk.
- The main split-mode creation paths now pass `runtime_workspace=self.workspace` / `runtime_workspace=workspace`, which fixes the primary doc-root vs runtime-root contract for normal gate initialization.