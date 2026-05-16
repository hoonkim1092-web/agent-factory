# Code Review: ise_loop

> Source: core/ise_loop.py
> Date: 2026-05-17 01:35
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### Findings

1. [High] DynamicOrchestrator checks the old lineage ledger while FSA writes the new runtime ledger
   - File: `core/dynamic_orchestrator.py:875`
   - Code: `_ll = get_lineage_ledger(target_workspace)`
   - Issue: FSA now writes lineage to `state_workspace` via `FSALoop.run_mission(..., runtime_workspace=state_workspace)`, but the pre-check still reads `target_workspace`. The maxed/degrade guard will not see the attempts FSA records under the runtime workspace, so repeated failures can bypass the lineage cap.
   - Suggestion: Use `get_lineage_ledger(state_workspace)` here, and add a regression test where runtime and user workspaces differ.

2. [High] RunEvent writes still bypass `runtime_workspace`
   - File: `core/dynamic_orchestrator.py:754`
   - Code: `get_default_store().append(RunEvent(`
   - Issue: F15 intends runtime state to move under `runtime_workspace`, but `get_default_store()` defaults to `runs` unless `AF_CHECKPOINT_DIR` was set before singleton initialization. Step events can still be written under the process CWD/user workspace, contradicting the runtime split.
   - Suggestion: Route RunEvent storage explicitly to `state_workspace/runs`, or initialize an orchestrator-scoped `FileRunEventStore` instead of using the global default.

3. [Medium] NEXT_STEPS still lists the fixed ISE gap as unresolved
   - File: `NEXT_STEPS.md:78`
   - Code: `ISELoop.run_mission()`이 `fsa.run_mission()`에 `runtime_workspace`를 전달하지 않음
   - Issue: `core/ise_loop.py:37-48` now accepts and forwards `runtime_workspace`, so this backlog item is stale. It will mislead the next session into redoing or splitting out already-applied work.
   - Suggestion: Move this item to completed or remove it from residual backlog.

### Comparison with Known Issues

- The `core/ise_loop.py` change directly addresses the known `NEXT_STEPS.md` F15 ISE gap.
- The lineage mismatch repeats a known AF pattern: workspace/runtime state split is only partially applied, causing guards to read a different state root than writers.
- No non-atomic write or shell injection was introduced in `core/ise_loop.py`.

### Positive Observations

- `ISELoop.run_mission()` preserves backward caller compatibility by adding `runtime_workspace` with a default of `None`.
- `tests/test_fsa_runtime_workspace.py` specifically covers ISE forwarding, and `pytest tests/test_fsa_runtime_workspace.py tests/test_ise_integration.py -q` passed: 9 tests. `py_compile` also passed for the changed runtime files.