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

This adds semantic routing for AF execution paths, including self-modifying dogfood behavior, worktree isolation, and packaging-visible `core/*.py` code.

### Findings

1. [High] Windows and dotted `core` references bypass dogfood isolation
   - File: `core/express_router.py:46`
   - Code: `_SELF_MOD: tuple[str, ...] = ( "core/", "af.spec", "master_blueprint", "dogfood", "self-modifying", )`
   - Issue: Self-mod detection only recognizes POSIX-style `core/`. Requests like `modify core\triad.py` or `modify core.triad` route to `light`, so AF-on-AF changes skip worktree isolation, triad, and merge policy.
   - Suggestion: Normalize `\` to `/`, and detect `core/`, `core.`, and explicit module references with boundary-aware matching. Add tests for `core\\triad.py` and `core.triad`.

2. [High] Top-level AF entry points can bypass dogfood routing
   - File: `core/express_router.py:46`
   - Code: `_SELF_MOD: tuple[str, ...] = ( "core/", "af.spec", "master_blueprint", "dogfood", "self-modifying", )`
   - Issue: Self-modifying AF work is broader than `core/`; the design lists `run_factory_cli.py`, `docs/*.md`, tests, and packaging config as normal repository outputs for dogfood work. A request like `update run_factory_cli.py parser` routes to `light`, skipping isolation and triad.
   - Suggestion: Add AF-owned top-level paths such as `run_factory_cli.py`, `agent_launcher.py`, `tests/`, packaging config, and relevant docs/skills paths, or accept explicit changed-file hints and classify those instead of relying only on prose tokens.

3. [High] New core module is missing from frozen-build hiddenimports
   - File: `af.spec:97`
   - Code: `'core.interview', 'core.research_brief', 'core.spec_compiler', 'core.premortem', 'core.planner', 'core.triad', 'core.dogfood', 'core.review_skill_router',`
   - Issue: `core/express_router.py` is a new `core/*.py` file but is not listed in `af.spec`. Known AF review patterns call this out because packaged `af.exe` can fail even when source tests pass.
   - Suggestion: Add `'core.express_router'` near the adjacent §17 modules and include a spec-presence or frozen smoke test.

### Comparison with Known Issues

- Repeats the known `af.spec hiddenimports` risk for new `core/*.py` modules.
- Repeats the AF-specific Windows/Unix path handling risk via `core/`-only matching.
- No subprocess, non-atomic file write, global cache, async lock, or thread-safety issue appears in `core/express_router.py`.

### Positive Observations

- `route_task()` is deterministic and side-effect free, which is appropriate for early intake routing.
- `RouteDecision.phases()` returns a copied list, so callers cannot mutate the canonical `_PHASES` table accidentally.