# Code Review: review_gate

> Source: scripts/review_gate.py
> Date: 2026-05-15 00:16
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No critical defects found, but Cross Review surfaced one real behavioral edge case (`--clear` with no `--files`) that should be fixed before merge or documented as a known limitation. Critic's findings are mostly maintainability / defensive-coding concerns.

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [Medium] Empty `--clear` can trigger stale-reset on PASS state
- **Critic**: not flagged
- **Cross**: New stale-reset branch fires even when `committed_files=[]`, because `_cli()` defaults `--files` to `""` → `[]` and still calls `clear_committed_files(ws, [])`. With a PASS round + idle state, the queue would be wiped without any commit being proven.
- **Judgment**: Verified against the diff — the new `else` branch (scripts/review_gate.py:376-389) checks only `has_block`, `round_count`, and `round_started_at`; it does not consult `committed_set`. Test coverage in `test_clear_stale_reset_when_round_passed_and_idle` uses `["docs/unrelated.md"]`, not `[]`, so the regression path is uncovered. This contradicts the docstring intent ("committed_set 미포함 stale .py가 큐에 남아있고") which implicitly assumes a real commit triggered the call.
- **Action Required**: Gate the stale-reset branch on `committed_set` being non-empty:
  ```python
  if (
      committed_set
      and "has_block" in lrs and not lrs["has_block"]
      and int(state.get("round_count", 0)) > 0
      and state.get("round_started_at") is None
  ):
  ```
  Add a negative test: `--clear` with empty files must not reset on a PASS state.

#### 2. [ACCEPT] [Medium] Duplicated metadata-reset block — divergence risk
- **Critic**: Two identical 5-line reset sequences at lines 369-375 and 383-389; future metadata key (`routing_state`, `claim_id_cursor`) likely to be added to only one branch.
- **Cross**: not flagged
- **Judgment**: Concrete risk — Phase 0 docstring already references `routing_state` as a separate concept, so additional reset keys are foreseeable. Diff confirms identical 5-pop sequences.
- **Action Required**: Extract `_reset_round_metadata(state)` helper; both branches call it. Single source of truth for cycle-completion contract.

#### 3. [ACCEPT] [Low] Brittle `is False` identity check on `has_block`
- **Critic**: `lrs.get("has_block") is False` silently fails if state schema drifts (e.g., `0`, `"false"`), reintroducing the bug being fixed.
- **Cross**: not flagged
- **Judgment**: Minor — current writer always emits a bool, so no live bug. But the cost of `"has_block" in lrs and not lrs["has_block"]` is identical and avoids the "missing key = green light" edge.
- **Action Required**: Replace identity check with explicit key-presence + truthiness, OR add a comment that `has_block` is contractually `bool`.

#### 4. [ACCEPT] [Low] `_log_event` reads `state['files']` after lock release
- **Critic**: Reading post-RMW state outside the lock is a smell; pre-existing pattern, but the new `stale_reset` semantics make the log line more load-bearing.
- **Cross**: not flagged
- **Judgment**: Not a correctness bug — the local `state` dict reflects what was saved, no other writer can mutate it. Style suggestion only.
- **Action Required**: Capture `remaining = len(state["files"])` inside the `with _state_lock(workspace):` block, log outside.

#### 5. [HOLD] [Low] `round_count > 0` is redundant with `has_block is False`
- **Critic**: `record_review_done` only writes `last_round_summary` together with `round_count++`, so the third check is defensive and confuses future readers.
- **Cross**: not flagged
- **Judgment**: Critic itself flags this as "not a bug." Defensive against manual state edits is reasonable; removing it doesn't help. Either keep as-is with a one-line comment, or drop it. Author preference.
- **Question for Author**: Is the redundant check intentional (defense against manual JSON edits / migration artifacts)? If yes, add a one-line comment so it's not removed in a future cleanup.

#### Cross Review #2 (REJECT — race condition) — Confirmed
- Cross correctly self-rejected the race claim. `enqueue_agent_review.py:113` sets `round_started_at` under the same `_state_lock` (verified — enqueue imports `review_gate._state_lock` at line 85). The `round_started_at is None` guard is sufficient. Existing test at `test_review_gate.py:299` confirms in-flight protection.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Empty `--clear` triggers stale-reset on PASS | Medium | ACCEPT | Cross |
| 2 | Duplicated metadata-reset block | Medium | ACCEPT | Critic |
| 3 | Brittle `is False` identity check | Low | ACCEPT | Critic |
| 4 | `_log_event` reads state post-lock | Low | ACCEPT | Critic |
| 5 | `round_count > 0` redundant | Low | HOLD | Critic |

### Recommendations

1. **Fix #1 first** — single-line guard (`committed_set and ...`) plus a negative test for `--clear` with empty files. This is the only finding that can erase user data.
2. **Refactor #2** — extract `_reset_round_metadata(state)` helper; replace both 5-line blocks. Pure mechanical change, eliminates future divergence.
3. **Tighten #3** — replace `is False` with `"has_block" in lrs and not lrs["has_block"]` while you're in the file.
4. **#4 and #5** — optional cleanups; defer to a follow-up commit if scope-sensitive.
5. **Positive observations from Critic stand**: race-correctness reasoning is verified, three-condition test coverage is solid, `stale-reset` log marker is the right diagnostic addition.