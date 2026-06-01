# Code Review: utils

> Source: core/utils.py
> Date: 2026-06-01 15:50
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: PASS

### T3 Advisory

t3_required: yes

This is an execution-behavior change: `core/utils.py` adds a new runtime utility function and exposes it through the module’s generated `__all__`.

### Findings

1. [Info] No non-atomic write / subprocess / cleanup risk introduced
   - File: `core/utils.py:194`
   - Code: `def running_max(values: list[int | float]) -> list[int | float]:`
   - Issue: The change is a pure in-memory list transformation. It does not touch files, subprocesses, threads, async cleanup, hooks, policy, tokens, or deployment paths.
   - Suggestion: No fix required.

2. [Info] Empty-input behavior is explicit and safe
   - File: `core/utils.py:199`
   - Code: `result: list[int | float] = []`
   - Issue: Empty input naturally returns `[]`, matching the documented behavior and avoiding `max([])`-style `ValueError`.
   - Suggestion: No fix required.

3. [Info] Running maximum state is local and bounded by input size
   - File: `core/utils.py:200`
   - Code: `current_max: int | float | None = None`
   - Issue: State is function-local, so there is no shared mutable state, cache growth, thread safety problem, or coroutine race.
   - Suggestion: No fix required.

4. [Info] Type-preserving behavior is implemented as documented
   - File: `core/utils.py:204`
   - Code: `result.append(current_max)`
   - Issue: The function appends the original max value rather than coercing through `float()`, so integer-only inputs remain integers as documented and tested.
   - Suggestion: No fix required.

### Comparison with Known Issues

- `docs/code_review/code-review.md` flags known AF patterns including non-atomic writes, shell injection, unbounded caches, silent fallback, `safe_id("") == "skill"`, and missing `af.spec` hiddenimports for new `core/*.py` files.
- This change does not repeat those patterns: no file I/O, no subprocess, no global cache, no exception swallowing, no `safe_id` usage, and no new `core/*.py` file.
- The touched file is an existing hiddenimport concern only if module layout changes; this diff only adds a function to existing `core/utils.py`.

### Positive Observations

- New tests cover empty, increasing, decreasing, mixed, negative, duplicate, float, length, type preservation, and final-max behavior.
- Focused verification passed: `pytest tests/test_utils.py` collected 132 tests, all passed.