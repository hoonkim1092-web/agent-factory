# Code Review: check_design_pending

> Source: scripts/check_design_pending.py
> Date: 2026-04-29 15:36
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

Two High findings about `core/design_review_utils.py` pattern lists (spec violation + coverage gap) plus several Medium/High robustness gaps in `scripts/check_design_pending.py`. No Critical/security issues; merge is possible but the High items should be fixed before the new hook starts firing in shared sessions.

### Aggregated Findings (8 total)

#### 1. [ACCEPT] [High] `docs/patterns/**` misclassified as design docs (spec violation)
- **Critic**: INCLUDE pattern `docs/**/20??-??-??-*.md` matches `docs/patterns/2026-04-18-external-api-3tier.md`; spec at `docs/2026-04-21-design-doc-review-gate.md:45` explicitly excludes `docs/patterns/*.md`.
- **Cross**: not flagged.
- **Judgment**: Strong evidence — file existence verified, spec text quoted, EXCLUDE_PATTERNS at L43-53 confirmed to lack the entry. EXCLUDE-first ordering at L126-128 cannot rescue it.
- **Action Required**: Add `"docs/patterns/**"` and `"docs/patterns/*"` to `EXCLUDE_PATTERNS` in `core/design_review_utils.py`.

#### 2. [ACCEPT] [High] `docs/work-items/**` excluded with no compensating auto-trigger
- **Critic**: Comment claims work-items are handled "별도 경로(af-doc-qa 3-agent)", but no hook/watcher/script automatically calls af-doc-qa; CLAUDE.md L42 is a manual instruction.
- **Cross**: not flagged.
- **Judgment**: Coverage gap is real — repo-wide search confirms only an agent definition exists. After this change work-item edits get zero automatic review.
- **Action Required**: Either add a `pending/workitem/` queue + emit `[af-workitem-review-pending]`, or revert the work-items EXCLUDE so the 2-agent design path remains active until 3-agent path is wired.

#### 3. [ACCEPT] [High] Multi-file batch hides paths but marks all fired
- **Critic**: not flagged.
- **Cross**: Hook prints only `latest_file_path` (`scripts/check_design_pending.py:127`) but records `fired[fname] = now` for every candidate at L134. Hidden candidates won't reappear until re-edited.
- **Judgment**: Verified by Cross's smoke run (two actionable files → one printed, both fired). Breaks the control signal contract from `CLAUDE.md:40`.
- **Action Required**: Print every candidate path that is marked fired, OR mark only the path(s) actually shown.

#### 4. [ACCEPT] [Medium] Fired marker shape not validated → hook can crash
- **Critic**: not flagged.
- **Cross**: `_load_fired()` returns any valid JSON; `[]`, `null`, or `{"x.json": null}` will raise at `.items()` or `float(...)`.
- **Judgment**: Code evidence is direct — `_load_fired()` only catches load exceptions at L45; main() immediately calls `fired.items()` and `float(fired.get(...))`. Violates the "always exit 0" contract.
- **Action Required**: `raw = _load_fired(ws); fired = raw if isinstance(raw, dict) else {}`, plus safe per-value parse with `0` fallback.

#### 5. [ACCEPT] [Medium] Silent JSON corruption causes repeated re-firing
- **Critic**: `_load_fired` returns `{}` on any decode failure → next iteration re-fires every queued item past quiet period, spamming the user.
- **Cross**: not flagged (overlaps with #4 in spirit, but addresses a different recovery path).
- **Judgment**: Distinct from #4 — that one prevents crash, this one prevents spam after a successful corruption recovery.
- **Action Required**: On JSON decode failure, `os.replace(path, path + ".bad")` so re-fire happens once, not on every poll.

#### 6. [ACCEPT] [Medium] Constants duplicated instead of imported from `core/`
- **Critic**: `DESIGN_QUEUE_DIR` and `FIRED_MARKER` (L26, L29) duplicate `core/design_review_utils.py:82` `PENDING_DESIGN_DIR`. The legacy path migration in `design_review_watcher.py:379` proves drift is a live concern.
- **Cross**: not flagged.
- **Judgment**: Strong evidence — convention per CLAUDE.md is scripts/ consumes core/ shared logic, and a migration history exists.
- **Action Required**: `from core.design_review_utils import PENDING_DESIGN_DIR` (PYTHONPATH already set by `_start_watcher`).

#### 7. [ACCEPT] [Medium] No regression tests for the new hook
- **Critic**: not flagged.
- **Cross**: `rg "check_design_pending|design_review_fired|af-design-review-pending" tests` returns no matches; sibling `check_pending_review.py` has `tests/test_pending_review.py`.
- **Judgment**: Documented gap, comparable script has coverage.
- **Action Required**: Add `tests/test_check_design_pending.py` for quiet-period suppression, refire after timestamp update, stale fired suppression, multi-candidate output/marker behavior, and malformed marker recovery.

#### 8. [ACCEPT] [Low] Magic number coupling + silent write-failure (combined minor cleanup)
- **Critic**: `MIN_BATCH_INTERVAL_SEC = 90` vs watcher's `QUIET_PERIOD_DESIGN = 8` — two debounce values living in two files; `_save_fired` exception handler also swallows write failures with a bare `pass`.
- **Cross**: not flagged.
- **Judgment**: Both are diagnostic/maintenance issues — accepted at Low because neither breaks correctness today.
- **Action Required**: Add comment/shared constant linking the two values; replace inner `pass` in `_save_fired` with `print(f"[check_design_pending] save failed: {exc}", file=sys.stderr)`.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `docs/patterns/**` misclassified | High | ACCEPT | Critic |
| 2 | `docs/work-items/**` coverage gap | High | ACCEPT | Critic |
| 3 | Multi-file batch hides paths but fires all | High | ACCEPT | Cross |
| 4 | Fired marker shape unvalidated → crash | Medium | ACCEPT | Cross |
| 5 | Corrupted marker → repeated re-firing | Medium | ACCEPT | Critic |
| 6 | Constants duplicated, not imported | Medium | ACCEPT | Critic |
| 7 | No regression tests | Medium | ACCEPT | Cross |
| 8 | Magic number + silent save failure | Low | ACCEPT | Critic |

### Recommendations
- Fix #1 and #2 before merge — they are spec-level correctness bugs that change what gets reviewed today.
- Fix #3 in the same patch — without it, the hook silently drops review obligations for batched edits.
- Bundle #4–#6 as a robustness pass on `scripts/check_design_pending.py` (validate marker shape, quarantine corrupted JSON, import shared constants).
- Add the `tests/test_check_design_pending.py` from #7 covering all five scenarios listed.
- Address #8 opportunistically; do not block on it.
- Cross's REJECT of the prior stale-count/newest-gating concern is upheld — current `candidates` construction at L113 fixes that earlier review's specific issue.