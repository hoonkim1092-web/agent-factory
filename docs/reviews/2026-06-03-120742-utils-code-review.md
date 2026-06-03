# Code Review: utils

> Source: core/utils.py
> Date: 2026-06-03 12:07
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: WARN

### T3 Advisory

t3_required: yes

The change adds executable behavior in `core/utils.py`, so it is semantic and should go through Tier 3.

### Findings

1. [Medium] Non-integer `window` can fail with an unclear runtime error
   - File: `core/utils.py:214`
   - Code: `if window < 1:`
   - Issue: `window=2.5` passes this check, then fails later at slicing with `TypeError: slice indices must be integers...`. Since this is a public utility exported via `__all__`, bad caller input gets an implementation error instead of a clear contract error.
   - Suggestion: Validate `isinstance(window, int)` before the range check, excluding `bool` if needed, and raise `ValueError` or `TypeError` with context.

2. [Medium] Sliding-window implementation is O(n * window) and copies each segment
   - File: `core/utils.py:219`
   - Code: `segment = values[start:i + 1]`
   - Issue: Each iteration allocates a slice and recomputes `sum(segment)`. Large inputs or large windows can become unexpectedly expensive for a generic stats helper.
   - Suggestion: Use a running sum and subtract the value that leaves the window. That gives O(n) time and no per-step list copy.

3. [Low] Test allows an implementation that violates the documented output shape
   - File: `tests/test_utils.py:522`
   - Code: `assert len(result) == 1 or result[-1] == pytest.approx(2.0)`
   - Issue: The function contract says it returns a value for each input position, but this assertion would pass if `moving_average([1, 2, 3], 3)` returned only `[2.0]`.
   - Suggestion: Replace with `assert result == pytest.approx([1.0, 1.5, 2.0])` or at least assert `len(result) == len(values)`.

### Comparison with Known Issues

- This change does not address the known `safe_id("") == "skill"` issue noted for `core/utils.py`.
- It does not repeat the critical AF patterns from `code-review.md`: no file writes, subprocess calls, thread joins, async cleanup, or provider assumptions.
- It does repeat a softer known pattern: recent `core/utils.py` changes have accumulated small public helpers, so weak tests around edge contracts can let behavior drift.

### Positive Observations

- The function handles empty input without division by zero.
- Existing `tests/test_utils.py` was updated and the focused test suite passes: `140 passed in 0.53s`.