# Code Review: review_skill_router

> Source: core/review_skill_router.py
> Date: 2026-05-25 10:05
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This changes review routing behavior and `core/*.py`, so it is meaningful behavior, not docs-only.

### Findings

1. [High] New router is not wired into the actual review gate path
   - File: `core/review_skill_router.py:123`
   - Code: `def route_review_skills(ctx: ReviewContext) -> ReviewSkillPlan:`
   - Issue: `route_review_skills` is only referenced by tests and `af.spec`; runtime review paths still use `scripts/review_gate.py` and `scripts/check_pending_review.py` with fixed tier/agent logic. `scripts/check_pending_review.py:185` still does `agent_list, instruction = _agents_for_tier(blast_tier, t3_skip_allowed)`, so specialized skill profiles are never shown, stored, or enforced.
   - Suggestion: Integrate this router where `.af_review_queue/pending_agent_review.json` is created, persist `required_tiers` and `profiles`, and make `check_pending_review.py`/`review_gate.py` consume that plan.

2. [High] Router output schema is incompatible with the existing gate contract
   - File: `core/review_skill_router.py:175`
   - Code: `required_tiers=["af-test-runner", "af-critic", "af-cross-review"],`
   - Issue: Existing gate code treats tiers as numeric review levels and maps them through `_TIER_AGENTS`. `scripts/review_gate.py:92` defines `_TIER_AGENTS: dict[int, str] = { ... }`, and `_required_tiers_for()` returns `[1, 2, 3]`. If this new plan is serialized as-is, current gate code cannot validate it without another translation layer.
   - Suggestion: Either rename this field to `required_agents`, or return numeric tier IDs plus profile metadata keyed by agent. Add an integration test with `pending_agent_review.json`.

3. [Medium] Invalid `blast_tier` silently routes as Tier 2
   - File: `core/review_skill_router.py:130`
   - Code: `if ctx.blast_tier == 1:`
   - Issue: The only validation is equality checks. `blast_tier=0`, `4`, or runtime string `"3"` falls into the Tier 2/3 branch, but `tier3 = ctx.blast_tier == 3` at `core/review_skill_router.py:144` stays false, so Tier 3-only skills are skipped without error.
   - Suggestion: Validate `blast_tier in (1, 2, 3)` at entry and raise `ValueError` for invalid values, or normalize from queue state before constructing `ReviewContext`.

4. [Medium] Duplicates existing critic skill routing without migration
   - File: `core/review_skill_router.py:79`
   - Code: `"af-code-review", "af-architecture", "systematic-debugging",`
   - Issue: The project already has `core/critic_skill_router.py:68` with `def map_paths_to_skills(changed_paths: list[str], max_skills: int = 3) -> list[str]:`. This new router introduces a parallel skill vocabulary and no caller migration, matching the known design-review warning about a second unused router.
   - Suggestion: Either adapt `review_skill_router` to call the existing critic router for critic-domain skills, or explicitly replace it and update all callers/tests.

### Comparison with Known Issues

- This repeats the known “parallel router not consumed by review gates” pattern called out in prior design reviews.
- It does address the known `af.spec hiddenimports` concern: `af.spec:104` includes `core.review_skill_router`.
- No repeat of the critical file-write, shell-injection, or thread-join patterns was found in this file.

### Positive Observations

- Path normalization is handled for blueprint impact: `f.replace("\\", "/")`.
- Unit coverage for the new pure routing function is broad: `tests/test_review_skill_router.py` has 35 passing tests.