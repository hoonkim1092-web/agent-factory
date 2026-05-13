# Code Review: utils

> Source: core/utils.py
> Date: 2026-05-14 00:51
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: WARN

### Findings

1. [High] Global `SKILLS_DIR` can shadow workspace project skills in external resolution
   - File: `core/utils.py:281`
   - Code: `SKILLS_DIR,`
   - Issue: `get_external_skill_roots()` now returns `BASE_DIR/skills` before `PROJECT_ROOT/skills`. In `ExternalSkillResolver`, `CodexOfficialSkillSource` de-duplicates candidates by `skill_id`, so a bundled/global `SKILLS_DIR/foo/SKILL.md` wins over a workspace-local `PROJECT_ROOT/skills/foo/SKILL.md`.
   - Suggestion: Put `os.path.join(PROJECT_ROOT, "skills")` before `SKILLS_DIR`, or keep `SKILLS_DIR` out of `get_external_skill_roots()` and rely on existing explicit `SKILLS_DIR` handling where needed.

2. [Medium] Environment-root precedence is documented incorrectly and can override personal/project roots
   - File: `core/utils.py:301`
   - Code: `for raw_root in list(extra_roots or []) + env_paths + defaults:`
   - Issue: The docstring says env roots are priority 4, after personal/project/runtime, but code prepends `extra_roots` and env paths before defaults. That means `AGENT_CODEX_SKILL_DIRS` / `AGENT_CLAUDE_SKILL_DIRS` silently outrank personal and project roots.
   - Suggestion: Either update the documented precedence to match override-first behavior, or change the loop to `defaults + env_paths + extra_roots` if the numbered contract is intended.

3. [Medium] New test encodes the likely wrong project/global precedence
   - File: `tests/test_cross_cli_skill_discovery.py:84`
   - Code: `assert root_strs.index(skills_dir) < root_strs.index(project_skills)`
   - Issue: This locks in `BASE_DIR/skills` before `PROJECT_ROOT/skills`, which conflicts with AF’s project override model and the existing `skill_registry` load order where project skills are first.
   - Suggestion: Reverse the assertion, or split global bundled skills from external project skill roots so tests reflect the intended override semantics.

### Comparison with Known Issues

- This change addresses the known gap noted in `docs/reviews/2026-05-13-234351...`: `PROJECT_ROOT/skills/` is now included in `get_external_skill_roots()`.
- It does not repeat the critical checklist patterns: no non-atomic writes, shell execution, async cleanup, or new thread/shared-state mutation.
- It does introduce a precedence risk similar to known AF path-resolution issues: global/frozen-aware `BASE_DIR` paths can win over workspace-specific `PROJECT_ROOT` behavior.

### Positive Observations

- Uses `os.path.join()` and existing `SKILLS_DIR` / `PROJECT_ROOT` constants, so Windows path handling and frozen/source path derivation stay centralized.
- The changed tests cover inclusion and ordering for the newly added roots; `pytest -q tests/test_cross_cli_skill_discovery.py` passed with `21 passed`.