# Code Review: check_design_pending

> Source: scripts/check_design_pending.py
> Date: 2026-04-29 15:44
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

I verified the disputed finding by reading the actual code. Critic #3 ("prints one path but fires all") is contradicted by code at `scripts/check_design_pending.py:131-135` which uses `", ".join(c[2] for c in candidates[:10])` — Cross is correct. Critic #2 (docs/patterns missing from EXCLUDE) is verified at `core/design_review_utils.py:43-53`.

## Final Code Review

### Verdict: BLOCK

Two Critical findings (uncaught exception path + spec-violation of `docs/patterns/**` routing) require fixes before merge. One major design issue (watcher starvation race) raised by Cross was missed by Critic.

### Aggregated Findings (10 total)

#### 1. [ACCEPT] [Critical] Uncaught exceptions break the file's "exit 0" contract
- **Critic**: `_load_fired` returns raw `json.load` output without type-validation; non-dict (`null`, `[]`, `"abc"`) crashes the dict-comprehension at L103, and `float(None)`/`float({})` at L117 raises `TypeError`. `main()` does not wrap either, so the hook propagates non-zero — exactly what the L16 docstring forbids.
- **Cross**: not flagged.
- **Judgment**: Verified in code. `_load_fired` (L45-51) only catches load exceptions, returns whatever loaded. Cross's REJECT #5 only addressed missing-`timestamp`-field, which is separately handled at L115-116 — but the non-dict `fired` shape and unguarded `float()` cast are real.
- **Action**: Coerce `fired = raw if isinstance(raw, dict) else {}` after load; wrap `float(fired.get(fname, 0))` in try/except returning 0; consider top-level try/except in `main()` as backstop.

#### 2. [ACCEPT] [Critical] `docs/patterns/**` silently routed to design review (spec violation)
- **Critic**: `core/design_review_utils.py:39` INCLUDE pattern `docs/**/20??-??-??-*.md` matches `docs/patterns/2026-04-18-external-api-3tier.md`; EXCLUDE_PATTERNS at L43-53 has no `docs/patterns/**`. Spec at `docs/2026-04-21-design-doc-review-gate.md:45` explicitly excludes it.
- **Cross**: not flagged.
- **Judgment**: Verified at `core/design_review_utils.py:43-53` — confirmed `docs/patterns` is missing from EXCLUDE list.
- **Action**: Add `"docs/patterns/**"` and `"docs/patterns/*"` to `EXCLUDE_PATTERNS` at `core/design_review_utils.py:53`.

#### 3. [ACCEPT] [High] Watcher starvation race — 90s hook vs 8s watcher consumer
- **Critic** (#7 Medium, framed as duplication): hook uses `MIN_BATCH_INTERVAL_SEC=90`, watcher uses `QUIET_PERIOD_DESIGN=8`; no link.
- **Cross** (#1): Watcher processes `pending/design` and **removes** queue files at `design_review_watcher.py:413` after 8s. The hook only emits after 90s. In normal flow (`scripts/design_review_trigger.py:76-77` calls `enqueue()` + `ensure_watcher()`), the queue is consumed before this hook can fire — the manual notification is starved.
- **Judgment**: Cross's framing is the true defect; Critic identified the same constants but underrated the impact. Severity escalated from Medium → High.
- **Action**: Decide ownership. Either (a) write a separate notification marker at `enqueue()` time that this hook reads (instead of scanning the queue dir the watcher consumes), or (b) drop this hook and update `CLAUDE.md:40` since the watcher already handles the auto-review.

#### 4. [ACCEPT] [High] Failed watcher items bypass the manual fallback
- **Critic**: not flagged.
- **Cross** (#2): `design_review_watcher.py:418-420` catches review errors and moves files to `FAILED_DIR` (L320-332), removing them from `pending/design`. This hook only scans `pending/design`, so failed auto-reviews never trigger the manual prompt.
- **Judgment**: Strong evidence; this is a real silent-failure mode for the manual-fallback contract.
- **Action**: Have watcher write a notification file on failure, or have this hook also scan `.af_review_queue/failed` and emit `[af-design-review-failed]` with file path + error.

#### 5. [ACCEPT] [High] `docs/work-items/**` excluded with no compensating automatic trigger
- **Critic** (#4): `core/design_review_utils.py:50-52` EXCLUDE comment claims work-items handled by "별도 경로(af-doc-qa 3-agent)", but no hook/script auto-emits `[af-workitem-review-pending]` — `CLAUDE.md:42` is manual-only.
- **Cross**: not flagged.
- **Judgment**: Verified — no `workitem` queue path or emission in this script or sibling scripts.
- **Action**: Either wire a `pending/workitem/` queue + matching emission, or revert the `docs/work-items/**` EXCLUDE until the 3-agent path is automated.

#### 6. [ACCEPT] [High] `_save_fired` silently swallows write failures
- **Critic** (#5): outer `except: pass` at `scripts/check_design_pending.py:70-71` hides cross-device-rename, full-disk, read-only-FS failures. Stale `fired` causes repeated `[af-design-review-pending]` floods.
- **Cross**: not flagged.
- **Judgment**: Verified at L54-71. Inner exception correctly cleans tmp; outer `pass` is the leak.
- **Action**: Replace outer `pass` with `print(f"[check_design_pending] save failed: {exc}", file=sys.stderr)` to preserve exit-0 while surfacing failures.

#### 7. [ACCEPT] [Medium] Constants duplicated + legacy `PENDING_DIR` not scanned
- **Critic** (#6): `DESIGN_QUEUE_DIR` hardcoded at L26 instead of importing `PENDING_DESIGN_DIR` from `core.design_review_utils`.
- **Cross** (#3): Watcher still scans legacy `.af_review_queue/pending` (`design_review_watcher.py:379` for backward compat); this hook does not, so legacy entries are invisible.
- **Judgment**: Both findings stem from the same root — hardcoding instead of reusing shared constants. Merged.
- **Action**: `from core.design_review_utils import PENDING_DESIGN_DIR, PENDING_DIR`; scan both with the legacy path filtered to exclude `pending/design` and `pending/code` subdirs.

#### 8. [ACCEPT] [Medium] No regression tests
- **Critic** (#8): No `tests/test_check_design_pending.py`; sibling `tests/test_pending_review.py` has 6 cases this script lacks.
- **Cross**: confirmed "no direct tests for `check_design_pending` yet".
- **Judgment**: Both reviewers verified the absence.
- **Action**: Mirror `tests/test_pending_review.py` cases — quiet-period suppression, refire-after-timestamp-update, stale-fired pruning, multi-candidate output, malformed-marker recovery (covers Finding #1 contract).

#### 9. [ACCEPT] [Medium] `existing_fnames` retains entries that failed JSON parse
- **Critic** (#9): L88 adds `fname` to `existing_fnames` *before* the JSON load (L91-96). If load fails, the file is skipped from `entries` but its `fname` remains in `existing_fnames`, so any matching `fired[fname]` survives pruning forever.
- **Cross**: not flagged.
- **Judgment**: Verified in code; minor unbounded leak.
- **Action**: Move `existing_fnames.add(fname)` into the success branch after `entries.append`.

#### 10. [ACCEPT] [Low] Wall-clock dependency for quiet-period check
- **Critic** (#10): `time.time()` at L112 is subject to NTP step / DST changes; backwards step >90s could re-arm or block firing.
- **Cross**: not flagged.
- **Judgment**: Edge case but real. Both `enqueue()` timestamps and `now` come from `time.time()`, so `monotonic()` isn't drop-in.
- **Action**: `elapsed = max(0, now - ts)` with comment, or document the wall-clock dependency.

#### REJECTED — Critic #3 "Multi-candidate batch prints one path"
- **Critic** quoted outdated code showing only `latest_file_path` printed.
- **Cross** correctly verified current code uses `", ".join(c[2] for c in candidates[:10])` at L131-135.
- **Judgment**: I confirmed — Critic was reading prior-review state, not current code. REJECT.

### Summary Table

| #  | Title                                                  | Severity | Verdict | Source |
|----|--------------------------------------------------------|----------|---------|--------|
| 1  | `_load_fired` non-dict crashes exit-0 contract         | Critical | ACCEPT  | Critic |
| 2  | `docs/patterns/**` missing from EXCLUDE                | Critical | ACCEPT  | Critic |
| 3  | Watcher starvation (90s hook vs 8s watcher)            | High     | ACCEPT  | Both   |
| 4  | Failed watcher items bypass manual fallback            | High     | ACCEPT  | Cross  |
| 5  | `docs/work-items/**` excluded, no auto trigger          | High     | ACCEPT  | Critic |
| 6  | `_save_fired` silently swallows write errors           | High     | ACCEPT  | Critic |
| 7  | Constants hardcoded; legacy PENDING_DIR unscanned      | Medium   | ACCEPT  | Both   |
| 8  | No regression tests                                    | Medium   | ACCEPT  | Both   |
| 9  | `existing_fnames` retains corrupted entries            | Medium   | ACCEPT  | Critic |
| 10 | Wall-clock dependency in quiet-period check            | Low      | ACCEPT  | Critic |
| —  | Multi-candidate prints one path                        | —        | REJECT  | Critic (outdated read) |

### Recommendations

1. **Fix Criticals first**:
   - Add `docs/patterns/**` + `docs/patterns/*` to EXCLUDE_PATTERNS in `core/design_review_utils.py:53`.
   - Coerce `_load_fired` output to `dict` and guard `float(fired.get(fname, 0))` against non-numeric values.
2. **Resolve the watcher race (Finding #3)**: pick one — separate notification marker, or remove this hook entirely. The current design has the hook fundamentally racing with the consumer.
3. **Wire the manual fallback (#4)**: scan `failed/` and emit `[af-design-review-failed]`.
4. **Decide work-items policy (#5)**: either wire automation or revert the EXCLUDE.
5. **Stop swallowing `_save_fired` errors (#6)**: log to stderr; preserve exit-0.
6. **Refactor constants (#7)** — import from `core/design_review_utils.py`; scan legacy `PENDING_DIR` too.
7. **Add tests (#8)** mirroring `tests/test_pending_review.py`.
8. **Polish #9, #10** in the same PR.