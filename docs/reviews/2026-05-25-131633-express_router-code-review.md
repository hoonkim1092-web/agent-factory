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

This change affects routing/policy for self-modifying AF work, dogfood isolation, triad review, packaging, and potentially destructive behavior.

### Findings

1. [High] Self-modifying AF work is under-detected
   - File: `core/express_router.py:46`
   - Code: `_SELF_MOD: tuple[str, ...] = ("core/", "af.spec", "master_blueprint", "dogfood", "self-modifying",)`
   - Issue: Only POSIX-style `core/` is recognized. Requests like `modify core\triad.py`, `modify core.triad`, `update run_factory_cli.py`, `change agent_launcher.py`, or `edit skills/dp/SKILL.md` can route to `light`, skipping worktree isolation, triad, and merge policy. The design explicitly treats self-modifying AF work as dogfood.
   - Suggestion: Normalize path separators and detect AF-owned source paths explicitly: `core[\\/...]`, dotted `core.*`, `run_factory_cli.py`, `agent_launcher.py`, `af.spec`, `Master_Blueprint.md`, `skills/*`, and packaging config. Prefer passing changed file paths from intake over substring matching free text.

2. [High] `force_route` can downgrade risky work
   - File: `core/express_router.py:218`
   - Code: `if force_route is not None: ... mode = force_route`
   - Issue: A caller can force `direct` for text that otherwise contains `security`, `delete`, or `core/`. If this is exposed through CLI/config, it becomes a policy bypass for dogfood isolation and premortem/research routing.
   - Suggestion: Treat force as trusted-only, or only allow escalation. Compute the natural route first and reject downgrades unless an internal override flag is used and audited.

3. [Medium] New `core/*.py` module is missing from frozen hiddenimports
   - File: `af.spec:97`
   - Code: `'core.interview', 'core.research_brief', 'core.spec_compiler', 'core.premortem', 'core.planner', 'core.triad', 'core.dogfood', 'core.review_skill_router',`
   - Issue: `core.express_router` is a new core module but is absent from `af.spec`. This repeats the known AF frozen-build issue where source tests pass but `dist/af/af.exe` misses dynamically imported modules.
   - Suggestion: Add `'core.express_router'` near the adjacent §17 modules and add a spec-presence or frozen smoke test.

4. [Medium] Router is not wired into production flow
   - File: `core/express_router.py:205`
   - Code: `def route_task(task: str, *, hints: list[str] | None = None, force_route: str | None = None) -> RouteDecision:`
   - Issue: Repository search shows `route_task()` is referenced by tests/docs/review artifacts, but no CLI, intake, dogfood, or orchestrator production path calls it. The Express Router behavior is therefore dead code for normal AF execution.
   - Suggestion: Wire it into the intended intake/CLI dispatch point before deep interview/dogfood selection, and add an integration test proving a real command uses the route decision.

5. [Medium] Destructive-risk vocabulary misses common destructive verbs
   - File: `core/express_router.py:55`
   - Code: `_RISK: tuple[str, ...] = ("delete", "migration", "security", "deploy", "breaking change", "drop table", "overwrite", "rollback",)`
   - Issue: Requests using `remove`, `purge`, `truncate`, `destroy`, `wipe`, `reset`, or `rm` can avoid the `full` route. That weakens the destructive-operation guardrail the review checklist calls out.
   - Suggestion: Expand destructive tokens and use word-boundary regexes for risk terms to reduce both misses and substring false positives.

### Comparison with Known Issues

- Repeats known AF packaging pattern M9: new `core/*.py` file not added to `af.spec` hiddenimports.
- No new file writes, subprocess shell usage, global mutable cache, or async/thread shared-state issue in `express_router.py`.
- The route downgrade issue is adjacent to known policy/gate bypass concerns in the dogfood/review pipeline.

### Positive Observations

- `route_task()` is deterministic and side-effect free, which makes it easy to test and safe to call early.
- `RouteDecision.phases()` returns a copy, so callers cannot mutate the canonical `_PHASES` table.

Verification: `python -m pytest tests\test_express_router.py -q` passed: 44 tests.