# Code Review: review_gate

> Source: scripts/review_gate.py
> Date: 2026-05-04 00:13
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. 3 Medium + 2 Low findings from Critic. Cross Review provider errored out (Codex stdin/auth failure visible in raw output) — single-reviewer aggregation only. Recommend re-running cross-review before merge if BLOCK confidence is needed; otherwise WARN-level merge with the actions below is acceptable per Phase 0 policy (WARN = advisory).

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [Medium] Helper has no in-file caller; integration depends on external commit
- **Critic**: `_extract_verdict_from_content` (lines 41–62) is unreachable in this diff; `is_gate_blocked()` at line 226–229 still reads `r.get("verdict")` directly. Wires-up is supposed to happen in `scripts/hook_runner.py` and `scripts/check_pending_review.py` per v7 §8.2 8-file commit.
- **Cross**: not flagged (provider error)
- **Judgment**: Diff evidence is unambiguous — the helper exists with no internal call site. If the bundled wrapper commit slips, this becomes dead code that drifts from `is_gate_blocked()` semantics.
- **Action Required**: Confirm the v7 §8.2 8-file commit actually wires `hook_runner.py` / `check_pending_review.py` to this helper in the same merge unit, OR add a defensive in-file integration point (e.g., re-parse inside `record_review_done` when `verdict` arrives stringly typed).

#### 2. [ACCEPT] [Medium] No unit tests for the new extraction algorithm
- **Critic**: Helper encodes nontrivial logic (fence-first → last-position over two start-disjoint regexes → `None`); zero tests in diff. `scripts/review_gate.py` is Tier 2~3 per `blast_radius`.
- **Cross**: not flagged (provider error)
- **Judgment**: Verifiable from diff — no `tests/` files modified. Edge cases (empty fence, multiple fences, fence-only no-match, overlapping regex hits) are exactly the parser bugs that bite later.
- **Action Required**: Add `tests/scripts/test_review_gate_verdict.py` covering: (a) fence beats out-of-fence, (b) empty fence → `None`, (c) two fences → first wins, (d) no fence → last-position fallback, (e) start-disjoint regex invariant.

#### 3. [ACCEPT] [Medium] Fence sentinel can be hijacked by markdown code-block examples
- **Critic**: `_VERDICT_FENCE_RE` matches anywhere in document — including inside ` ``` ` code blocks. A spec doc that *quotes* the fence as an example will shadow the real later fence (first-pair-wins). Phase 2 v7 §5.3 itself documents this fence — non-hypothetical risk.
- **Cross**: not flagged (provider error)
- **Judgment**: Regex inspection confirms no code-block exclusion. Given the documented stale-baseline cross-review false-positive history (`feedback_cross_review_stale_baseline_repeat.md`), this is the exact failure mode the fence is meant to prevent — and the regex as written can break its own design doc.
- **Action Required**: Either (a) strip fenced code blocks before regex search, or (b) require fence at line-start outside code blocks + add a regression test with the fence quoted inside ` ``` `.

#### 4. [ACCEPT] [Low] Fence-absent fallback silently picks last verdict-shaped string
- **Critic**: When fence is missing, last-position wins. Spec docs frequently include changelog tables ("v5 verdict was BLOCK") near the bottom that will shadow the real top-of-doc verdict. Silent failure mode.
- **Cross**: not flagged (provider error)
- **Judgment**: Real concern given repo conventions, but Low because (a) caller wrapper is supposed to handle `None` per §5.5, and (b) the fence is the canonical mechanism — fallback is best-effort.
- **Action Required**: When fence missing AND multiple distinct labels detected, log a warning or return ambiguity sentinel. Defer to caller.

#### 5. [ACCEPT] [Low] Case-insensitive header regex relies on caller `.lower()` discipline
- **Critic**: `_VERDICT_HEADER_RE` uses `IGNORECASE` but capture group preserves source case. New code correctly `.lower()`s; future call sites might not, breaking dict lookup at line 228 (`("block","fail")`).
- **Cross**: not flagged (provider error)
- **Judgment**: Hypothetical future-callsite risk, but cheap to harden.
- **Action Required**: Either drop `IGNORECASE` (require uppercase per convention) or normalize to lowercase inside the regex helper itself.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Helper unreachable in-file (depends on bundled commit) | Medium | ACCEPT | Critic |
| 2 | No unit tests for extraction algorithm | Medium | ACCEPT | Critic |
| 3 | Fence regex hijacked by code-block quotes | Medium | ACCEPT | Critic |
| 4 | Fence-absent last-position fallback brittle | Low | ACCEPT | Critic |
| 5 | IGNORECASE + uppercase capture relies on caller normalization | Low | ACCEPT | Critic |

### Recommendations
- **Before merge**: confirm v7 §8.2 bundle actually wires `hook_runner.py` + `check_pending_review.py` to `_extract_verdict_from_content` (Finding 1).
- **In this commit**: add `tests/scripts/test_review_gate_verdict.py` with the 5 test cases enumerated in Finding 2 — closes Tier 2~3 test gap so af-test-runner has something to assert.
- **Harden regex (Finding 3)**: strip fenced code blocks before searching, OR add a regression test that locks in current behavior + documents the constraint in spec.
- **Re-run cross-review** (Codex provider failed): if cross-review remains unavailable, accept this WARN aggregation as single-reviewer; per Phase 0 policy WARN is advisory and not blocking.
- **Optional polish (Findings 4–5)**: defer to follow-up if test + fence-hardening land in this commit.