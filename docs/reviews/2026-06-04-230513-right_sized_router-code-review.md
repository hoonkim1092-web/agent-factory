# Code Review: right_sized_router

> Source: core/right_sized_router.py
> Date: 2026-06-04 23:05
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

Review baseline: latest committed `core/right_sized_router.py` changes through `8849193c`. No current worktree diff exists for this file.

### T3 Advisory

`t3_required: yes`

The change controls execution depth, isolation, and mandatory review stages.

### Findings

1. [Critical] Non-dict LLM responses crash DEVELOP instead of falling back
   - File: `core/right_sized_router.py:105`
   - Code: `isolation = raw.get("isolation", "")`
   - Issue: `_validate_raw()` assumes `raw` is a dict. The API fallback's `generate_json()` can return any valid JSON value. A response such as `["bad"]` raises `AttributeError`, escaping the fallback path and terminating `_run_develop_phase()`.
   - Suggestion: Start `_validate_raw()` with `if not isinstance(raw, dict): return None`, and wrap validation plus safety-floor application in the conservative fallback boundary.

2. [High] Unknown stages are silently removed, allowing unsafe light routing
   - File: `core/right_sized_router.py:110`
   - Code: `stages = [s for s in raw_stages if s in STAGE_VOCAB]`
   - Issue: A response containing `["plan", "implement", "test", "security_review"]` silently drops `security_review`, then qualifies as light. Invalid schema should not become a less restrictive valid decision.
   - Suggestion: Require `required_stages` to be a list of known, unique stages in execution order. Fall back when any unknown stage exists.

3. [High] Content safety floor scans the old file, not the intended change
   - File: `core/right_sized_router.py:176`
   - Code: `return max(classify_with_content(f, workspace) for f in changed_files)`
   - Issue: Routing occurs before implementation. Adding `eval()`, subprocess, auth, or destructive behavior to an existing safe file remains Tier 2 because only its pre-change content is scanned. New executable files also remain Tier 2 because no content exists yet.
   - Suggestion: Use task-risk signals before execution, then reclassify actual changed content before review/finalization. Conservatively classify unknown new executable files.

4. [High] Task-derived paths can read outside the workspace
   - File: `core/right_sized_router.py:176`
   - Code: `classify_with_content(f, workspace)`
   - Issue: The caller derives paths directly from task text, including `../outside/risk.py`. `classify_with_content()` joins these without workspace-containment checks. This permits synchronous reads outside the workspace and can block on special files.
   - Suggestion: Resolve paths, enforce workspace containment, require regular files, and limit scanned file size.

5. [High] File-read failures silently weaken the safety floor
   - File: `core/right_sized_router.py:176`
   - Code: `classify_with_content(f, workspace)`
   - Issue: The callee catches `OSError` and treats unreadable files as having no Tier 3 content, silently downgrading them to Tier 2.
   - Suggestion: Make read failure distinguishable and route it to Tier 3 or `_fallback_decision()`.

### Comparison with Known Issues

- Findings 3–5 match the existing `2026-06-04-170631-right_sized_router-code-review.md` safety-floor findings.
- Silent read-failure downgrade resembles known silent-fallback issue H3.
- Frozen-build compatibility was addressed: both `core.right_sized_router` and `scripts.blast_radius` are present in `af.spec`.

### Positive Observations

- Empty scope and LLM exceptions conservatively route to the full pipeline.
- Windows path separators are normalized by both self-modification and blast-radius checks.

Verification: `168` targeted router and dogfood tests passed. The malformed-response and unknown-stage cases are currently untested.