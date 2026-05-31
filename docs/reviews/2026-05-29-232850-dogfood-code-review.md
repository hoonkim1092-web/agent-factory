# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-29 23:28
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This touches auto-merge policy, merge gates, cleanup semantics, and trace error handling.

### Findings

1. [High] Empty `merge_mode` still falls through to auto-policy
   - File: `core/dogfood.py:1054`
   - Code: `mode=mode or state.merge_mode,`
   - Issue: `build_merge_policy(state, "")` treats an explicit invalid empty string as “use `state.merge_mode`”. Through `_run_merge_phase(state, "")`, this can still auto-merge instead of failing closed, leaving a gap in the new merge-mode validation.
   - Suggestion: Use `state.merge_mode if mode is None else mode`, and validate `mode` at the start of `build_merge_policy()` or `_run_merge_phase()`.

2. [High] Scope allowlist uses unsafe prefix matching
   - File: `core/dogfood.py:1023`
   - Code: `if not any(f.startswith(p) for p in policy.allowed_paths):`
   - Issue: A plan allowing `core/utils.py` also allows `core/utils.py.bak`; a plan allowing `core/foo` allows `core/foobar.py`. This matters more after this change because `_run_merge_phase()` now routes auto-merge through plan-derived `allowed_paths`.
   - Suggestion: Normalize paths and require exact match for file paths, or directory-boundary matching only for explicit directory entries, e.g. `f == p or f.startswith(p.rstrip("/") + "/")`.

3. [Medium] New cleanup disambiguation is not exposed by the CLI caller
   - File: `agent_launcher.py:1093`
   - Code: `print(f"isolation_status  : {state.isolation_status}")`
   - Issue: `core/dogfood.py:778-779` still records `isolation_status = "cleanup_failed"` with `cleanup_skip_reason = "wt_never_created"`, but `dogfood status` prints only the failure label. Operators still see the false alarm the new field was meant to disambiguate.
   - Suggestion: Print `cleanup_skip_reason` when present, or use a non-failure status such as `cleanup_skipped` for the intentional branch-preservation path.

4. [Medium] Trace read errors are silently converted to “no trace”
   - File: `core/dogfood.py:1984`
   - Code: `except OSError: return []`
   - Issue: Permission/lock/read failures are not the same as a missing or truncated trace. Returning `[]` hides a real operational error and repeats the known “silent fallback” pattern from `code-review.md`.
   - Suggestion: Return partial records only when possible, otherwise surface/log the `OSError` with path context. If the public API must stay non-throwing, include an error sentinel record.

### Comparison with Known Issues

- This change directly addresses known dogfood findings: plan-derived auto-merge allowlist bypass, arbitrary `merge_mode` fallthrough, and cleanup skip explanation.
- It still repeats two known patterns: silent fallback on real errors, and merge policy gates that can be bypassed by loose path matching.

### Positive Observations

- Extracting `build_merge_policy()` makes manual and auto merge paths share the same denied-path and plan allowlist construction.
- `MergePolicy.__post_init__()` adds a useful second validation layer for most invalid merge-mode inputs.