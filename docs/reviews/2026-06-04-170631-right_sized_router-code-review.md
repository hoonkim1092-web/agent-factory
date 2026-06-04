# Code Review: right_sized_router

> Source: core/right_sized_router.py
> Date: 2026-06-04 17:06
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

The change modifies a safety floor controlling execution depth and review requirements.

### Findings

1. [High] Content scan examines the old file, not the intended change
   - File: `core/right_sized_router.py:176`
   - Code: `return max(classify_with_content(f, workspace) for f in changed_files)`
   - Issue: Routing occurs before implementation. A safe existing file about to receive `eval()`, subprocess, auth, or destructive operations remains Tier2. New files also fall back to Tier2 because no content exists yet, allowing a light route for risky planned changes.
   - Suggestion: Keep deterministic pre-execution routing, then classify the produced diff/content before review or merge. Treat unknown new executable files conservatively.

2. [High] File-read failures silently downgrade the safety floor
   - File: `core/right_sized_router.py:176`
   - Code: `classify_with_content(f, workspace)`
   - Issue: `classify_with_content()` calls `_has_tier3_content()`, which catches `OSError` and returns `False`. Unreadable, temporarily unavailable, or broken-link files therefore become Tier2 instead of triggering conservative fallback.
   - Suggestion: Make content-read failure distinguishable from safe content and route failures to `_fallback_decision()` or Tier3.

3. [High] Task-derived paths can cause reads outside the workspace or blocking I/O
   - File: `core/right_sized_router.py:176`
   - Code: `classify_with_content(f, workspace)`
   - Issue: The caller derives scope directly from task text. `classify_with_content()` joins paths without rejecting absolute paths or `../` traversal. This newly permits synchronous reads outside the workspace; special files such as Unix FIFOs can block routing indefinitely.
   - Suggestion: Resolve each path, enforce workspace containment, require regular files, and apply a maximum file-size/read limit before scanning.

4. [Medium] Content regex false positives can unnecessarily force the full pipeline
   - File: `core/right_sized_router.py:176`
   - Code: `return max(classify_with_content(f, workspace) for f in changed_files)`
   - Issue: The content classifier skips comment-only lines but still matches docstrings and ordinary string literals. For example, documentation containing `eval(user_input)` promotes an otherwise safe file to Tier3.
   - Suggestion: Use tokenization or AST-based detection for Python and add router-level false-positive tests.

### Comparison with Known Issues

- This addresses the prior review finding that path-only classification misses existing sensitive provider/subprocess files.
- It conflicts with the detailed design’s explicit choice of path-only classification for pre-execution routing and new files.
- Silent read-failure downgrade resembles the known silent-fallback risk pattern.

### Positive Observations

- `scripts.blast_radius` is already included in `af.spec`, preserving frozen-build compatibility.
- Tier aggregation uses the maximum classification, preserving conservative behavior when scanning succeeds.

Verification: `168` targeted router/dogfood tests and `29` blast-radius/router tests passed.