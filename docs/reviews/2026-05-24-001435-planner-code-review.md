# Code Review: planner

> Source: core/planner.py
> Date: 2026-05-24 00:14
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This adds executable behavior in a new `core/*.py` planning module and affects verification/packaging behavior.

### Findings

1. [High] Research gaps can be falsely marked as resolved by generic prefix tokens
   - File: `core/planner.py:118`
   - Code: `risk_tokens = set(_WORD_RE.findall(risk.description.lower()))`
   - Issue: `_unresolved_risks()` tokenizes the whole description, including the fixed prefix `"Unanswered research question"`. Any scope like `core/research.py` overlaps on `research`, so unrelated gaps such as `"retry budget"` can disappear from `unresolved_risks`.
   - Suggestion: strip the fixed prefix before tokenizing, and ignore common structural tokens. Match only the actual gap text.

2. [High] Verification step drops the commands it is supposed to run
   - File: `core/planner.py:178`
   - Code:
     ```python
     step = PlanStep(
         id=f"S{counter[0]}",
         action="Run verification checks from premortem",
         target="verification",
         tests_required=[],
         artifacts=["verification_report.md"],
         depends_on=list(impl_ids),
     )
     ```
   - Issue: `_build_verification_step(commands, ...)` only checks that commands exist, then discards them. Consumers iterating `plan.steps` get a verification step with no executable command payload, so the “executable plan” is incomplete unless they know to separately read `verification_requirements`.
   - Suggestion: include the commands in the step, for example via `tests_required=list(commands)` or a dedicated `commands` field on `PlanStep`.

3. [Medium] New `core/*.py` module is missing from PyInstaller hiddenimports
   - File: `af.spec:97`
   - Code:
     ```python
     'core.research_brief',
     'core.spec_compiler',
     'core.premortem',
     'core.interactive_chat',
     ```
   - Issue: `core/planner.py` is a new core module but `af.spec` lists `core.spec_compiler` and `core.premortem` without `core.planner`. This repeats the known AF packaging risk where frozen `dist/af/af.exe` may miss newly added modules.
   - Suggestion: add `'core.planner'` to `hiddenimports`, near the adjacent §17 modules.

4. [Medium] Nested core modules do not get test suggestions
   - File: `core/planner.py:76`
   - Code: `if p.suffix == ".py" and p.parent.name in ("core", "scripts"):`
   - Issue: This only handles direct children like `core/foo.py`. AF has many nested modules such as `core/providers/session_adapter.py` and `core/control/supervisor.py`; those implementation steps will have no suggested test file even though conventional `tests/test_session_adapter.py` or subsystem tests exist.
   - Suggestion: detect `core` or `scripts` anywhere in the path parts, or derive test suggestions from the final module stem for nested modules too.

### Comparison with Known Issues

- This change repeats the known `af.spec hiddenimports` pattern from the review checklist: “new `core/*.py` file not added to hiddenimports.”
- It is related to the known packaging/frozen-build concern in `code-review.md` section M9.
- No evidence that this change addresses an existing issue from `code-review.md`; it adds a new planner module plus tests.

### Positive Observations

- The planner keeps `CompiledSpec`, `PremortomResult`, and `ExecutablePlan` as explicit data boundaries instead of passing loose dicts through the whole flow.
- The generated step ordering is deterministic: investigation, implementation, then verification, with stable sequential IDs.