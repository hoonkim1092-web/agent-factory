# Code Review: warning_overrides

> Source: core/warning_overrides.py
> Date: 2026-05-10 00:09
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### Findings

1. [High] Corrupt `_overrides.json` fails open and can silently re-enable blockers
   - File: `core/warning_overrides.py:30`
   - Code: `except (OSError, json.JSONDecodeError): return {"schema_version": 1, "overrides": []}`
   - Issue: A malformed or temporarily unreadable override file is treated as “no overrides.” That silently changes escalation behavior and repeats the known “silent fallback hides real errors” pattern from `docs/code_review/code-review.md`.
   - Suggestion: Fail closed for existing-but-invalid files. Return an explicit error state, raise a contextual exception, or write `_decision.json` with a blocking override-load error. Do not silently drop override state.

2. [High] Upsert overwrites corrupt override files, causing override data loss
   - File: `core/warning_overrides.py:43`
   - Code: `except (OSError, json.JSONDecodeError): data = {"schema_version": 1, "overrides": []}`
   - Issue: If `_overrides.json` exists but has a decode error, `upsert_override()` replaces it with a fresh document containing only the new rule. Existing override decisions are lost.
   - Suggestion: Distinguish missing file from corrupt file. For corrupt JSON, abort with an error, preserve the bad file as `_overrides.json.corrupt.<ts>`, and require repair before writing.

3. [Medium] `slug` is not path-confined to the warnings root
   - File: `core/warning_overrides.py:17`
   - Code: `os.path.abspath(workspace), "runtime", "warnings", slug, "_overrides.json"`
   - Issue: A slug like `../../outside` escapes `<workspace>/runtime/warnings`. This is especially risky because the generated remediation command tells users to pass `--slug` directly.
   - Suggestion: Validate slug as a safe project slug, or resolve the final path and reject it unless it remains under `<workspace>/runtime/warnings`.

4. [Medium] Generated remediation points to a CLI command that is not registered
   - File: `core/escalation_decision_report.py:168`
   - Code: ``f"2. `af warning-override --workspace . --slug {slug} --rule {rule_id} "``
   - Issue: `run_factory_cli.py` only registers `warning-summary` and `warning-repair`; there is no `warning-override` dispatch. The block report gives users a non-working remediation path.
   - Suggestion: Add `warning-override` and probably `warning-unoverride` CLI handlers wired to `upsert_override()` / `remove_override()`, or change the report text to a supported command.

5. [Medium] New `core/*.py` files are missing from PyInstaller hiddenimports
   - File: `af.spec:39`
   - Code: `'core.escalation_evaluator', 'core.warning_registry',`
   - Issue: `core/warning_overrides.py` and `core/escalation_decision_report.py` are new core modules, but neither is listed in `af.spec`. `warning_registry` imports `escalation_decision_report` dynamically, which is exactly the frozen-build pattern that often needs explicit hiddenimports.
   - Suggestion: Add `core.warning_overrides` and `core.escalation_decision_report` to hiddenimports and include a frozen smoke test for `af warning-summary`.

### Comparison with Known Issues

- The change partially addresses the known non-atomic write risk by using `tempfile.mkstemp()` plus `os.replace()`.
- It introduces/repeats the known silent fallback pattern: corrupt override files are swallowed in both `warning_overrides.py` and `warning_registry.py`.
- It also hits the AF-specific hiddenimport checklist: new `core/*.py` modules are not added to `af.spec`.

### Positive Observations

- Writes use atomic replace rather than direct `open(path, "w")`, which avoids partial-file corruption on normal write failure.
- Mutating override operations use `locked_file()`, so concurrent writers are serialized.