# Code Review: warning_registry

> Source: core/warning_registry.py
> Date: 2026-05-09 20:52
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### Findings

1. [High] `project_slug` / `rule_id` can escape the warning store
   - File: `core/warning_registry.py:122`
   - Code: `slug_dir = os.path.join(self.warnings_root, project_slug)`
   - Issue: `project_slug` and `rule_id` are used directly in paths (`f"{rule_id}.jsonl"` at line 125). Values like `../x` can write outside `<workspace>/runtime/warnings`, especially once CLI/API callers are added.
   - Suggestion: Validate both with a strict regex such as `^[A-Za-z0-9._-]+$`, reject path separators, and verify `os.path.commonpath([self.warnings_root, resolved_path]) == self.warnings_root`.

2. [High] Dedup key can suppress meaningful escalation changes
   - File: `core/warning_registry.py:106`
   - Code: `"rule_id": rule_id, "affected_phase": canonical_phase, "count": count, "affected_ids": sorted(affected_ids),`
   - Issue: `record_id` excludes `severity`, `baseline_delta`, `false_positive_override`, and `rationale`. A later `block_candidate` or `block` record for the same affected IDs/count can be silently skipped at line 141.
   - Suggestion: Include escalation-relevant fields in the stable payload, or separate “event identity” from “latest state” with an explicit update/merge path.

3. [Medium] Approval gate links to `_decision.md`, but registry never creates it
   - File: `core/warning_registry.py:173`
   - Code: `summary = _build_summary(project_slug, slug_dir)`
   - Issue: `ApprovalGate` now always renders `gate_decision_report` to `<runtime_workspace>/runtime/warnings/<slug>/_decision.md` (`core/approval_gate.py:350`), but `summarize()` only writes `_summary.json`. The design’s accepted v6 behavior requires lazy `_decision.md` creation.
   - Suggestion: Add `_ensure_decision_md(project_slug, summary)` inside `summarize()` after atomic summary write, using atomic write as well.

4. [High] Required warning summary/repair CLI is missing
   - File: `run_factory_cli.py:556`
   - Code: `parser = argparse.ArgumentParser(description="Agent Factory CLI")`
   - Issue: No `warning-summary` / `warning-repair` subcommands are registered, and `core/warning_registry.py` has no `__main__` CLI. `python -m core.warning_registry summary --workspace ...` will not perform the documented action.
   - Suggestion: Add argparse handlers in `core.warning_registry` for `summary` and `repair`, then wire frozen-safe `af warning-summary` and `af warning-repair` in `run_factory_cli.py`.

5. [Medium] Frozen build hiddenimports missing for new core modules
   - File: `af.spec:33`
   - Code: `hiddenimports=[`
   - Issue: `core.warning_registry` and `core.escalation_evaluator` are absent from explicit hiddenimports, despite the project’s known PyInstaller pattern and the design acceptance requiring both.
   - Suggestion: Add `'core.warning_registry'` and `'core.escalation_evaluator'` to the core hiddenimports block and run a frozen import smoke test.

### Comparison with Known Issues

- `docs/code_review/code-review.md` only has a skipped review entry for this exact `core/warning_registry.py` edit, so it does not already cover these defects.
- The broader design docs repeatedly flag the same accepted requirements: frozen hiddenimports, CLI wiring, `_decision.md` lazy creation, and no cwd/doc_root fallback. This change partially implements the registry but repeats the known “frozen build compatibility” and “missing operational entrypoint” risk patterns.

### Positive Observations

- `WarningRegistry(workspace)` correctly rejects empty workspace and uses workspace-owned runtime paths instead of cwd fallback.
- `_summary.json` uses `tempfile.mkstemp` plus `os.replace`, which matches the project’s atomic cache-write pattern.