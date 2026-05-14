# Code Review: review_gate

> Source: scripts/review_gate.py
> Date: 2026-05-15 00:26
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No critical defects. The stale-reset guards (`has_block is False`, `round_count > 0`, `round_started_at is None`) are correct and have negative test coverage. However, three Medium-severity issues converge on the same root cause — the `committed_files=[]` path is a contract-violating footgun that lacks both a guard and a regression test — and the meta-reset block is duplicated, inviting future drift.

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [Medium] Empty `committed_files=[]` triggers wholesale stale-reset
- **Critic**: With `committed_files=[]`, the filter at line 362 is a no-op; if guards match (idle PASS + non-empty queue), the entire queue is wiped despite no actual commit. CLI default `--files=""` (line 443) makes this reachable from manual/test invocation even though `.githooks/post-commit:14-19` guards `$CHANGED` non-empty.
- **Cross**: not flagged directly, but Cross HOLD #1 (pre-summary stale queues) is the inverse scope question.
- **Judgment**: Diff confirms `committed_set = set([])` → empty set → filter no-op → falls into `else` branch with guards potentially satisfied. Function contract ("clear committed files") is violated when nothing was committed. Production path is currently safe, but the CLI default makes it a latent footgun.
- **Action Required**: Add `if not committed_set: return` early-exit, OR gate the `else` branch on `committed_set and …`. Document the chosen semantics.

#### 2. [ACCEPT] [Medium] Duplicated meta-reset block invites drift
- **Critic**: Lines 371-377 and 390-396 independently perform the same 5-key reset + `reviews={}`. Adding a future meta key (e.g., `last_fire_id`, `tier_overrides`) will likely miss one branch.
- **Cross**: not flagged.
- **Judgment**: Diff verbatim shows the duplication. Single-source-of-truth violation is plain.
- **Action Required**: Extract `_reset_round_meta(state)` helper. Both branches call it; second branch additionally sets `state["files"] = []`.

#### 3. [ACCEPT] [Medium] Test gap: empty `committed_files=[]` and Tier-1 stale-reset uncovered
- **Critic**: All 5 new tests use non-empty `committed_files` and `blast_tier=3`. The `[]` case (Finding #1) and Tier-1 PASS round are not exercised.
- **Cross**: not flagged; Cross ran 69 tests PASS but didn't audit the gap.
- **Judgment**: Test file inspection confirms — no `clear_committed_files(ws, [])` invocation, no `blast_tier=1` stale-reset assertion.
- **Action Required**: Add (a) `committed_files=[]` regression locking the chosen semantics from Finding #1; (b) Tier-1 PASS + idle + stale → assert reset.

#### 4. [HOLD] [Medium] Pre-summary stale queues unreachable by new branch
- **Critic**: not flagged.
- **Cross**: Reset requires `last_round_summary.has_block is False` + `round_count > 0`. Older stale queues from before round-summary plumbing existed won't satisfy the guard.
- **Judgment**: Cross is right that the guard excludes pre-summary queues. But scope is genuinely unclear — Round 2 docstring (line 349) only promises "PASS round residue" reset, not a one-time migration sweep. Need author intent.
- **Question for Author**: Is the intended scope only "post-PASS-round residue" (current code), or should this also clean pre-summary stale queues (one-time migration)? If just the former, add a one-line note to the docstring.

#### 5. [ACCEPT] [Low] Forensic log uses `,` as sample separator
- **Critic**: `','.join(stale_reset_info['sample'])` corrupts downstream parsing if filenames contain commas. `.py` filenames rarely do, but the log line uses `|` for top-level separation already.
- **Cross**: not flagged.
- **Judgment**: Diff line 405 confirms. Low priority since logs are human-read today, but cheap to fix.
- **Action Required**: Use `;` separator or `json.dumps(sample)`.

#### 6. [ACCEPT] [Low] Redundant `list()` wrapper on slice
- **Critic**: `list(state["files"][:5])` — slice already returns a list.
- **Cross**: not flagged.
- **Judgment**: Diff line 387 confirms; trivial cleanup.
- **Action Required**: `"sample": state["files"][:5]`.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Empty `committed_files=[]` wipes queue | Medium | ACCEPT | Critic |
| 2 | Duplicated meta-reset block | Medium | ACCEPT | Critic |
| 3 | Test gap (empty list + Tier-1) | Medium | ACCEPT | Critic |
| 4 | Pre-summary stale queues uncovered | Medium | HOLD | Cross |
| 5 | Comma in forensic log sample | Low | ACCEPT | Critic |
| 6 | Redundant `list()` on slice | Low | ACCEPT | Critic |

### Recommendations

- **Must fix before merge** (Findings #1, #3): Add `if not committed_set: return` early-exit (or equivalent guard), and add a regression test asserting the chosen behavior for `committed_files=[]`. These are linked — pick the semantics, lock it with a test.
- **Should fix in same PR** (Finding #2): Extract `_reset_round_meta(state)` to dedupe the two branches. Cheap, prevents future drift.
- **Add Tier-1 test** (Finding #3 second half): One test asserting `blast_tier=1` PASS + idle + stale also resets.
- **Answer scope question** (Finding #4): Decide whether pre-summary queues need a migration sweep or remain manual. Update docstring either way.
- **Polish** (Findings #5, #6): Optional but trivial — swap `,` separator in log, drop `list()` wrapper.