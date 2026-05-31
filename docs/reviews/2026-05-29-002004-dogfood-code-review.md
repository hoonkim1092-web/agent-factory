# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-29 00:20
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: WARN

### T3 Advisory

t3_required: yes

This touches dogfood worktree lifecycle behavior and potentially destructive cleanup policy.

### Findings

1. [High] `worktree_on_block` is not wired into any BLOCK path
   - File: `core/dogfood.py:268`
   - Code: `worktree_on_block: Literal["preserve", "cleanup"] = "preserve"`
   - Issue: The new policy field is never read. Existing BLOCK transitions call `block_run()` or set `state.phase = DogfoodPhase.BLOCKED`, but no path invokes worktree removal based on this option. A caller expecting `"cleanup"` will still leave the worktree behind.
   - Suggestion: Add a single BLOCK transition helper that accepts/evaluates the cleanup policy, removes the git worktree safely, updates `isolation_status`, and is used by all block paths.

2. [Medium] Main CLI cannot select the new cleanup behavior
   - File: `agent_launcher.py:953`
   - Code: `df_run.add_argument("--merge", default="auto-policy", dest="merge_mode",`
   - Issue: `dogfood run` exposes merge mode and partial implementation policy, but no `--worktree-on-block` or equivalent. Since `run_all()` also lacks this parameter, the new behavior is unreachable from the primary user path.
   - Suggestion: Add a CLI flag with choices `preserve|cleanup`, pass it into `run_all()`, and persist/report the effective policy in status output if runs need to be resumable.

3. [Medium] `Literal` value is not runtime-validated
   - File: `core/dogfood.py:270`
   - Code: `def __post_init__(self) -> None:`
   - Issue: `Literal["preserve", "cleanup"]` is only a type hint. `MergePolicy(worktree_on_block="delete")` is accepted at runtime, and `__post_init__` currently validates only `allow_partial_impl`. That is risky for a policy controlling cleanup/destructive behavior.
   - Suggestion: Validate `self.worktree_on_block in {"preserve", "cleanup"}` in `__post_init__` and raise `ValueError` for invalid values.

### Comparison with Known Issues

- The known review file repeatedly flags dogfood worktree lifecycle and policy-gate mismatches as high-risk. This change introduces another policy knob without connecting it to lifecycle enforcement.
- It also resembles the known “dead code / policy not applied by callers” pattern: the field exists, but no caller or state transition consumes it.

### Positive Observations

- The default `"preserve"` is the safer operational default for debugging blocked dogfood runs.
- Restricting the intended values with `Literal` gives static checkers a clear contract once runtime validation and wiring are added.