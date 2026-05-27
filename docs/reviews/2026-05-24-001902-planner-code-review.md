# Code Review: planner

> Source: core/planner.py
> Date: 2026-05-24 00:19
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: WARN

### T3 Advisory

t3_required: yes

This is semantic behavior in a new planning module and affects verification/packaging behavior.

### Findings

1. [High] Planner is not wired into any runtime caller
   - File: `core/planner.py:197`
   - Code: `def build_plan(spec: CompiledSpec, premortem: PremortomResult) -> ExecutablePlan:`
   - Issue: Repository search found `core.planner` referenced only by `tests/test_planner.py` and prior review docs. No CLI, pipeline, interview, spec compiler, or premortem path calls `build_plan()`, so the new “executable plan” behavior is dead in normal AF execution.
   - Suggestion: Wire `build_plan()` after `compile_spec()` and `run_premortem()` in the intended planning flow, persist/pass the `ExecutablePlan`, and add an integration test.

2. [Medium] Nested core modules do not get test suggestions
   - File: `core/planner.py:78`
   - Code: `if p.suffix == ".py" and p.parent.name in ("core", "scripts"):`
   - Issue: This only handles direct children like `core/foo.py`. AF has many nested modules such as `core/providers/session_adapter.py`, `core/hooks/checkpoint.py`, and `core/control/intake.py`; those get `tests_required=[]`, weakening executable plan coverage.
   - Suggestion: Detect paths under `core/` and `scripts/`, not only immediate parents. For example, normalize path parts and generate `tests/test_<stem>.py` or use an explicit module-to-test mapping.

3. [Medium] Research gap resolution can be falsely cleared by generic token overlap
   - File: `core/planner.py:120`
   - Code: `risk_tokens = set(_WORD_RE.findall(risk.description.lower()))`
   - Issue: `_unresolved_risks()` treats any overlapping token as resolved. Generic tokens from the fixed prefix, such as `research`, `question`, or broad words like `core`, can overlap scope items and suppress unresolved risks even when the actual question is unanswered.
   - Suggestion: Strip the `"Unanswered research question: "` prefix before tokenizing, remove stopwords/generic path tokens, and require overlap on meaningful gap terms.

4. [Low] Verification step dependency ignores investigation-only plans
   - File: `core/planner.py:186`
   - Code: `depends_on=list(impl_ids),`
   - Issue: If a plan has research-gap investigation steps and verification commands but no implementation scope, the verification step has no dependencies and can run before the investigation in a dependency-driven executor.
   - Suggestion: Make verification depend on both implementation and investigation IDs, or on the immediately preceding generated steps.

5. [Low] Whitespace-prefixed comments become executable commands
   - File: `core/planner.py:88`
   - Code: `if not v.command.startswith("#"):`
   - Issue: Commands like `"  # manual check"` are not filtered and will be included in `verification_requirements` and the verification step. Empty or whitespace-only commands are also accepted.
   - Suggestion: Normalize with `cmd = v.command.strip()` and include only `cmd and not cmd.startswith("#")`.

### Comparison with Known Issues

- The known AF `af.spec` hiddenimports risk is addressed here: `af.spec` now adds `'core.planner'`.
- No non-atomic writes, shell execution, thread joins, global cache growth, or async cleanup paths are introduced in `core/planner.py`.
- The change still resembles the known “dead code / unwired behavior” pattern: a new behavioral module is tested directly but not connected to production flow.

### Positive Observations

- `PlanStep.commands` now carries verification commands on the verification step, fixing the earlier executor-visibility issue.
- Focused verification passed: `python -m py_compile core/planner.py tests/test_planner.py` and `pytest -q tests/test_planner.py` both passed, with 35 tests passing.