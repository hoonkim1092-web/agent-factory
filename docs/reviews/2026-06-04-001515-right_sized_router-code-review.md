# Code Review: right_sized_router

> Source: core/right_sized_router.py
> Date: 2026-06-04 00:15
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This is new `core/*.py` behavior that routes execution depth and isolation, so Tier 3 review is required.

### Findings

1. [High] Empty scope can still produce a light router decision
   - File: `core/right_sized_router.py:256`
   - Code: `files: list[str] = list(changed_files or [])`
   - Issue: `changed_files=[]` is accepted, the LLM is still called, and `is_light()` can return `True` if the LLM returns high-confidence `["plan", "implement", "test"]`. The detailed design and acceptance criteria require no-scope tasks to go full/conservative because Tier3 floors cannot be evaluated.
   - Suggestion: Return `_fallback_decision("no changed_files scope")` before building the prompt when `files` is empty. Update `test_r_fb_noscope` to assert `source == "fallback"` and `is_light() is False`.

2. [High] Sensitive core provider files are not forced through full review
   - File: `core/right_sized_router.py:173`
   - Code: `return max(classify_path(f) for f in changed_files)`
   - Issue: The router uses path-only `classify_path()`. `scripts/blast_radius.py:119-141` only marks explicit Tier3 paths/prefixes and otherwise returns Tier2, so files like `core/providers/cli.py` that contain subprocess/provider execution logic will not trigger the Tier3 floor. This repeats a known design-review issue.
   - Suggestion: Use `classify_with_content(rel_path, workspace)` for existing files, or extend `_TIER3_PATHS`/`_TIER3_PREFIXES` to cover provider/subprocess/auth/hook code paths used by AF.

3. [Medium] New core module is missing from frozen-build hidden imports
   - File: `af.spec:33`
   - Code: `hiddenimports=[`
   - Issue: `core.right_sized_router` is a new `core/*.py` file but is not listed in `af.spec`. The project’s known review patterns explicitly call out new core files missing from hiddenimports, and the detailed design also required adding this module.
   - Suggestion: Add `'core.right_sized_router'` to `af.spec`. Also check whether `scripts.blast_radius` must be packaged, since this router imports it at runtime.

4. [High] Self-modification floor depends on workspace path name
   - File: `core/right_sized_router.py:158`
   - Code: `token.rstrip("/") in ws_lower for token in ("agent-factory", "agent_factory")`
   - Issue: A self-modifying scope such as `core/foo.py` only triggers if `workspace` contains `agent-factory` or `agent_factory`. Dogfood worktrees or alternate checkout names can bypass the floor and keep LLM-selected lower isolation.
   - Suggestion: Decide self-modification from normalized repo-relative `changed_files` alone, or pass an explicit `is_agent_factory_workspace`/source-root flag instead of inferring from path text.

### Comparison with Known Issues

- Repeats the known `af.spec` hiddenimports risk for new `core/*.py` modules.
- Repeats the prior design-review warnings for no-scope fallback, path-only blast-radius classification, and workspace-dependent self-mod detection.
- Does not address any existing `code-review.md` issue directly; it introduces new routing behavior that needs the same AF frozen-build and Tier3 safeguards.

### Positive Observations

- The LLM response schema is validated before constructing `RouteDecision`, with invalid isolation and empty stages falling back.
- Tier3 floors are applied after LLM classification, so valid floors can override an underestimating model response when classification detects the risk.