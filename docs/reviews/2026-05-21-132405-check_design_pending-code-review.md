# Code Review: check_design_pending

> Source: scripts/check_design_pending.py
> Date: 2026-05-21 13:24
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: PASS

The shown diff is a 2-line documentation/print-string change in `scripts/check_design_pending.py` that aligns the hook output with the `CLAUDE.md:118` "단일 설계문서 → af-cross-review만" policy (G8 in the gap analysis). No control-flow, queue logic, atomic-write, or hook-exit contract is touched. Both reviewers report zero Critical/High findings. All remaining items are Low/Info/advisory, several of which are actually scoped to the companion `check_pending_review.py`/`review_gate.py` edits that ride along on this branch.

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [Medium] Missing regression test for the changed hook output contract
- **Critic**: not flagged (Critic #3 touches test ordering, but for `check_pending_review.py`, not this file)
- **Cross**: `rg "check_design_pending|af-design-review-pending" tests` returns no matches — the user-facing hook contract changed but has zero direct coverage
- **Judgment**: Single-reviewer call but evidence is strong: `.claude/settings.json:79` invokes this script as a hook and `CLAUDE.md:118` mandates the exact "af-cross-review만" wording. Without a test, a future drift back to "af-critic + af-cross-review" would not be caught — that drift already persisted ~20 days per `docs/2026-05-21-af-dogfooding-infrastructure-gap-analysis.md`.
- **Action Required**: Add `tests/test_check_design_pending.py` that seeds `.af_review_queue/pending/design/*.json`, runs `main()`, and asserts output contains `af-cross-review` but NOT `af-critic`. Bypass `MIN_BATCH_INTERVAL_SEC` via old timestamp or env override.

#### 2. [HOLD] [Medium] `.claude/settings.local.json` may override project hook wiring
- **Critic**: not flagged
- **Cross**: `.claude/settings.json:79` registers `check_design_pending.py`, but `.claude/settings.local.json:92-100` only wires `cli_hook_bridge` for `UserPromptSubmit`. If local settings override (not merge) project settings, the fix never executes in the active session.
- **Judgment**: Genuinely missing information — settings merge semantics are not documented in this diff or the referenced files. Worth confirming before claiming the fix is live.
- **Question for Author**: Does Claude Code merge `settings.json` + `settings.local.json` hook arrays, or does `settings.local.json` shadow the project file entirely? If the latter, `check_design_pending.py` and `check_pending_review.py` need to be re-added to the local file.

#### 3. [ACCEPT] [Info] Branch scope wider than this diff shows
- **Critic**: `git status` shows `scripts/check_pending_review.py` (`MAX_ROUNDS 2→5`, agent-ordering reversal) and `scripts/review_gate.py` (`< 5` literal) also modified — those ARE semantic policy changes; the design_pending diff is cosmetic
- **Cross**: not flagged
- **Judgment**: Critic is correct per `git status` in the session prelude. The branch couples a docstring fix with a round-cap bump and an order inversion. Reviewers reading only this diff will under-assess risk.
- **Action Required**: Commit-message hygiene — either split into two commits (docstring vs policy) or call out both changes explicitly in one commit message. Don't let `MAX_ROUNDS 2→5` ride silently on a print-string fix.

#### 4. [ACCEPT] [Low] `review_gate.py:282` hard-codes the `5` literal instead of importing `MAX_ROUNDS`
- **Critic**: `MAX_ROUNDS = 5` in `check_pending_review.py:30` and `int(state.get("round_count", 0)) < 5` in `review_gate.py:282` are now drifted by literal. Same two-edit footgun G1 was meant to remove.
- **Cross**: not flagged
- **Judgment**: Out of scope for this diff but caused by the companion edit. `review_gate.py` already uses `sys.path.insert(0, _scripts_dir)` so `from check_pending_review import MAX_ROUNDS` is mechanically trivial.
- **Action Required**: Replace literal `5` in `review_gate.py:282` with `MAX_ROUNDS` import. Advisory — won't block merge.

#### 5. [ACCEPT] [Low] Stale `capped_notified_at` from `MAX_ROUNDS=2` era never cleared
- **Critic**: Markers persisted under previous regime with `round_count: 2` + `capped_notified_at: <ts>` now resume firing (correct), but on next wraparound to 5 the user gets no `[af-review-capped]` notification.
- **Cross**: not flagged
- **Judgment**: Single-reviewer but the failure mode is concrete and self-contained to `check_pending_review.py:119-132`. Not a functional break (BLOCK still enforced via `review_gate.py`), but the "1회 알림" UX contract silently breaks on first wraparound.
- **Action Required**: When `round_count < MAX_ROUNDS` but `capped_notified_at` is set, clear it on the next marker write. Same applies to `warn_only_notified_at` per the prior 2026-05-04 review note.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Missing regression test for design hook output | Medium | ACCEPT | Cross |
| 2 | settings.local.json hook override risk | Medium | HOLD | Cross |
| 3 | Branch couples cosmetic + policy changes | Info | ACCEPT | Critic |
| 4 | `review_gate.py:282` literal vs `MAX_ROUNDS` import | Low | ACCEPT | Critic |
| 5 | Stale `capped_notified_at` after cap bump | Low | ACCEPT | Critic |

### Recommendations
- **Must-do before next session**: Add `tests/test_check_design_pending.py` (Finding #1). Resolves the ~20-day drift class identified in the gap analysis.
- **Verify**: Test settings.json + settings.local.json merge semantics. If shadow, mirror project hooks into local file (Finding #2).
- **Same branch, separate concern**: Replace `5` literal in `review_gate.py:282` with import from `check_pending_review.MAX_ROUNDS` (Finding #4) and clear stale `capped_notified_at` on wraparound (Finding #5).
- **Commit hygiene**: Split or annotate the commit so the `MAX_ROUNDS 2→5` + ordering reversal don't ride on a print-string fix (Finding #3).
- **No blockers** to merging this specific diff — PASS verdict stands.