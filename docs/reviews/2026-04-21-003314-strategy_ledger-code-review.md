# Code Review: strategy_ledger

> Source: core/memory_system/strategy_ledger.py
> Date: 2026-04-21 00:33
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. Five accepted findings (2 Medium from Critic, 2 Medium from Cross, 1 Low from Critic). Safe to merge with documented risks and follow-up tickets.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [Medium] Empty batch triggers spurious disk write
- **Critic**: "When `entries=[]`, lock is acquired, eviction runs, and `_save()` writes file unchanged."
- **Cross**: Not flagged.
- **Judgment**: Strong evidence — current caller guards with `if _batch:` in `pipeline.py:994`, but the method has no internal guard. Any future caller omitting that check incurs a no-op atomic write. Defensive fix is trivial.
- **Action Required**: Add `if not entries: return` as the first line of `record_role_batch()` body, before `with self._lock`.

---

#### 2. [ACCEPT] [Medium] Mid-loop exception leaves in-memory/on-disk state diverged
- **Critic**: "If an exception is raised mid-iteration, entries 1..N-1 have mutated `_role_assignments` but `_save()` is never reached. On process restart, partial updates are lost."
- **Cross**: Not flagged.
- **Judgment**: Strong evidence — single-entry methods save after each mutation so they can't exhibit this gap, but the batch loop has no guard. A `None` pattern or bad tuple from a caller causes silent partial commit to memory with no disk persistence.
- **Action Required**: Add entry validation at the top of the loop:
  ```python
  for pattern, owner_role, project_id, succeeded in entries:
      if not isinstance(pattern, str) or not pattern:
          continue
  ```

---

#### 3. [ACCEPT] [Medium] Synthetic/fallback module names create self-reinforcing role bias
- **Critic**: Not flagged.
- **Cross**: "Caller puts `_mod.get('name')` into `_batch` before deliverables. `strategy_ledger.py:229` matches on split tokens, so fallback names like `'{owner} Module {index}'` embed the owner's role name — creating a self-reinforcing loop where the ledger learns the already-assigned role back as a signal."
- **Judgment**: Strong evidence — `project_task_board.py:440` confirms fallback name format includes owner name; `strategy_ledger.py:229` uses token-level matching. The bias compounds across runs.
- **Action Required**: In `project_pipeline.py`, exclude fallback/auto-generated module names from `_batch`. Only submit real deliverable strings. If module-name hints are needed, store them under a separate namespace not used by `lookup_best_role()`.

---

#### 4. [ACCEPT] [Medium] 30-character truncation merges unrelated delivery histories
- **Critic**: Not flagged.
- **Cross**: "`project_pipeline.py:989-993` slices `_raw` to 30 chars before passing to `record_role_batch()`. `strategy_ledger.py:205` uses the truncated value as both the persistence key and `deliverable_pattern`. Deliverables sharing a 30-char prefix share the same history entry."
- **Judgment**: Strong evidence — truncation is in the caller, key is the truncated string, and `lookup_best_role()` only sees the abbreviated form. Data loss is irreversible once written.
- **Action Required**: In `project_pipeline.py`, pass the full normalized pattern to `record_role_batch()`. Apply truncation only to display/logging fields. If key size is a concern, use a hash.

---

#### 5. [ACCEPT] [Low] Single post-batch eviction allows transient overshoot past `_MAX_ENTRIES`
- **Critic**: "A batch of 500 new entries on a 950-entry dict grows to 1450 before eviction trims it. Current callers are small (< 50 entries), so actual overshoot is bounded, but nothing in the API contract enforces this."
- **Cross**: Not flagged.
- **Judgment**: Acceptable for current callers, but the API contract is silent on batch size constraints. Low risk now, non-trivial risk if the API is reused.
- **Action Required**: Add a docstring note to `record_role_batch()`: "Eviction runs once after all entries are inserted; callers should not submit batches significantly larger than `_MAX_ENTRIES`."

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Empty batch spurious disk write | Medium | ACCEPT | Critic |
| 2 | Mid-loop exception / partial state divergence | Medium | ACCEPT | Critic |
| 3 | Synthetic module names cause role bias loop | Medium | ACCEPT | Cross |
| 4 | 30-char truncation merges unrelated histories | Medium | ACCEPT | Cross |
| 5 | Post-batch eviction allows transient overshoot | Low | ACCEPT | Critic |

---

### Recommendations

1. **record_role_batch() guard** — add `if not entries: return` before acquiring the lock.
2. **Entry validation** — skip entries where `pattern` is not a non-empty string; log a warning.
3. **Caller cleanup in project_pipeline.py** — strip fallback module names (those matching `"{owner} Module {index}"` pattern) from `_batch` before calling `record_role_batch()`.
4. **Remove 30-char truncation from persistence path** — pass full pattern to `record_role_batch()`; truncate only for logging.
5. **Docstring note** — document the single-eviction behavior and caller batch-size expectation on `record_role_batch()`.