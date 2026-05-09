# Code Review: design_review_utils

> Source: core/design_review_utils.py
> Date: 2026-04-29 15:31
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

The diff itself is small and the immediate behavior is correct (Critic verified empirically). However, two scope-related concerns from Cross and one test-coverage gap from Critic warrant follow-up before this becomes load-bearing for the design pipeline.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [Medium] `docs/patterns/**` now silently becomes a design-review target
- **Critic**: not flagged
- **Cross**: New include `docs/**/20??-??-??-*.md` matches `docs/patterns/2026-04-29-*.md`, but `2026-04-21-design-doc-review-gate.md` historically treats `docs/patterns/*.md` as non-design reference material; no exclude was added.
- **Judgment**: Diff evidence confirms — `EXCLUDE_PATTERNS` covers `archive/`, `code_review/`, `reviews/`, and the new `work-items/`, but not `patterns/`. The recursive include at line 38 captures it. This is a scope expansion not stated in the diff intent.
- **Action Required**: Either add `"docs/patterns/**"` (+ flat pair if keeping the convention) to `EXCLUDE_PATTERNS`, or amend the inline comment to declare patterns docs are now in scope.

#### 2. [ACCEPT] [Medium] No test coverage for `is_design_doc()` / new patterns
- **Critic**: `tests/**/*.py` has zero hits for `design_review_utils`, `is_design_doc`, or `INCLUDE_PATTERNS`; the hand-rolled `_matches_glob()` means pattern edits can silently change behavior.
- **Cross**: not flagged
- **Judgment**: Verified — the routing logic is now used by `scripts/design_review_trigger.py:72` and `core/hooks/design_review_hook.py:116,157`. With work-item exclusion + dated include + precedence (exclude-before-include) all on one matcher, the regression surface just grew without a net.
- **Action Required**: Add `tests/test_design_review_utils.py` with at least 5 cases — flat dated → True, nested dated → True, `docs/work-items/<slug>/2026-04-29-x.md` → False, `docs/code_review/*.md` → False, `docs/random.md` → False. Add `docs/patterns/2026-04-29-x.md` once finding #1 is resolved (whichever way).

#### 3. [HOLD] [Medium] Work-item exclusion removes the only automatic queue path
- **Critic**: Positively notes the inline comment ("별도 경로(af-doc-qa 3-agent)로 처리됨") matches CLAUDE.md policy.
- **Cross**: But no caller wires the replacement: `design_review_trigger.py:72-80` only enqueues when `is_design_doc()` is True, `hook_runner._post_edit_enqueue` returns early for non-`.py`, `review_gate` passes when no `.py` exists — so `docs/work-items/<slug>/*.md` is neither design-queued nor gate-queued.
- **Judgment**: CLAUDE.md states the work-item 3-agent pipeline runs *manually* by Claude Code (`af-doc-qa + af-critic + af-cross-review **3개를 병렬 실행**한다`), not via an automated queue — so the "missing wiring" may be intentional. But Cross's concern is reasonable: before this diff, work-item docs were *not* matched by the includes either (they're not `*design*` / `*feature*`), so adding the dated-include + work-item-exclude is a no-op for the automation path. Still, the comment phrasing implies an automated handoff exists.
- **Question for Author**: Is `af-doc-qa` work-item handling intended to remain manual (Claude-Code-driven)? If yes, soften the comment to "별도 경로(Claude Code의 수동 3-agent 호출)로 처리됨" so a future reader doesn't search for nonexistent automation. If no, follow up with the queue route Cross proposed.

#### 4. [ACCEPT] [Low] Redundant flat patterns (`docs/20??-??-??-*.md`, `docs/work-items/*`)
- **Critic**: `_matches_glob()` already matches the flat case via the recursive `**` form; `fnmatch` doesn't treat `/` as special so `docs/work-items/*` ≡ `docs/work-items/**`. Empirically verified.
- **Cross**: not flagged
- **Judgment**: Cosmetic — pre-existing convention in this file (`docs/*design*.md` paired with `docs/**/*design*.md` is the same no-op). No behavior risk.
- **Action Required**: Optional. Either drop the flat duplicates, or add a single comment stating the flat pair is a stylistic mirror, not coverage. Don't fix in this PR if it'd churn the existing legacy pairs.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|-------|
| 1 | `docs/patterns/**` scope expansion | Medium | ACCEPT | Cross |
| 2 | No tests for `is_design_doc()` | Medium | ACCEPT | Critic |
| 3 | Work-item exclusion handoff | Medium | HOLD | Cross |
| 4 | Redundant flat patterns | Low | ACCEPT | Critic |

### Recommendations
- **Before merge (WARN)**: Decide finding #1 — add `docs/patterns/**` to excludes, or update the diff's intent comment to acknowledge patterns docs are now reviewable.
- **Before merge or in next commit**: Add `tests/test_design_review_utils.py` per finding #2 (5+ cases including the resolved patterns case).
- **Clarify in this PR**: Reword the work-item exclusion comment (finding #3) to either "수동 3-agent 호출" or stub in the automated queue route — pick one and stop the comment from over-promising.
- **Defer**: Finding #4 (cosmetic) and Critic's noted M10 issue at `enqueue()` line 224-225 (pre-existing non-atomic JSON write — out of scope).