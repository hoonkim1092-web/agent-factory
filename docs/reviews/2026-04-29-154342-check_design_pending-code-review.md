# Code Review: check_design_pending

> Source: scripts/check_design_pending.py
> Date: 2026-04-29 15:43
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings, but Cross flagged a **High-severity architectural ownership conflict** (watcher vs prompt-hook race on the same queue), and Critic flagged two Medium correctness gaps (no dict-type validation on marker JSON, no cross-process lock around read-modify-write). Mergeable with documented risks; address the High before extending this code path further.

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [High] Prompt hook and watcher both consume the same `pending/design` queue
- **Critic**: not flagged
- **Cross**: "watcher quiet period 8s consumes queue before this hook's 90s gate fires" — `design_review_watcher.py:381,413` vs `check_design_pending.py:120`
- **Judgment**: Evidence is concrete and cross-references real code paths. PostToolUse → `design_review_trigger.py:77-78` → `ensure_watcher()` runs in parallel with this UserPromptSubmit script reading the same queue. With 8s vs 90s windows, the watcher will almost always win, making this script's gate effectively dead code most of the time, while occasionally racing on identical entries.
- **Action Required**: Pick one owner. Either (a) PostToolUse enqueues only and does NOT call `ensure_watcher()` for design docs (let UserPromptSubmit own execution), or (b) leave the watcher as owner and have `check_design_pending.py` read watcher results instead of polling the same queue. Document the chosen ownership in the script docstring.

#### 2. [ACCEPT] [Medium] No cross-process lock around fired-marker read-modify-write
- **Critic**: "T1 reads {}, T2 reads {}, T1 writes {A:now}, T2 writes {B:now} — A is lost" (lines 102-141)
- **Cross**: not flagged
- **Judgment**: Real concurrency gap. Hook can fire from multiple Claude sessions on the same workspace, or interleave with the watcher path identified in Finding #1. Repo already has `core/file_lock.py` for exactly this pattern, so the fix is mechanical.
- **Action Required**: Wrap `_load_fired` → mutate → `_save_fired` block with `core/file_lock.py` on `FIRED_MARKER + ".lock"`.

#### 3. [ACCEPT] [Medium] `_load_fired` returns `json.load` result without dict validation
- **Critic**: "if marker is `null`/`[]`/string, `fired.items()` raises AttributeError; main() has no top-level try/except, so hook exits non-zero — violating 'always exit 0' contract" (lines 45-51, 103)
- **Cross**: not flagged
- **Judgment**: Legitimate — the docstring explicitly promises non-blocking exit, and an unguarded `.items()` on non-dict breaks that promise on any corruption. Minimal fix.
- **Action Required**: In `_load_fired`, add `if not isinstance(data, dict): return {}` before return. As belt-and-suspenders, also wrap `main()` in `try/except Exception` at the `__main__` block to guarantee `sys.exit(0)`.

#### 4. [ACCEPT] [Medium] No existence check on `file_path` before announcing/marking fired
- **Critic**: not flagged
- **Cross**: "watcher guards with existence check at `design_review_watcher.py:395-398`; this script doesn't" (line 93)
- **Judgment**: Evidence cites a sibling code path that already implements the guard, making this an obvious parity gap. Deleted/renamed docs get announced and burn a `fired` slot.
- **Action Required**: Before appending a candidate, `os.path.exists(os.path.join(ws, file_path))`. If missing, skip without marking fired (and optionally remove the stale queue JSON to mirror watcher behavior).

#### 5. [ACCEPT] [Low] Wall-clock arithmetic vulnerable to clock skew
- **Critic**: "negative elapsed from NTP/DST → entry held forever; forward jump → premature fire" (lines 120-122)
- **Cross**: not flagged
- **Judgment**: Real but rare. `time.monotonic()` isn't usable across processes, so full fix isn't possible — clamping is the right pragmatic mitigation.
- **Action Required**: `elapsed = max(0.0, now - ts)`. Optionally cap forward jumps. One-line change.

#### 6. [ACCEPT] [Low] Magic numbers (`5`, `10`) and `existing_fnames` includes pre-parse failures
- **Critic**: timeout=5, `[:10]`, `+{n-10}` (line 36, 131-133); `existing_fnames.add` runs before JSON load succeeds (lines 84-96)
- **Cross**: not flagged
- **Judgment**: Minor maintenance hygiene. The `existing_fnames` ordering is self-correcting on next run, so very low impact.
- **Action Required**: Name `GIT_TOPLEVEL_TIMEOUT_SEC = 5`, `MAX_DISPLAYED_FILES = 10`. Move `existing_fnames.add(fname)` after successful JSON parse.

### Rejected (carried over from Cross, no merge)
- **Newest-file suppression bug**: Cross verified per-entry filtering at lines 114-123 already fixes it. No action.
- **External callers with broken signatures**: Cross verified the script is invoked via argv from `.claude/settings.local.json`, not imported. No action.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Watcher/prompt-hook ownership conflict | High | ACCEPT | Cross |
| 2 | No cross-process lock on marker R-M-W | Medium | ACCEPT | Critic |
| 3 | No dict-type validation in `_load_fired` | Medium | ACCEPT | Critic |
| 4 | No existence check on `file_path` | Medium | ACCEPT | Cross |
| 5 | Wall-clock skew not clamped | Low | ACCEPT | Critic |
| 6 | Magic numbers + `existing_fnames` ordering | Low | ACCEPT | Critic |

### Recommendations
- **Decide ownership first** (Finding #1). Findings #2 and #4 partially dissolve once one process owns the queue. Document the choice in the script docstring.
- **Apply fixes in this order**: #1 (architectural) → #3 (one-line robustness, restores exit-0 contract) → #2 (file_lock wrap) → #4 (existence guard) → #5 (clamp) → #6 (constants).
- **Test gap**: add a unit test that writes a non-dict (`null`, `[]`) to `.design_review_fired.json` and asserts the script still exits 0. The current "always exit 0" promise is documented but not enforced anywhere.