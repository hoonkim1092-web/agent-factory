# Code Review: nightly_state

> Source: core/nightly_state.py
> Date: 2026-04-18 17:04
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

Three ACCEPT findings (2 High, 1 Medium). No Critical. All High findings feed the same silent-reset vulnerability via `load_state()`'s bare `except Exception:`.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] `int(None)` crash on `consecutive_tick_failures=null`

- **Critic**: "`data.get('consecutive_tick_failures', 0)` returns `None` (not default) when key exists with JSON `null`. `int(None)` raises `TypeError`; `max(0, ...)` never executes."
- **Cross**: not flagged directly (captured under shape-validation gap)
- **Judgment**: Python fact — `{"consecutive_tick_failures": null}` reproduces instantly. The `max(0, int(...))` pattern adds false safety. Crash feeds `load_state():141-146` bare `except`, silently resetting all watchdog escalation state.
- **Action Required**: Change line ~127 to `int(data.get("consecutive_tick_failures") or 0)`.

---

#### 2. [ACCEPT] [High] Shape guard missing for `task_retry_count`, `watchdog`, `budget`

- **Critic**: not flagged
- **Cross**: "`NightlyState.from_dict({'task_retry_count': ['bad']})` → `AttributeError` on `.items()`. `{'watchdog': [1]}` and `{'budget': [1]}` → `AttributeError` in sub-`from_dict`. All swallowed by `load_state()` bare except, resetting nightly state."
- **Judgment**: Three concrete reproductions provided. `raw_retry.items()` is called without an `isinstance(raw_retry, dict)` guard. `watchdog`/`budget` pass any truthy value directly to `WatchdogState.from_dict()`/`BudgetState.from_dict()`. This mirrors the silent-reset pattern documented at `code-review.md:280`/`:340`.
- **Action Required**: Add `isinstance(raw_retry, dict)` guard before `.items()` call (fallback to `{}`). Same for `watchdog` and `budget` before sub-`from_dict()` calls.

---

#### 3. [ACCEPT] [Medium] `active_assignments` inner entries unvalidated — consumer crash

- **Critic**: not flagged
- **Cross**: "`NightlyState.from_dict({'active_assignments': {'backend': 'oops'}})` succeeds, but `scripts/nightly_summary.py:40-42` immediately raises `AttributeError: 'str' object has no attribute 'get'`. `nightly_tick.py:217-218` calls `write_summary()` every tick, so a single bad entry kills the whole tick."
- **Judgment**: Evidence is precise and cross-referenced. `safe_assignments` only validates the outer dict type, not inner entry shape. Consumer crash is a tick-level failure, not just a load failure.
- **Action Required**: Deep-normalize `active_assignments` — filter or reconstruct entries to ensure each value is a dict. Reference `core/continuity/manifest_store.py:97` `_normalized_active_assignments()` as candidate shared helper.

---

#### 4. [HOLD] [Low] Silent drop of string-encoded retry counts

- **Critic**: "String values like `'3'` are silently dropped; task restarts at retry 0."
- **Cross**: not flagged
- **Judgment**: JSON spec guarantees numbers deserialize as `int`/`float`, so this path is only reachable via manual state edits or cross-version migration. Evidence is speculative, not reproduced.
- **Question for Author**: Is there any migration path (older snapshot format, manual override) that could produce `"task_a": "3"` in the state file? If yes, promote to Medium and add a warning log in the else-path.

---

#### 5. [HOLD] [Low] `bool` subclass passes `isinstance(v, (int, float))` filter

- **Critic**: "`True`/`False` stored as retry counts yield `1`/`0` with no warning."
- **Cross**: not flagged
- **Judgment**: Practically unreachable — JSON `true`/`false` only appears here via a serialization bug elsewhere. No concrete reproduction path provided.
- **Question for Author**: Is there any codepath that could write boolean values to `task_retry_count`? If no, this is noise; if yes, add `and not isinstance(v, bool)` guard.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `int(None)` crash on `consecutive_tick_failures=null` | High | ACCEPT | Critic |
| 2 | Shape guard missing for `task_retry_count`/`watchdog`/`budget` | High | ACCEPT | Cross |
| 3 | `active_assignments` inner entries unvalidated | Medium | ACCEPT | Cross |
| 4 | Silent drop of string-encoded retry counts | Low | HOLD | Critic |
| 5 | `bool` subclass passes int filter | Low | HOLD | Critic |

---

### Recommendations

- **Fix 1**: `int(data.get("consecutive_tick_failures") or 0)` — covers both missing and explicit-null cases.
- **Fix 2**: Add `if not isinstance(raw_retry, dict): raw_retry = {}` before the dict comprehension. Wrap `data.get("watchdog")` and `data.get("budget")` with `isinstance(..., dict) or {}` before sub-`from_dict()`.
- **Fix 3**: Filter `safe_assignments` entries: `{k: v for k, v in raw_assignments.items() if isinstance(v, dict)}`.
- **Deferred**: ACCEPT-1 (`load_state()` bare `except Exception:`) from prior review remains unaddressed and directly amplifies all three High/Medium findings above — findings 1–3 would be low-risk if that catch were narrowed to `json.JSONDecodeError`.