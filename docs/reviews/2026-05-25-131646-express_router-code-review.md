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

This change adds semantic routing for AF execution paths, including self-modifying work, worktree isolation, triad, merge, and packaged `core/*.py` behavior.

### Findings

1. [High] Windows and dotted `core` references bypass dogfood isolation
   - File: `core/express_router.py:46`
   - Code: `_SELF_MOD: tuple[str, ...] = ("core/", "af.spec", "master_blueprint", "dogfood", "self-modifying")`
   - Issue: Self-modifying detection only catches POSIX-style `core/`. `route_task("modify core\\triad.py")` and `route_task("modify core.triad")` both route to `light`, skipping `requires_worktree`, `requires_triad`, and `requires_merge`. That violates the AF-specific self-modifying isolation requirement.
   - Suggestion: Normalize `task` and `hints` before matching (`\` → `/`) and detect `core/`, `core.`, and explicit module/file references with boundary-aware rules. Add tests for `core\\triad.py` and `core.triad`.

2. [High] New core module is missing from frozen-build hiddenimports
   - File: `af.spec:97`
   - Code: `'core.interview', 'core.research_brief', 'core.spec_compiler', 'core.premortem', 'core.planner', 'core.triad', 'core.dogfood', 'core.review_skill_router',`
   - Issue: `core/express_router.py` is a new `core/*.py` module but is not listed in `af.spec`. Known AF review patterns explicitly flag this; source tests can pass while `dist/af/af.exe` fails to import the new router.
   - Suggestion: Add `'core.express_router'` beside the other §17 pipeline modules and add a spec-presence or frozen-smoke test.

3. [High] Migration-risk verb is missed, routing destructive DB work as light
   - File: `core/express_router.py:55`
   - Code: `_RISK: tuple[str, ...] = ("delete", "migration", "security", "deploy", "breaking change", "drop table", "overwrite", "rollback")`
   - Issue: The risk list includes noun `"migration"` but not the common verb `"migrate"`. `route_task("migrate auth database schema")` routes to `light`, so a risky schema operation skips research and premortem.
   - Suggestion: Add verb/stem coverage such as `"migrate"` and use boundary-aware matching so risk tokens catch normal task phrasing without broad substring false positives.

4. [Medium] Router has no production caller yet
   - File: `core/express_router.py:205`
   - Code: `def route_task(task: str, *, hints: list[str] | None = None, force_route: str | None = None) -> RouteDecision:`
   - Issue: Direct caller search finds only `tests/test_express_router.py`; no CLI/intake/dogfood path imports `route_task()`. As committed, the new routing behavior is dead for real AF runs.
   - Suggestion: Wire it into the intended dispatch point, or explicitly keep this as an API-only step and add the integration in the same feature branch before relying on it.

### Comparison with Known Issues

- Repeats the known `af.spec` hiddenimports risk for new `core/*.py` files.
- Hits the AF-specific Windows/Unix path handling category: self-mod routing is path-format sensitive.
- No new non-atomic writes, subprocess shell usage, global cache, or async/thread shared-state issues were found in `express_router.py`.

### Positive Observations

- `route_task()` is deterministic and side-effect free, making it cheap to test and safe to call early.
- `RouteDecision.phases()` returns a copy of the canonical phase list, preventing accidental mutation of `_PHASES`.