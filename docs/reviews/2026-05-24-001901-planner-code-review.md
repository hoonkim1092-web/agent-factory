# Code Review: planner

> Source: core/planner.py
> Date: 2026-05-24 00:19
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This adds meaningful planner behavior, carries executable verification commands, changes packaging surface via `af.spec`, and affects planning/verification flow.

### Findings

1. [High] Verification can run before unresolved research investigation when there is no implementation scope
   - File: `core/planner.py:212`
   - Code: `verify_step = _build_verification_step(verify_cmds, impl_ids, counter)`
   - Issue: `_build_verification_step()` depends only on `impl_ids`. If a spec has research gaps plus verification commands but `spec.scope == []`, the verification step has `depends_on=[]` and can run before the investigation steps, contradicting the file contract: “investigation → implementation → verification”.
   - Suggestion: Pass all prior step IDs, e.g. `prior_ids = inv_ids + impl_ids`, and make verification depend on `prior_ids`.

2. [High] Executable plan stores unvalidated shell command strings from user-derived scope
   - File: `core/planner.py:187`
   - Code: `commands=list(commands),`
   - Issue: Planner now places premortem command strings directly on `PlanStep`. The callee builds at least one command with interpolated `CompiledSpec.scope` (`core/premortem.py:88`: `command=f"python -m py_compile {targets}"`). Scope originates from interview/spec artifacts, so a future executor that runs `step.commands` with `shell=True` inherits command-injection risk.
   - Suggestion: Store structured argv (`["python", "-m", "py_compile", path]`) or validate/quote targets at the premortem boundary and document that executors must use `shell=False`.

3. [Medium] Research-gap resolution check can be defeated by generic prefix tokens
   - File: `core/planner.py:120`
   - Code: `risk_tokens = set(_WORD_RE.findall(risk.description.lower()))`
   - Issue: The token set includes boilerplate from `"Unanswered research question: ..."`. A scope like `docs/research.md` overlaps on `research`, so `_unresolved_risks()` may mark an unrelated gap as resolved even though the actual question terms are absent.
   - Suggestion: Strip the known prefix before tokenizing and ignore generic tokens like `unanswered`, `research`, and `question`.

4. [Medium] Test-file inference is not path-normalized across Windows/Unix artifacts
   - File: `core/planner.py:77`
   - Code: `p = Path(target)`
   - Issue: Planner accepts scope strings from artifacts. A Windows-style target such as `core\foo.py` will be interpreted differently on Unix-like runners, causing `_test_file_for()` to miss conventional tests. AF explicitly has Windows/Unix path portability concerns.
   - Suggestion: Normalize separators first (`target.replace("\\", "/")`) and use a consistent path parser for artifact paths.

### Comparison with Known Issues

- This change appears to address known AF packaging issue M9: `af.spec` already includes `'core.planner'` beside `core.spec_compiler` and `core.premortem`.
- It introduces a related C4-adjacent pattern: executable shell command strings are propagated through the plan. There is no direct subprocess call in `core/planner.py`, but the new `commands` payload makes the future execution boundary security-sensitive.
- No non-atomic writes, thread joins, global caches, async cleanup paths, or bare `except: pass` were introduced in `core/planner.py`.

### Positive Observations

- `PlanStep.commands` is now serialized through `to_dict()`, so verification commands are not silently lost.
- Focused tests pass: `pytest -q tests/test_planner.py` reports `35 passed`.