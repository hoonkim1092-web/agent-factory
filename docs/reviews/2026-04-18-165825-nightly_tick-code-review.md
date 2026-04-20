# Code Review: nightly_tick

> Source: scripts/nightly_tick.py
> Date: 2026-04-18 16:58
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. High severity issues exist in both state management (`nightly_state.py`) and orchestration logic (`nightly_tick.py`) that should be resolved before relying on the nightly pipeline in production.

---

### Aggregated Findings (9 total)

#### 1. [ACCEPT] [High] `load_state()` bare `except Exception:` — silent state reset
- **Critic**: "파일 손상 시 예외가 삼켜지고 watchdog 레벨이 조용히 `OK`로 리셋. 3회 연속 지적."
- **Cross**: not flagged
- **Judgment**: Critic evidence is direct and concrete — `core/nightly_state.py:145` swallows all exceptions and returns a fresh `NightlyState()`. A corrupted snapshot silently resets `STALL_3`/`CHECKPOINT_ONLY` escalation state, neutralizing the watchdog. Single-reviewer but strong evidence; confirmed pattern.
- **Action Required**: Add `logging.getLogger(__name__).warning("state_snapshot load failed, starting fresh: %s", e)` before `return NightlyState()`.

#### 2. [ACCEPT] [High] 14-minute hard deadline not enforced for in-flight tasks
- **Critic**: not flagged
- **Cross**: "hard-limit check only at loop top; task started near minute 14 can still run full 10-minute soft timeout; SIGTERM handler only flips a flag."
- **Judgment**: Cross evidence cites three specific lines (`nightly_tick.py:130`, `168`, `110` in docs). The design doc says SIGTERM should interrupt work — the implementation contradicts it. Clear architectural regression.
- **Action Required**: Compute remaining wall-clock budget before each `_run_task()`; use `min(SOFT_DEADLINE_SEC, remaining)` for `wait_for()`; make SIGTERM cancel the current task coroutine.

#### 3. [ACCEPT] [High] Nightly budget accounting detached from actual token recording
- **Critic**: not flagged
- **Cross**: "`state.budget.consumed_tokens` is never updated in nightly mode; `core.run_budget` is never initialized; `--budget` flag has no runtime effect."
- **Judgment**: Cross traces the full call chain (`run_factory_cli.py:195` → `agent_runner.py:914` → `run_budget.py:51`). The budget guard at `nightly_tick.py:196` reads a counter that is never written. The feature is documented but non-functional.
- **Action Required**: Initialize `set_run_budget()` from `state.budget.max_tokens` at tick start; persist `get_run_budget().consumed` back into `state.budget.consumed_tokens` after each task.

#### 4. [ACCEPT] [Medium] `mark_alert()` non-atomic file write
- **Critic**: "`save_state()` uses tempfile+`os.replace`; `mark_alert()` uses direct `open(..., 'w')` — inconsistent pattern. Process crash mid-write leaves partial flag file."
- **Cross**: not flagged
- **Judgment**: Pattern inconsistency within the same file (`nightly_state.py:195-196`). Matches existing code-review pattern M10. Evidence is direct.
- **Action Required**: Replace direct `open()` write with tempfile+`os.replace` pattern or `Path.write_text()` + `Path.rename()`.

#### 5. [ACCEPT] [Medium] `_write_json_file()` silently suppresses write failures for derived files
- **Critic**: "쓰기 실패가 억제되어 `watchdog_state.json`, `budget_state.json`, `lineage_ledger.json`이 stale 상태로 남음."
- **Cross**: not flagged
- **Judgment**: `core/nightly_state.py:184-188` cleans up the temp file but never re-raises or logs. `save_state()` returns success while derived files are stale. Critic evidence is direct.
- **Action Required**: After temp file cleanup, either re-raise the original exception or add `logging.warning(...)` at minimum.

#### 6. [ACCEPT] [Medium] Lock-contention exit code triggers launchd restart
- **Critic**: not flagged
- **Cross**: "`tick_once()` returns `1` on benign flock contention; plist has `KeepAlive.SuccessfulExit=false` → overlap triggers immediate relaunch loop."
- **Judgment**: Cross cites `nightly_tick.py:183` and `install_launchd.sh:57`. The combination turns a normal overlap into a tight restart loop.
- **Action Required**: Return `0` for lock-contention path, or remove `KeepAlive` and rely on `StartInterval`.

#### 7. [ACCEPT] [Medium] `CHECKPOINT_ONLY` watchdog level never gates dispatch
- **Critic**: not flagged
- **Cross**: "`watchdog.is_checkpoint_only()` is defined but has no caller; ticks continue dispatching normally even after escalation."
- **Judgment**: `core/watchdog.py:60` defines the method, `nightly_tick.py:196` only gates budget, not watchdog state. The escalation level becomes decorative.
- **Action Required**: Add `state.watchdog.is_checkpoint_only()` gate in `tick_once()` before `_dispatch_actions()`.

#### 8. [ACCEPT] [Medium] Completed board misclassified as stall
- **Critic**: not flagged
- **Cross**: "`_dispatch_actions()` returns `False` for both idle and complete; `tick_once()` escalates watchdog on every `False` — a finished project drifts to `CHECKPOINT_ONLY`."
- **Judgment**: Cross cites `project_task_board.py:556`, `nightly_tick.py:94`, and `215`. Logic flaw is clear.
- **Action Required**: Return a tri-state (`progress` / `idle` / `complete`) from `_dispatch_actions()`, or detect completion before escalating watchdog.

#### 9. [ACCEPT] [Low] `--workspace` not preserved in generated launchd plist
- **Critic**: not flagged
- **Cross**: "`nightly-start --workspace X` saves state under `X`; generated plist hardcodes `--workspace <repo root>`; post-handoff ticks use different state path."
- **Judgment**: Cross cites `run_factory_cli.py:186` vs `install_launchd.sh:36`. Workspace mismatch is a configuration bug — functional impact depends on whether users override workspace.
- **Action Required**: Pass selected workspace into `install_launchd.sh` and write it into the plist `ProgramArguments`.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `load_state()` bare except — silent reset | High | ACCEPT | Critic |
| 2 | Hard deadline not enforced for in-flight tasks | High | ACCEPT | Cross |
| 3 | Budget accounting detached from token recording | High | ACCEPT | Cross |
| 4 | `mark_alert()` non-atomic write | Medium | ACCEPT | Critic |
| 5 | `_write_json_file()` silently suppresses failures | Medium | ACCEPT | Critic |
| 6 | Lock-contention returns 1, triggers launchd restart | Medium | ACCEPT | Cross |
| 7 | `CHECKPOINT_ONLY` never gates dispatch | Medium | ACCEPT | Cross |
| 8 | Completed board misclassified as stall | Medium | ACCEPT | Cross |
| 9 | `--workspace` lost in launchd plist | Low | ACCEPT | Cross |

---

### Recommendations

- **Fix #1 first** — three-session repeat finding; one-line logging fix with zero risk.
- **Fix #3 before enabling `--budget`** — the flag silently does nothing; initialize `run_budget` at tick start and persist consumed tokens back to state.
- **Fix #8 before fixing #7** — `CHECKPOINT_ONLY` gating (#7) depends on the stall escalation logic being correct; if completed boards are misclassified as stalls, gating would incorrectly block completed projects.
- **Fix #2 and #6 together** — both involve deadline/scheduling contract; simplest fix is `return 0` on lock-contention + `min(SOFT_DEADLINE_SEC, remaining)` budget in `_run_task`.
- **Fixes #4 and #5** can be batched as a single "atomic write hygiene" commit in `nightly_state.py`.
- **Fix #9** is low-risk config change; include in the launchd-related commit with #6.