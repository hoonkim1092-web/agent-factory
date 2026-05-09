# Code Review: check_design_pending

> Source: scripts/check_design_pending.py
> Date: 2026-04-29 14:51
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. Multiple High/Medium issues exist that should be addressed before this script is relied upon in production, but do not block merge with documented risks.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] Stale entries inflate count AND newest-mtime gating suppresses older actionable docs
- **Critic**: "`n = len(entries)` counts ALL `.json` files ever written to the queue directory, misleading the user about how many docs need review."
- **Cross**: "Script gates the entire queue on the newest file's mtime — if a fresh edit arrives, the hook exits and older already-actionable docs are silently skipped."
- **Judgment**: Both reviewers independently converge on the same root: the queue scan has no concept of "already-fired" vs "actionable." Critic's fix (filter by `fired` marker) and Cross's fix (filter by `MIN_BATCH_INTERVAL_SEC`) are complementary and both needed. Evidence in `check_design_pending.py:94-114` confirms both problems coexist.
- **Action Required**: Replace the current scan/count logic with a two-stage filter: (a) exclude entries whose `fn` is already in `fired` with a mtime ≤ `fired[fn]`; (b) of remaining entries, exclude those newer than `MIN_BATCH_INTERVAL_SEC` (not yet settled). Report only the resulting `actionable_entries`.

---

#### 2. [ACCEPT] [Medium] Silent `_save_fired` failure causes infinite re-fire
- **Critic**: "`except Exception: pass` in `_save_fired` swallows disk/permission failures. On next prompt `_load_fired` returns `{}`, `last_fired_at` is `0` (falsy), suppression is skipped, and the script fires indefinitely."
- **Cross**: Not flagged.
- **Judgment**: Evidence is unambiguous — `check_design_pending.py:50-65` contains a bare `except Exception: pass`. The re-fire path via `last_fired_at = 0` → `if last_fired_at:` short-circuit failing is confirmed by reading lines 101-103. Single-reviewer but code speaks clearly.
- **Action Required**: Replace `pass` with `print(f"[check_design_pending] WARNING: fired marker save failed: {exc}", file=sys.stderr)` at minimum.

---

#### 3. [ACCEPT] [Medium] Non-atomic write in `enqueue()` — corrupt queue entry persists forever
- **Critic**: "Direct `open(..., 'w') + json.dump` in `design_review_utils.py:217-218` is non-atomic. A mid-write kill leaves a corrupt `.json` that is never cleaned up and continues to pollute `len(entries)` indefinitely."
- **Cross**: Not flagged.
- **Judgment**: Confirmed M10 pattern (already listed as known issue in `code-review.md §3.3`). The corrupt-file-survives-forever consequence is distinct from prior M10 instances and makes Finding 1's count inflation worse. Contrast with `_save_fired()` which correctly uses `tempfile + os.replace`.
- **Action Required**: Apply the same `tempfile.mkstemp → os.replace` pattern used in `_save_fired()` to the `enqueue()` write path.

---

#### 4. [ACCEPT] [Medium] `FIRED_MARKER` dict accumulates unboundedly; 12-char MD5 prefix collision risk
- **Critic**: "One permanent entry per design doc with no TTL or eviction. 12-char MD5 hash prefix (`pathhash()`) is collision-prone on long-running projects — a collision silently suppresses a legitimate review signal."
- **Cross**: Not flagged.
- **Judgment**: The unbounded growth alone is a maintenance concern; the hash collision risk elevates it. 12 hex chars = 48-bit space; with hundreds of docs over months, collision probability is non-trivial. Evidence: `design_review_utils.py:187` confirms 12-char prefix; `check_design_pending.py:118-119` confirms no pruning on save.
- **Action Required**: Add TTL pruning on save (e.g., discard entries older than `MIN_BATCH_INTERVAL_SEC * 10`). Consider increasing hash length to 24+ chars or using full SHA256.

---

#### 5. [ACCEPT] [Medium] Legacy design queue path (`.af_review_queue/pending/`) not scanned
- **Critic**: Not flagged.
- **Cross**: "Hook only scans `.af_review_queue/pending/design`, but `design_review_watcher.py:378` and `design_review_utils.py:343-358` still support legacy entries in `.af_review_queue/pending/`. Producers using the legacy path will never trigger `[af-design-review-pending]`."
- **Judgment**: Cross reviewer provides specific file/line evidence. The watcher explicitly handles the legacy path for backward compatibility, making it a supported producer path. The hook's omission is a functional gap, not a theoretical one.
- **Action Required**: Import `PENDING_DIR` from `core.design_review_utils` and include it in the scan, or delegate to a shared helper that mirrors `design_review_watcher.process_queue()`'s path logic.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Stale entries inflate count + newest-mtime gating suppresses older docs | High | ACCEPT | Both |
| 2 | Silent `_save_fired` failure → infinite re-fire | Medium | ACCEPT | Critic |
| 3 | Non-atomic `enqueue()` write → corrupt entry persists | Medium | ACCEPT | Critic |
| 4 | `FIRED_MARKER` unbounded growth + hash collision risk | Medium | ACCEPT | Critic |
| 5 | Legacy queue path not scanned | Medium | ACCEPT | Cross |

---

### Recommendations

- **Fix Finding 1 first** — it is the most user-visible bug and the fix will touch the same code region as Findings 2 and 4, so do them together.
- Apply `tempfile + os.replace` to `enqueue()` (Finding 3) — it is a one-line pattern already present in the same file.
- Add stderr logging to `_save_fired` exception handler (Finding 2) — one-line fix, zero risk.
- Add legacy path scan using `PENDING_DIR` (Finding 5) — prevents silent loss of older queue entries.
- TTL pruning + longer hash (Finding 4) — low urgency but do it before the project accumulates hundreds of docs.