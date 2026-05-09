# Code Review: review_gate

> Source: scripts/review_gate.py
> Date: 2026-04-30 08:40
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. Multiple Medium issues exist that can block commits unexpectedly or silently exhaust the Phase 0 round cap. Mergeable with documented risks, but the two Medium issues (A and E) warrant fixes before this gate runs in production.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [Medium] Null/invalid `blast_tier` violates fail-open contract
- **Critic**: "`state.get("blast_tier", 2)` returns `None` when key exists with JSON null → `int(None)` raises `TypeError`, propagating uncaught through `is_gate_blocked`, blocking the commit."
- **Cross**: "Malformed `"bad"` string raises `ValueError` on the same line; issue extends to `round_count`, `updated_at`, `completed_at` coercions; only `_load_state` is inside the fail-open guard, not the numeric coercions."
- **Judgment**: Both reviewers flag the same location (`review_gate.py:127`) from complementary angles. The fail-open docstring promise is structurally broken — `_required_tiers_for` is called at line 157, outside the `try/except` that wraps lines 139–143. The `clear_committed_files` pop path mostly avoids the null case, but a manual file edit or concurrent write race can produce `blast_tier: null`.
- **Action Required**: Replace bare `int(state.get("blast_tier", 2))` with a safe coercion, e.g. `int(state.get("blast_tier") or 2)`. Apply the same pattern to `round_count`, `updated_at`, and `completed_at`. Alternatively, wrap the entire gate decision body (not just `_load_state`) in a fail-open `try/except`.

---

#### 2. [ACCEPT] [Medium] CLI `--record` without `--files` stores empty snapshot → triggers `new-files-added`
- **Critic**: not flagged
- **Cross**: "Omitted `--files` becomes `[]` and is passed as `files_snapshot=[]` (not `None`), so `is_gate_blocked` sees an empty snapshot and reports `new-files-added`. `hook_runner.py:337-338` passes `files_snapshot=None` explicitly to avoid this, but the CLI path bypasses that safeguard."
- **Judgment**: Cross provides precise evidence from `hook_runner.py:337-338`. The `files_snapshot is not None` guard in `record_review_done` is the load-bearing distinction; `[]` and `None` are treated differently. The CLI path silently breaks a property that the hook runner upholds by design.
- **Action Required**: Change CLI call to `record_review_done(ws, agent, tier, verdict, args.files if args.files else None)`. Add a regression test: `--record af-test-runner --verdict pass` with no `--files` must not trigger `new-files-added`.

---

#### 3. [ACCEPT] [Medium] Tier 1 duplicate records silently exhaust the max-round cap
- **Critic**: not flagged
- **Cross**: "For `blast_tier=1`, `af-test-runner` alone completes a round. After round 1 clears `round_started_at`, a duplicate `record_review_done` call immediately starts and closes round 2. `check_pending_review.py:83` stops firing at `round_count >= 2`, so the Phase 0 cap is exhausted without a real second review cycle."
- **Judgment**: Cross provides evidence with a traceable code path. The new Tier 2 duplicate test in the diff does not cover the single-agent Tier 1 path. The `round_started_at` token model is designed to prevent this, but the correction path (`if not state.get("round_started_at"): state["round_started_at"] = now`) fires again on the duplicate call, restarting the clock and re-completing the round.
- **Action Required**: Before incrementing `round_count`, check whether the new record's `completed_at` is a fresh call (e.g., compare against a per-agent dedup token or require a new `updated_at` generation before a new round can start). Add a `blast_tier=1` duplicate-record regression test.

---

#### 4. [ACCEPT] [Low/Medium] Step 7 verdict scan iterates all agents, not just `required_tiers` — stale BLOCKs persist
- **Critic**: "If blast_tier was previously 3 (all 3 agents ran, one gave BLOCK) then drops to 2, the old non-required BLOCKs in `reviews` still fire at step 7 even though those agents are no longer in `required_tiers`."
- **Cross**: not flagged
- **Judgment**: Critic correctly identifies the inconsistency: steps 4 and 5 filter by `required_tiers`; step 7 (lines 185–187 in pre-diff state) does not. Critic also documents why it is not currently triggerable: blast_tier=1 + `.py` files is impossible today, and tier 2 vs 3 both produce `required_tiers=[1,2,3]`. Severity is Low today, Medium as a future-correctness trap.
- **Action Required**: Replace `for agent, r in reviews.items()` with `for tier in required_tiers: agent = _TIER_AGENTS[tier]; r = reviews.get(agent, {})` in the verdict-block check, consistent with the tier-filtering pattern used in steps 4 and 5.

---

#### 5. [ACCEPT] [Low] Unknown agent names produce malformed `claim_id` suffixes
- **Critic**: "If `agent` is not in the `{"af-test-runner": "T1", ...}` lookup, the full agent string is used as the suffix. The CLI validates `agent not in _AGENT_TIER`, but the public Python function `record_review_done` has no such guard."
- **Cross**: not flagged
- **Judgment**: Code evidence is clear at `review_gate.py:274`. Impact is low because the CLI is the primary call site, and it validates agent names. Risk is confined to direct Python API callers. Low severity, but trivially fixed.
- **Action Required**: Add `assert agent in _AGENT_TIER, f"unknown agent: {agent}"` at the top of `record_review_done`, or truncate the fallback to a fixed-width substring (`agent[:4]`).

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Null/invalid `blast_tier` crashes fail-open gate | Medium | ACCEPT | Both |
| 2 | CLI `--record` without `--files` → empty snapshot | Medium | ACCEPT | Cross only |
| 3 | Tier 1 duplicate records exhaust round cap | Medium | ACCEPT | Cross only |
| 4 | Step 7 scans all agents, ignores `required_tiers` | Low–Med | ACCEPT | Critic only |
| 5 | Unknown agent → malformed `claim_id` | Low | ACCEPT | Critic only |

---

### Recommendations

- **Fix #1 first** — it is the only path to an uncaught exception in the pre-commit hook, making it the highest operational risk despite being "Medium." One-liner: `int(state.get("blast_tier") or 2)` plus the same pattern for other numeric fields.
- **Fix #2 before enabling CLI-based review recording** — the `--record` CLI path is only safe today if `--files` is always supplied; tightening the default costs one line.
- **Fix #3 before relying on the 2-round cap as a correctness guarantee** — if the cap can be exhausted by a single agent retrying, the WARN-only no-fire policy downstream loses its foundation.
- **Fix #4 and #5 can be batched** — both are low-risk correctness improvements with no urgent operational impact.
- The `round_started_at` token model and `clear_committed_files` cycle-reset logic are sound per both reviewers — no action needed there.