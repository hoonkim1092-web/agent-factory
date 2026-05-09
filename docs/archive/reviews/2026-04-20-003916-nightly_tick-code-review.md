# Code Review: nightly_tick

> Source: scripts/nightly_tick.py
> Date: 2026-04-20 00:39
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings, but 4 accepted issues across the two reviewers — two in the diff itself (wrong exception type, incomplete platform guard) and two pre-existing bugs surfaced by the cross reviewer (state persistence split, retry count drop).

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [Medium] Wrong exception type for platform guard
- **Critic**: "`ImportError` is semantically reserved for module-loading failures; certain harnesses will swallow it silently (e.g. `try: import nightly_tick except ImportError: pass`), masking the guard on Windows."
- **Cross**: Not flagged.
- **Judgment**: Strong evidence — Python's import machinery does suppress `ImportError` in try/except import guards, which is a real risk if any integration test or lazy-importer wraps this module. The semantics are clearly wrong regardless of whether the silent-swallow path is currently exercised.
- **Action Required**: `nightly_tick.py:24` — replace `raise ImportError(...)` with `raise RuntimeError("nightly_tick.py는 macOS/Linux 전용입니다. 현재 플랫폼: " + sys.platform)`.

---

#### 2. [ACCEPT] [Medium] Platform guard is win32-only, not POSIX-allowlist
- **Critic**: "`fcntl` is unavailable on Cygwin (`sys.platform == 'cygwin'`), MSYS2, and some embedded builds. The comment explicitly says 'macOS/Linux 한정' so a positive allowlist is both more accurate and forward-safe."
- **Cross**: Not flagged directly; consistent with their concern about non-POSIX environments.
- **Judgment**: The diff comment literally says "macOS/Linux 한정" but the guard only blocks `win32`. The allowlist form is strictly more correct and aligns the guard with the stated intent.
- **Action Required**: `nightly_tick.py:23` — replace `if sys.platform == "win32":` with `if sys.platform not in ("darwin", "linux"):`. Combine with fix #1 above into a single change.

---

#### 3. [ACCEPT] [High] Mid-tick `save_state` forks the source of truth when `active_workspace != ws`
- **Critic**: Not flagged.
- **Cross**: "`_dispatch_actions()` saves state to `state.active_workspace` (the project path) while `tick_once()` loads and finally saves the canonical snapshot at `ws`. Crash recovery and subsequent ticks therefore read stale state from `ws`."
- **Judgment**: Cross reviewer provides line-level evidence across `nightly_tick.py:155,225,242-243,253`, `run_factory_cli.py:186-197`, and `nightly_state.py:3-5,150-166`. The split write is a real state-divergence bug under `af nightly-start --project ...`. Elevated to High because it silently corrupts recovery state rather than failing loudly.
- **Action Required**: Separate `state_workspace` from `execution_workspace`. All `load_state`/`save_state` calls must use `ws`; pass `active_workspace` only to board/orchestrator calls. Add regression test asserting only `ws/.af/state_snapshot.json` changes when `active_workspace != ws`.

---

#### 4. [ACCEPT] [High] `_task_retry_count` is not synchronized back to `NightlyState`, so retry gate resets every tick
- **Critic**: Not flagged.
- **Cross**: "`DynamicOrchestrator._task_retry_count` is incremented on failure but never written back to `state.task_retry_count` on the normal failure path. `save_state` therefore persists stale zeroes, and the `_max_task_retries` gate never accumulates across ticks."
- **Judgment**: Cross reviewer traces the full path: `restore_from()` reads from snapshot, `_execute_agent_task()` increments the in-memory counter, but the normal `_run_task()` return path (`nightly_tick.py:203-205`) drops it before `save_state`. The design doc itself (`docs/2026-04-18-nightly-autonomous-pipeline.md:182-184`) specifies this field must be persisted. Elevated to High because the safeguard against infinite retries is silently broken.
- **Action Required**: After every `_run_task()` call, sync `state.task_retry_count = dict(orch._task_retry_count)` before `save_state`. Add a multi-tick test that forces 3+ internal failures and asserts the 4th tick is suppressed by `_max_task_retries`.

---

### Summary Table

| # | Title | Severity | Verdict | Source | In Diff? |
|---|-------|----------|---------|--------|----------|
| 1 | Wrong exception type for platform guard | Medium | ACCEPT | Critic | Yes |
| 2 | Platform guard is win32-only, not POSIX-allowlist | Medium | ACCEPT | Critic | Yes |
| 3 | Mid-tick save_state forks source of truth | High | ACCEPT | Cross | Pre-existing |
| 4 | Retry count not persisted across ticks | High | ACCEPT | Cross | Pre-existing |

---

### Recommendations

- **Fix #1 + #2 together** (single line change): replace the guard with `if sys.platform not in ("darwin", "linux"): raise RuntimeError(...)`.
- **Fix #3**: audit all `save_state` call sites in `nightly_tick.py` and `run_factory_cli.py`; pin every state persistence operation to `ws`, not `state.active_workspace`.
- **Fix #4**: add `state.task_retry_count = dict(orch._task_retry_count)` after each `_run_task()` return before any `save_state` — on both the success and failure paths.
- **Tracking**: the bug ID `F3` referenced in the new comment has no entry in `code-review.md`'s registry (C1–C5, H1–H7, M1–M10). Add it for consistency.
- Fixes #3 and #4 are pre-existing but discovered during this review; they should ship in the same branch before merge to avoid a silent correctness regression.