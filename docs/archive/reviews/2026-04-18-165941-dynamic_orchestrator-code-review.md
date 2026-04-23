# Code Review: dynamic_orchestrator

> Source: core/dynamic_orchestrator.py
> Date: 2026-04-18 16:59
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. Three High/Medium findings exist with concrete evidence. Critic could not review (no diff provided), so all findings are single-source — but Cross review evidence is specific and verifiable.

---

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [High] Nightly path drops `task_id`, forcing unsafe fallback matching

- **Critic**: not flagged (no diff available)
- **Cross**: "`scripts/nightly_tick.py:160-164` forwards only `role` and `subtask`; `core/project_task_board.py:659` falls back to instruction matching when `task_id` absent; `core/dynamic_orchestrator.py:446` explicitly documents instruction fallback was removed as unsafe."
- **Judgment**: Evidence is precise — three cross-referenced locations confirm the gap. `task_id` is available from `_dispatch_from_board()` but silently dropped, degrading into the unsafe path the orchestrator was explicitly hardened against.
- **Action Required**: In `scripts/nightly_tick.py:160-164`, thread `task_id` from `task_info["task_id"]` into `_execute_agent_task()`. Use same `task_id` as retry key.

---

#### 2. [ACCEPT] [High] `restore_from()` hydrates nightly snapshot into incompatible orchestrator schema

- **Critic**: not flagged
- **Cross**: "Nightly state stores `active_assignments[role] = {subtask_id, started_at, tick_id, result_path}` (`nightly_tick.py:135`), but orchestrator expects `active_assignments[run_id] = {role, subtask, workspace, task_id?}` (`dynamic_orchestrator.py:675,682`). `OrchestratorManifestStore._normalized_active_assignments()` reads different keys and produces blank fields (`manifest_store.py:97`)."
- **Judgment**: The key schema mismatch is proven with specific line references. The nightly retry key (`role:subtask_id`) also diverges from orchestrator's retry key (`task_id` or `role:instruction[:60]`). Silent data corruption on restore.
- **Action Required**: Add a normalization step inside `restore_from()` (`core/dynamic_orchestrator.py:85`) converting nightly-format entries to orchestrator-native shapes, or stop hydrating `active_assignments`/`task_retry_count` until contracts are unified.

---

#### 3. [ACCEPT] [Medium] No test coverage for `restore_from()` with real `NightlyState` payload

- **Critic**: not flagged
- **Cross**: "No `nightly_tick`/`restore_from` tests found. `pytest -q` reports `1 failed, 8 passed`; failing test does not touch the new classmethod."
- **Judgment**: The schema mismatch in finding #2 would ship silently without this test. Single-reviewer but the gap is objectively confirmed by the failing test suite report.
- **Action Required**: Add unit test for `restore_from()` using `NightlyState.to_dict()` snapshot. Add integration test verifying `task_id`/retry propagation through `nightly_tick` dispatch.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Nightly path drops `task_id`, unsafe fallback | High | ACCEPT | Cross |
| 2 | `restore_from()` schema mismatch | High | ACCEPT | Cross |
| 3 | No test for `restore_from()` | Medium | ACCEPT | Cross |

---

### Recommendations

- Fix `nightly_tick.py:160-164` to pass `task_id` through to `_execute_agent_task()`.
- Add normalization inside `restore_from()` at `dynamic_orchestrator.py:85` before writing nightly snapshot fields into orchestrator internals.
- Standardize retry key format across nightly and orchestrator — commit to `task_id` as the canonical key.
- Write `test_restore_from_nightly_state()` exercising the full round-trip: `NightlyState.to_dict()` → `restore_from()` → assert `active_assignments` shape.
- Re-run `pytest` after fixes; resolve the pre-existing 1 failing test independently.