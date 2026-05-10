# Code Review: escalation_evaluator

> Source: core/escalation_evaluator.py
> Date: 2026-05-10 00:07
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### Findings

1. [High] P2 BLOCK evaluation is not wired into any caller
   - File: `run_factory_cli.py:288`
   - Code: `summary = WarningRegistry(workspace=args.workspace).summarize(project_slug=args.slug)`
   - Issue: The changed evaluator can now return `block=True`, but direct caller inspection shows `warning-summary` only rebuilds/prints `_summary.json`. `rg` shows `compute_run_decision()` and `write_decision_report()` are only defined, not called. Result: P2 “e2e_command_missing BLOCK 활성” never produces `_decision.json/_decision.md` and cannot actually block a run.
   - Suggestion: Wire `load_policy() -> compute_run_decision() -> write_decision_report()` into the summary/gate path, then have the pipeline/approval gate enforce `decision.block`.

2. [High] `compute_run_decision()` ignores its `policy` and `current_phase` arguments
   - File: `core/escalation_evaluator.py:184`
   - Code: `d = evaluate(virtual)`
   - Issue: `compute_run_decision(summary, policy, current_phase=...)` accepts an injected policy and phase, but delegates to `evaluate()`, which reloads the global policy and hardcodes P2 at `core/escalation_evaluator.py:96` / `core/escalation_evaluator.py:106`. P4 rules can never activate through this API, and tests/custom policies passed into `compute_run_decision()` are silently ignored.
   - Suggestion: Make `evaluate(record, *, policy=None, current_phase="P2")`, or extract a private `_evaluate_record(record, rule, current_phase)` used by both paths.

3. [High] Policy load/parse failures fail open and disable escalation
   - File: `core/escalation_evaluator.py:73`
   - Code: `except Exception:`
   - Issue: Any YAML parse error, missing `yaml`, malformed top-level structure, or validation error collapses to `{"version": 0, "rules": []}`. In P2 this means an invalid packaged policy silently turns every warning into `rule_not_active` instead of fail-closed. This repeats the known “silent fallback hides real errors” pattern from `docs/code_review/code-review.md`.
   - Suggestion: In active phases, log context and raise policy errors so the caller can write `write_error_decision(..., reason="evaluator_error")` and block. If missing policy is allowed in dev mode, gate that explicitly with an environment flag.

4. [Medium] `exempt_when` schema is not validated before use
   - File: `core/escalation_evaluator.py:60`
   - Code: `exempt_when=d.get("exempt_when"),`
   - Issue: `block_when` is validated as a mapping, but `exempt_when` is not. A typo like `exempt_when: never` reaches `core/escalation_evaluator.py:120` and crashes with `'str' object has no attribute get'`.
   - Suggestion: Validate `exempt_when` in `_PolicyRule.from_dict()` the same way as `block_when`, and include `rule_id` in the `ValueError` for diagnosis.

5. [Medium] Decision reports cannot reliably identify which phase blocked
   - File: `core/escalation_decision_report.py:204`
   - Code: `for ph in by_phase: return ph`
   - Issue: `EscalationDecision` does not carry `affected_phase`, so the report guesses by returning the first `by_phase` key for every blocking decision. If `build` and `verify` both exist, every blocked row may display the wrong phase/count.
   - Suggestion: Add `affected_phase` and `count` to `EscalationDecision`, set them during evaluation, and render those directly.

### Comparison with Known Issues

- The prior review issue “new `core/*.py` file not added to hiddenimports” is addressed for `core.escalation_evaluator` and `core.warning_registry` in `af.spec`.
- The change introduces a known bad pattern from `code-review.md`: silent fallback on broad exception handling now directly affects escalation enforcement.

### Positive Observations

- The policy uses `os.path.join(BASE_DIR, "config", "escalation_policy.yaml")`, which is aligned with AF frozen/source path handling.
- `block_when` rejects non-mapping values, which is the right direction for policy schema hardening; it just needs to cover the rest of the policy fields.