# Code Review: nightly_tick

> Source: scripts/nightly_tick.py
> Date: 2026-04-20 00:19
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

Cross review surfaced 4 substantive bugs in `scripts/nightly_tick.py` with strong file:line evidence. Critic abstained because the dispatch claimed "no diff," but the cross reviewer examined the actual file state and produced verifiable findings against the project's own design contract. Two findings break core nightly-pipeline invariants (progress accounting and crash recovery) — must fix before this pipeline can be trusted.

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [High] Failed task executions counted as progress
- **Critic**: not reviewed (claimed no diff)
- **Cross**: `scripts/nightly_tick.py:151` — `_run_task()` returns normally even when `_execute_agent_task()` swallows failures, so `made_progress=True` resets watchdog and clears alerts on failure
- **Judgment**: Strong evidence. Cross traced `core/dynamic_orchestrator.py:657` confirming `_execute_agent_task()` has no return value and handles failures internally. Verified with fake-callee test.
- **Action Required**: `_execute_agent_task()` must return an explicit outcome (`completed`/`failed`/`no_progress`); only mark `made_progress` and call `tick_progress()` / `clear_alert()` on real completion.

#### 2. [ACCEPT] [High] Crash recovery state never persisted mid-dispatch
- **Critic**: not reviewed
- **Cross**: `scripts/nightly_tick.py:142` mutates `state.active_assignments` only in memory; first disk save is at line 234, and exception path at line 250 reloads from disk, discarding the assignment
- **Judgment**: Strong evidence, and directly contradicts `docs/2026-04-18-nightly-autonomous-pipeline.md:189` which specifies unfinished `active_assignments` must survive a crash. Recovery contract is unimplemented.
- **Action Required**: Persist state immediately after adding/mutating `active_assignments[role]` and after each retry bump, then again on clear. Or explicitly drop the recovery contract from `nightly_tick` until implemented end-to-end.

#### 3. [ACCEPT] [High] Windows scheduling installed but nightly path not Windows-safe
- **Critic**: not reviewed
- **Cross**: `scripts/install_scheduler.py:25,153` registers a Windows Task; `scripts/nightly_tick.py:17` imports `fcntl` unconditionally; `scripts/nightly_tick.py:172` builds `run_id = f"{tick_id}:{role}"` where `:` is invalid in Windows paths. `core/dynamic_orchestrator.py:600` and `core/agent_runner.py:851` use `run_id` as path segment.
- **Judgment**: Strong structural evidence; also conflicts with `docs/2026-04-18-nightly-autonomous-pipeline.md:64` ("Phase 0 macOS-only"). Shipping this advertises a broken Windows install.
- **Action Required**: Either gate the Windows branch in `install_scheduler.py` behind a feature flag until portable, or add a platform lock abstraction and sanitize `run_id` (e.g. `safe_id()`) before any filesystem use.

#### 4. [ACCEPT] [Medium] Failure streak/alert only clears on progress, not on healthy idle tick
- **Critic**: not reviewed
- **Cross**: `scripts/nightly_tick.py:250` increments `consecutive_tick_failures` on exception, `:227` resets only on progress, and `:231` (no-progress success) does not clear it. `scripts/nightly_summary.py:47` renders the stale count.
- **Judgment**: Clear asymmetry in state machine. Operator sees false ongoing-failure after recovery.
- **Action Required**: Reset `consecutive_tick_failures` and clear `alert.flag` on any non-exception tick; track `no_progress` via a separate counter. Add regression test: "5 failures → 1 successful idle tick → streak=0".

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Failed tasks counted as progress | High | ACCEPT | Cross |
| 2 | Crash recovery state not persisted | High | ACCEPT | Cross |
| 3 | Windows scheduling structurally broken | High | ACCEPT | Cross |
| 4 | Failure streak doesn't clear on idle success | Medium | ACCEPT | Cross |

### Recommendations
- Fix #1 first — it's the primary integrity gate; without it the watchdog is a no-op.
- Fix #2 together with #1 — both live in `_dispatch_actions()` and together restore the recovery contract.
- For #3, disable the Windows branch in `install_scheduler.py` now; track portable rewrite as separate work.
- For #4, couple the fix with a new e2e test in `tests/e2e/tick_simulator.py` that covers recovery, not just alert creation — current fixtures stub `_dispatch_actions` per `tests/e2e/conftest.py:25` and miss these boundaries.
- Re-dispatch critic with a concrete diff once fixes land; the cross review's REJECT #5 (baseline green, 3 passed) stands as current test state.