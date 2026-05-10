# Code Review: escalation_decision_report

> Source: core/escalation_decision_report.py
> Date: 2026-05-10 00:08
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### Findings

1. [High] P2 escalation block is never generated on the main work-item path
   - File: `core/work_item_generator.py:1087`
   - Code: `gate = ApprovalGate(doc_root, slug, runtime_workspace=workspace)`
   - Issue: `e2e_command_missing` records are appended above, but `WarningRegistry.summarize()` is never called before `gate.initialize()`. Since `_decision.json` is only written from `summarize()`, `ApprovalGate.read_block_decision()` later sees no `_summary.json` and fails open. The P2 BLOCK path is therefore inactive for normal `generate_work_items()` usage.
   - Suggestion: After the warning record loop and before `gate.initialize()`, call `WarningRegistry(workspace=workspace).summarize(project_slug=slug)`. Add an integration test covering `generate_work_items()` -> `_summary.json` + `_decision.json` -> `read_block_decision()`.

2. [High] Frozen build will miss the new dynamically imported modules
   - File: `af.spec:39`
   - Code: `'core.escalation_evaluator',`
   - Issue: `core.escalation_decision_report` and `core.warning_overrides` are not listed in `hiddenimports`, while `warning_registry.py` imports the decision writer dynamically. In PyInstaller builds this can make `summarize()` fail into the emergency path, producing `block=true` decisions even for otherwise valid runs.
   - Suggestion: Add `core.escalation_decision_report` and `core.warning_overrides` to `af.spec` hiddenimports, then add a frozen-build smoke test for `WarningRegistry.summarize()`.

3. [Medium] Decision report can show the wrong blocking phase
   - File: `core/escalation_decision_report.py:204`
   - Code: `for ph in by_phase:`
   - Issue: `_extract_phase_from_decision_reason()` returns the first key in `by_phase` for every blocking decision. If the summary has `scope` first and `build` second, a build-phase block can be reported as `scope`, which is actively misleading in `_decision.md`.
   - Suggestion: Store `affected_phase` on `EscalationDecision` when `compute_run_decision()` creates the virtual record, and render that exact phase instead of guessing from `by_phase`.

4. [Medium] Generated remediation points to a CLI that is not wired
   - File: `core/escalation_decision_report.py:168`
   - Code: `f"2. \`af warning-override --workspace . --slug {slug} --rule {rule_id} "`
   - Issue: The report tells users to run `af warning-override`, but `run_factory_cli.py` has no `warning-override` dispatch entry or handler. Blocked users get a documented escape hatch that does not exist.
   - Suggestion: Implement and register `_run_warning_override_subcommand`, add it to `_STAGE1_DISPATCH` and usage text, and add add/remove CLI tests.

### Comparison with Known Issues

- This change correctly addresses the known non-atomic write pattern for individual `_decision.json` and `_decision.md` writes by using `tempfile.mkstemp()` plus `os.replace()`.
- It repeats an AF-specific known risk: new `core/*.py` runtime modules were not added to `af.spec` hiddenimports.
- The main gate wiring still resembles prior “report artifact computed but not enforced” issues: the decision writer exists, but the normal producer path does not call the summarizer that creates the decision.

### Positive Observations

- The decision writer is kept mostly leaf-level and avoids a module-level `warning_registry` import.
- The JSON payload includes schema/version and summary timestamp fields, which gives `ApprovalGate.read_block_decision()` enough data to detect stale decisions once the generation path is wired.