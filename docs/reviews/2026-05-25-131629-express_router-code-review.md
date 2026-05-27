# Code Review: express_router

> Source: core/express_router.py
> Date: 2026-05-25 13:16
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This change adds semantic routing for AF execution paths, including self-modifying work, worktree isolation, and packaging-visible `core/*.py` behavior.

### Findings

1. [High] Windows and dotted `core` references bypass dogfood isolation
   - File: `core/express_router.py:46`
   - Code: `_SELF_MOD: tuple[str, ...] = ("core/", "af.spec", "master_blueprint", "dogfood", "self-modifying")`
   - Issue: Self-mod detection only matches POSIX-style `core/`. `route_task("modify core\\triad.py")` and `route_task("modify core.triad")` both return `light`, so AF-on-AF changes can skip worktree isolation, triad, and merge policy.
   - Suggestion: Normalize `\` to `/`, and detect `core/`, `core.`, and explicit repo file paths with boundary-aware matching. Add tests for `core\\triad.py` and `core.triad`.

2. [High] New core module missing from PyInstaller hiddenimports
   - File: `af.spec:97`
   - Code: `'core.interview', ... 'core.triad', 'core.dogfood', 'core.review_skill_router',`
   - Issue: `core/express_router.py` is a new `core/*.py` module but is not listed in `af.spec`. This repeats the known AF frozen-build failure pattern: source tests pass, packaged `af.exe` can miss the module.
   - Suggestion: Add `'core.express_router'` next to the other §17 pipeline modules and add a spec-presence test.

3. [Medium] Substring matching causes false full-route escalation
   - File: `core/express_router.py:154`
   - Code: `return [t for t in tokens if t in low]`
   - Issue: Risk/research/complexity tokens match arbitrary substrings. Examples: `review deployments summary` routes `full` via `risk:deploy`; `redesign button spacing` routes `full` via `research:design`. That makes normal tasks pay full interview/research/premortem cost.
   - Suggestion: Use boundary-aware matching for natural-language tokens, and keep path/special tokens in a separate matcher.

4. [Medium] Router is not wired into production callers
   - File: `core/express_router.py:205`
   - Code: `def route_task(task: str, *, hints: list[str] | None = None, force_route: str | None = None) -> RouteDecision:`
   - Issue: `rg` finds no production import or caller for `route_task`; only tests, docs, and the module itself reference it. The router currently cannot affect CLI/intake behavior.
   - Suggestion: Wire it into the intended intake/CLI dispatch path, or mark the module as staged-only and add the integration in the same change.

### Comparison with Known Issues

- Repeats the known `af.spec hiddenimports` risk for new `core/*.py` files.
- Hits the AF-specific Windows/Unix path handling category.
- Does not introduce non-atomic writes, subprocess shell injection, global caches, async shared-state mutation, or resource cleanup issues.

### Positive Observations

- `route_task()` is deterministic and side-effect free, which makes it safe to call early in intake.
- `RouteDecision.phases()` returns a copy, so callers cannot mutate `_PHASES`.

Targeted verification: `python -m pytest tests\test_express_router.py -q` passed, 44 tests.