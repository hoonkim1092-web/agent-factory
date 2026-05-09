# Code Review: work_item_generator

> Source: core/work_item_generator.py
> Date: 2026-05-04 15:53
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

The diff fixes the visible double-prefix render bug with a strong regression test, but it patches the wrong layer and triplicates a string literal that was already flagged as a future-bug source in `docs/code_review/code-review.md:4478`. No critical issues — merge-able with documented risk, but a follow-up cleanup should be queued.

> **Note on Cross Review**: The cross-verification reviewer returned a provider error (Codex stdin read, no findings produced). All findings below come from the Critic only; severity remains as critic-rated since cross-review could not corroborate or escalate.

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [Medium] Fix is in the wrong layer — producer is the real root cause
- **Critic**: Marker `"[LLM prior] "` only exists in `core/researcher.py:630` title string; all other classification signals are structured metadata (`source_type="llm_prior"`, `verified=False`, `weight=0.4`). Fixing only the consumer means future renderers will reintroduce the double-prefix.
- **Cross**: not flagged (provider error)
- **Judgment**: Accept based on diff evidence. The diff at `core/work_item_generator.py:95-98` strips a marker that the producer just added — a classic asymmetric coupling. The producer has structured metadata that already encodes "LLM prior"; the visual prefix is redundant.
- **Action Required**: Drop the marker at `core/researcher.py:630` → `"title": f"{label}: {text[:80]}"`. The consumer's strip is idempotent for existing on-disk JSON. If applied, findings #2, #3, #4 become moot.

#### 2. [ACCEPT] [Medium] Diff regresses against an existing Info finding (literal duplicated 3+ places)
- **Critic**: `docs/code_review/code-review.md:4478` already records the hardcoded-prefix duplication risk and recommends a shared constant. This diff does the opposite — adds the literal to `core/work_item_generator.py:98` (×2) and `tests/test_work_item_generator_references.py:20,37`. Pre-fix: 1 site. Post-fix: 4 sites.
- **Cross**: not flagged (provider error)
- **Judgment**: Accept — directly verifiable via the diff. The literal `"[LLM prior] "` now appears in producer + consumer + 2 test sites with no shared constant. Any single edit will silently no-op the strip.
- **Action Required**: If finding #1 is rejected, define `LLM_PRIOR_TITLE_PREFIX = "[LLM prior] "` once in `core/researcher.py` and import into work_item_generator and tests. If #1 is accepted, this becomes moot.

#### 3. [ACCEPT] [Low] Use `str.removeprefix()` — idiomatic, removes off-by-one risk
- **Critic**: `core/work_item_generator.py:98` uses `raw_label[len("[LLM prior] "):] if raw_label.startswith("[LLM prior] ") else raw_label` — two literal repeats and explicit `len()`. AF targets ≥3.10 (already uses PEP 604 `dict[str, Any]` in this file).
- **Cross**: not flagged (provider error)
- **Judgment**: Accept — pure idiom upgrade, no behavioral change. `str.removeprefix()` is exactly this pattern's stdlib solution. Severity downgraded from critic's Medium to Low because correctness isn't broken; readability/maintenance only.
- **Action Required**: `label = raw_label.removeprefix("[LLM prior] ")`. (Or skip if #1 is taken.)

#### 4. [ACCEPT] [Low] Comment cites a line number that will rot
- **Critic**: `core/work_item_generator.py:95-96` comment says `researcher.py:630` — the function name `_collect_llm_prior_knowledge` is already the stable anchor.
- **Cross**: not flagged (provider error)
- **Judgment**: Accept — line numbers are well-known to rot. Trivial fix.
- **Action Required**: Drop `:630` from the comment, keep only the function name. (Moot if #1 is taken — comment goes away.)

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Fix at wrong layer (producer is root cause) | Medium | ACCEPT | Critic only |
| 2 | Triplicated string literal regresses Info finding | Medium | ACCEPT | Critic only |
| 3 | Use `str.removeprefix()` | Low | ACCEPT | Critic only |
| 4 | Line-number citation will rot | Low | ACCEPT | Critic only |

### Recommendations

- **Preferred path** (collapses all 4 findings): Move the fix to the producer at `core/researcher.py:630` — drop the `"[LLM prior] "` marker from the title. Consumer strip becomes a no-op for new data and idempotent cleanup for old data.
- **Fallback path** (keep consumer-side strip): Extract `LLM_PRIOR_TITLE_PREFIX` constant, replace slice with `removeprefix`, drop `:630` from comment.
- **Positive to retain**: The test fixture at `tests/test_work_item_generator_references.py:20,37` is high-quality — keep the negative regression assertions for `"[LLM prior] [LLM prior]"` and `"LLM prior: [LLM prior]"` regardless of which path is chosen.
- **Cross-review gap**: Cross-verification did not run successfully (Codex provider error). Per Phase 0 policy, Tier 3 with 0 successful external providers auto-passes (SKIP). Consider re-running `af-cross-review` if a Tier 3-eligible provider becomes available before merge.