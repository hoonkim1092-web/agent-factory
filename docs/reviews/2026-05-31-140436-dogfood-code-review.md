# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-31 14:04
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: PASS

### T3 Advisory

t3_required: yes

This touches dogfood merge policy behavior and status reporting, so it is meaningful execution behavior.

### Findings

No correctness, security, or design findings in the reviewed diff.

Clean evidence:

1. `core/dogfood.py:1025`
   - Code: `f == p or f.startswith(p.rstrip("/") + "/")`
   - Why clean: fixes the prior fail-open prefix match while still allowing exact file matches and directory-boundary matches.

2. `core/dogfood.py:1061`
   - Code: `mode=state.merge_mode if mode is None else mode`
   - Why clean: preserves the `None` default contract while letting invalid explicit values reach `MergePolicy.__post_init__` and fail closed.

3. `core/dogfood.py:1993`
   - Code: `except OSError as exc:`
   - Why clean: keeps `read_phase_trace()` non-throwing on locked/unreadable trace files and now surfaces diagnostic context instead of silently collapsing to `[]`.

### Comparison with Known Issues

- This change directly addresses known AF review patterns around fail-open policy gates and silent fallback.
- It does not introduce the known non-atomic write, shell injection, unbounded cache, thread join, or asyncio shared-state patterns.
- The `read_phase_trace()` path still intentionally drops corrupt JSONL lines, but that matches its documented diagnostic-only contract.

### Positive Observations

- Auto and manual merge paths both continue routing through `build_merge_policy()`, avoiding policy drift.
- Regression tests cover the suffix-sibling allowlist bypass and explicit empty merge mode behavior.

Verification run: 5 focused tests passed.