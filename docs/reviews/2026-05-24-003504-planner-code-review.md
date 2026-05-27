# Code Review: planner

> Source: core/planner.py
> Date: 2026-05-24 00:35
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This is meaningful execution-planning behavior and it introduces serializable verification commands that a later runner may execute.

### Findings

1. [High] Planner is not wired into any production flow
   - File: `core/planner.py:200`
   - Code: `def build_plan(spec: CompiledSpec, premortem: PremortomResult) -> ExecutablePlan:`
   - Issue: Repository search found `build_plan()` used only by `tests/test_planner.py` and review docs. The active pipeline still uses `ProjectPlanningDirector.plan()` / `enrich_role_plan()` directly, so normal AF execution never produces or consumes `ExecutablePlan`.
   - Suggestion: Wire `build_plan()` after `compile_spec()` and `run_premortem()` in the intended planning path, persist/pass the result, and add an integration test covering that path.

2. [High] Verification step can run before investigation when there are no implementation steps
   - File: `core/planner.py:189`
   - Code: `depends_on=list(impl_ids),`
   - Issue: Verification depends only on implementation IDs. If a plan has research-gap investigation steps and verification commands but no scoped implementation items, `impl_ids` is empty, so a dependency-driven executor may run verification before the required investigation step.
   - Suggestion: Make verification depend on all prerequisite steps, e.g. `depends_on=list(impl_ids or investigation_ids)` or pass a consolidated `prior_step_ids`.

3. [Medium] Raw shell-like verification commands are now serialized into executable plan steps
   - File: `core/planner.py:190`
   - Code: `commands=list(commands),`
   - Issue: The callee builds commands as strings, including interpolated scope values in `core/premortem.py:88`: `command=f"python -m py_compile {targets}"`. Scope originates from spec/interview artifacts. A future Step 7 executor using `shell=True` would inherit command-injection risk.
   - Suggestion: Store verification commands as structured argv lists, or add a command schema with explicit executable/args fields and require runners to use `subprocess.run(argv, shell=False)`.

4. [Medium] Unresolved research-gap detection is too weak and can suppress real gaps
   - File: `core/planner.py:124`
   - Code: `if not risk_tokens & scope_tokens:`
   - Issue: Any single token overlap marks a research gap as resolved. Generic tokens from paths such as `core`, `py`, `policy`, or `test` can hide unresolved questions without evidence that the question was actually answered.
   - Suggestion: Use a stricter match: ignore path/boilerplate stopwords, require multiple meaningful token overlaps, or track explicit gap-resolution artifacts instead of inferring from scope filenames.

### Comparison with Known Issues

- The known AF `af.spec` hiddenimports issue is addressed: `af.spec:101` includes `'core.planner'`.
- The prior issue where verification commands were lost from `PlanStep` is addressed by `PlanStep.commands`.
- The new raw command field creates a nearby shell/subprocess risk pattern from the checklist, even though this file does not execute commands yet.

### Positive Observations

- `PlanStep` and `ExecutablePlan` use `field(default_factory=list)`, avoiding shared mutable defaults.
- The planner keeps spec, premortem, and plan as explicit dataclass boundaries with serializable `to_dict()` methods.