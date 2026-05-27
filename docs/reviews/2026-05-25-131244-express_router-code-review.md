# Code Review: express_router

> Source: core/express_router.py
> Date: 2026-05-25 13:12
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This change adds semantic routing behavior for self-modifying AF work and packaging-visible `core/*.py` code.

### Findings

1. [High] Windows and dotted `core` references bypass dogfood isolation
   - File: `core/express_router.py:45`
   - Code: `_SELF_MOD: tuple[str, ...] = ( "core/", "af.spec", ... )`
   - Issue: Self-mod detection only recognizes POSIX-style `core/`. Requests like `modify core\triad.py` or `modify core.triad` route to `light`, so AF-on-AF changes can skip worktree isolation, triad, and merge policy. This conflicts with the design requirement that self-modifying AF work uses dogfood isolation.
   - Suggestion: Normalize task and hints before matching, e.g. replace `\` with `/`, and detect `core/`, `core.`, and explicit repo file paths with boundary-aware matching. Add tests for `core\\triad.py` and `core.triad`.

2. [High] New `core/*.py` module is missing from PyInstaller hiddenimports
   - File: `af.spec:97`
   - Code: `'core.interview', 'core.research_brief', 'core.spec_compiler', 'core.premortem', 'core.planner', 'core.triad', 'core.dogfood', 'core.review_skill_router',`
   - Issue: `core/express_router.py` is a new core module but is not listed in `af.spec`. Known AF review patterns explicitly call out new `core/*.py` files missing from hiddenimports; packaged `af.exe` can fail even if source tests pass.
   - Suggestion: Add `'core.express_router'` near the adjacent §17 pipeline modules and include a frozen-build or spec-presence test.

3. [Medium] Substring token matching misroutes non-trivial tasks as direct
   - File: `core/express_router.py:153`
   - Code: `return [t for t in tokens if t in low]`
   - Issue: Tokens are matched as arbitrary substrings. For example, `fix blacklist handling` routes to `direct` because `list` is inside `blacklist`. That can skip interview/deep-skip for actual code changes.
   - Suggestion: Use boundary-aware matching for single-word tokens and explicit phrase matching for multi-word tokens. Keep path tokens separate from natural-language tokens.

### Comparison with Known Issues

- This repeats the known `af.spec hiddenimports` packaging risk for new `core/*.py` files.
- It also hits the AF-specific Windows/Unix path handling category: self-mod routing is path-format sensitive.
- No new non-atomic writes, subprocess shell usage, global cache, or async/thread safety issues were introduced in `express_router.py`.

### Positive Observations

- `route_task()` is deterministic and side-effect free, which makes it easy to test and safe to call early in intake.
- `RouteDecision.phases()` returns a copy of the phase list, avoiding accidental mutation of the canonical route table.

Targeted verification: `python -m pytest tests\test_express_router.py -q` passed: 40 tests.