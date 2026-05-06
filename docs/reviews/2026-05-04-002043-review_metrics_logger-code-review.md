# Code Review: review_metrics_logger

> Source: scripts/review_metrics_logger.py
> Date: 2026-05-04 00:20
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: PASS

The diff is a minimal, spec-anchored regex extension. The Critic gave PASS with metric-semantics caveats (all Medium/Low advisory, all explicitly accepted by the design spec §7.6 v5). The Cross reviewer errored out (provider failure) and produced no findings. Without a second independent confirmation, I am not escalating any Critic-only finding to ACCEPT — they remain HOLD/advisory pending the spec's already-scheduled 1-week operational checkpoint.

### Aggregated Findings (3 total)

#### 1. [HOLD] [Medium] `[BONUS]` inflates T3-only contribution rate (`t3_rate`) used for Phase 4 routing
- **Critic**: BONUS findings are off-scope by definition (§5.6 / docs/2026-05-03-phase2-verdict-label-spec.md:172). After this change, every BONUS appended by T3 increments `t3_findings`, inflating `t3_rate` at `scripts/review_metrics_logger.py:267` and biasing Phase 4 routing thresholds at `:294-299`.
- **Cross**: not flagged (provider errored — no independent second opinion).
- **Judgment**: Real semantic concern, but spec §7.6 v5 has explicitly accepted this drift and scheduled re-evaluation after 1 week of operation. No code bug — the metric definition matches the documented contract. Single-source finding without evidence of operational harm yet.
- **Question for Author**: Is the §7.6 v5 1-week checkpoint already wired into a follow-up (e.g., `bonus_count` column in the report, or a calendar reminder)? If yes → close. If no → file the follow-up now so the gating decision is not lost.

#### 2. [HOLD] [Low] `[REJECTED]` still counted in `findings_count` despite being verdict-neutral
- **Critic**: Spec §4.3 declares `[REJECTED]` verdict-neutral, but `parse_findings_count` continues to count it (`scripts/review_metrics_logger.py:34-37, 110`). Combined with new BONUS counting, a `5×[REJECTED] + 3×[BONUS] + 0×[ACCEPT★]` review would report `findings_count=8` while contributing nothing actionable. Docstring at `:109` does not surface this asymmetry.
- **Cross**: not flagged.
- **Judgment**: Documented as intentional in spec §7.6 #4 ("기존 정책 유지"). Pure documentation gap, not a behavioral bug.
- **Action Required (advisory, optional)**: Update the `parse_findings_count` docstring at `:109` to note that `REJECTED`/`BONUS` are counted as raw markers and are not equivalent to actionable findings. One-line clarification, no behavior change.

#### 3. [HOLD] [Low] `re.IGNORECASE` allows label-case drift; no severity-bracket co-validation
- **Critic**: With `IGNORECASE`, `[accept-adv]`, `[Bonus]`, etc. all match. Spec §5.1 mandates uppercase. Also, regex matches `[ACCEPT-ADV]` even without the required `[Severity]` bracket — §4.3 fail-safe-default cannot be enforced at the metric layer.
- **Cross**: not flagged.
- **Judgment**: Critic explicitly recommends "Defer — this is by design per the spec's single-grep simplicity policy." Already covered by the §7.6 v5 operational checkpoint.
- **Action Required**: None now. At the 1-week checkpoint, compare `findings_count` vs. severity-aware count; tighten regex if divergence > 5%.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `[BONUS]` inflates `t3_rate` for Phase 4 routing | Medium | HOLD | Critic only (Cross errored) |
| 2 | `[REJECTED]` counted but verdict-neutral — docstring drift | Low | HOLD | Critic only |
| 3 | `IGNORECASE` + missing severity-bracket co-validation | Low | HOLD | Critic only |

### Recommendations

- **Merge as-is.** The diff faithfully implements Phase 2 v7 §5.6, has tight regex bounds (no backtracking risk, ACCEPT variants correctly disambiguated), full test coverage at `tests/test_review_metrics_logger.py:64-117`, and clear spec-anchored comments at `:31-33` and `:45-46`.
- **Cross-review provider failed** (Codex stdin/provider error visible in the raw transcript). All three findings are single-source from the Critic; per the aggregation rules, single-reviewer Medium/Low findings without independent confirmation default to HOLD. None block merge.
- **Re-run af-cross-review** if you want a confirmed second opinion before closing the HOLD items — current verdict relies on Critic alone.
- **Confirm the §7.6 v5 1-week checkpoint** is captured somewhere durable (issue, calendar, NEXT_STEPS.md). The Critic's three findings collapse into one operational question: did the bonus/rejected counting drift cause routing miscalls in week 1? Bake that check in now so it does not get forgotten.
- **Optional doc nit**: Update `parse_findings_count` docstring at `scripts/review_metrics_logger.py:109` to say "Counts `[ACCEPT★]`, `[ACCEPT-ADV]`, `[WARN]`, `[BLOCK]`, `[REJECTED]`, `[BONUS]` as raw markers; `[REJECTED]` and `[BONUS]` are advisory and do not represent actionable findings." Trivial, can ride in the next commit touching this file.