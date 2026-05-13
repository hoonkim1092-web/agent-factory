# Code Review: utils

> Source: core/utils.py
> Date: 2026-05-14 01:11
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: WARN

### Findings

1. [Medium] Changed knowledge-skill priority has no direct regression coverage
   - File: `core/utils.py:326`
   - Code: `ordered_roots = get_codex_skill_roots(priority + (extra_roots or []))`
   - Issue: This changes the resolution path for knowledge skills, but existing tests cover `get_external_skill_roots()` and action-skill `resolve_skill_paths()`, not `resolve_knowledge_skill_path()` when the same skill exists in project/global/extra roots. This is risky because callers use it to load runtime knowledge skills and decide reuse.
   - Suggestion: Add tests for `resolve_knowledge_skill_path()` with duplicate `SKILL.md` in `PROJECT_SKILLS_DIR`, `SKILLS_DIR`, and `extra_roots`, covering both `prefer_project_skills=True` and `False`.

2. [High] Silent fallback hides visualizer update failures
   - File: `core/utils.py:125`
   - Code: `except Exception:`
   - Issue: `print_agent_msg()` suppresses all visualizer update errors with `pass`, matching the known H3 silent-fallback pattern from `docs/code_review/code-review.md`. A broken visualizer/state update becomes invisible while execution continues with stale UI state.
   - Suggestion: Log the agent name, phase, and exception at warning/debug level, or re-raise in strict/test mode.

3. [High] JSON parse fallback hides malformed model output
   - File: `core/utils.py:80`
   - Code: `except Exception:`
   - Issue: `safe_json_load()` catches any JSON error, regex-extracts the first object, and returns `{}` if none exists. Callers can treat malformed output as an empty valid result, repeating the known silent-fallback pattern.
   - Suggestion: Catch `json.JSONDecodeError`, include the parse context, and return an explicit error object or raise `ValueError from e` when extraction fails.

4. [Medium] Case-insensitive dedupe is applied on case-sensitive filesystems
   - File: `core/utils.py:306`
   - Code: `key = normalized.lower()`
   - Issue: On Linux/macOS case-sensitive volumes, two valid roots that differ only by case collapse into one. The changed resolver now routes explicit priority roots through this dedupe path, so a valid skill root can be skipped.
   - Suggestion: Use `os.path.normcase(normalized)` for the dedupe key instead of unconditional `.lower()`.

### Comparison with Known Issues

- The change does not directly address the known high-risk issues in `docs/code_review/code-review.md`.
- `core/utils.py` still contains patterns similar to known issue H3: broad exception handling with silent fallback.
- No new `core/*.py` file was added, so `af.spec` hiddenimports are not implicated.

### Positive Observations

- The changed line removes duplicate project/global roots by routing priority roots through the centralized root normalizer.
- The resolver still uses `os.path.join()` and existing `PROJECT_SKILLS_DIR` / `SKILLS_DIR` constants, so it does not introduce hardcoded Unix/Windows path separators.

Verification: ran `python -m pytest tests/test_cross_cli_skill_discovery.py tests/test_project_overrides.py -q`. Result: 24 passed, 1 failed. The failure is in `tests/test_project_overrides.py::test_project_skill_override_priority` due a Windows-style suffix assertion on POSIX, not this `resolve_knowledge_skill_path()` change.