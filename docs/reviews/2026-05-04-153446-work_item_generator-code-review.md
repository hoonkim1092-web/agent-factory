# Code Review: work_item_generator

> Source: core/work_item_generator.py
> Date: 2026-05-04 15:34
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

Note: the cross-review provider errored out (no findings returned), so this aggregate rests on the critic plus my own diff verification.

## Final Code Review

### Verdict: WARN

The diff itself is a clean, surgical extension of `_reference_bullets` that closes documented defect #1 (LLM prior dropped from work-item docs). However, I confirmed via direct code read that the consumer prefix `- LLM prior:` collides with the producer's `[LLM prior] ` prefix at `core/researcher.py:630`, producing visibly redundant double-tagged bullets in every generated work-item document. The cross-reviewer was unavailable (provider error), so judgments below are made by reading the diff and producer code directly.

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [Medium] Double `"LLM prior:"` prefix in rendered bullets
- **Critic**: At `core/work_item_generator.py:99`, `line = f"- LLM prior: {label}"` is concatenated onto a `label` whose source already prepends `"[LLM prior] "` at `core/researcher.py:630`. Result: `- LLM prior: [LLM prior] Concept: foo bar`.
- **Cross**: not flagged (provider error).
- **Judgment**: Verified directly — `researcher.py:630` emits `"title": f"[LLM prior] {label}: {text[:80]}"` unconditionally, and the new consumer block at `work_item_generator.py:95` reads `item.get("title")` first. The double prefix is deterministic and ships in production.
- **Action Required**: Pick one side. Either:
  - Drop the consumer prefix: `line = f"- {label}"` (title self-identifies), or
  - Strip the producer prefix in the consumer before formatting: `if label.startswith("[LLM prior] "): label = label[len("[LLM prior] "):]`.
  Coordinate the choice in a comment to prevent future drift.

#### 2. [ACCEPT] [Medium] Regression test fixture does not match producer output shape
- **Critic**: `tests/test_work_item_generator_references.py` uses `{"title": "LLM Prior Knowledge", ...}`, but the real producer always prepends `"[LLM prior] "`. Test passes while double-prefix bug slips through.
- **Cross**: not flagged (provider error).
- **Judgment**: Direct consequence of #1 — fixture is misshapen vs. the only producer that writes this slot. Strong evidence.
- **Action Required**: Update fixture title to producer shape (e.g. `"[LLM prior] Concept: model recall fallback"`) and assert the de-duplicated rendered form. This locks in whichever fix is chosen for #1.

#### 3. [ACCEPT] [Medium] `verified=False` provenance silently dropped in rendered bullet
- **Critic**: Producer attaches `verified=False`, `weight=0.4`, `source_type="llm_prior"` (researcher.py:633–636), and derived_notes already record `"llm_prior_references=N (unverified)"`. The bullet renderer surfaces neither flag, so LLM-prior bullets read at the same visual rank as verified `Web:` references.
- **Cross**: not flagged (provider error).
- **Judgment**: Verified — no `verified` / `(unverified)` marker in the new block. Misalignment with derived_notes annotation already present in the codebase. Strong evidence.
- **Action Required**: Append an `(unverified)` marker, conditional on the flag: `if item.get("verified") is False: line += " (unverified)"`. Keeps verified bullets unchanged.

#### 4. [HOLD/Deferred] [Low] Three near-identical loop blocks invite drift
- **Critic**: local/web/llm_prior loops are ~90% identical. Suggests `_render_ref_block(items, prefix, label_keys, marker=None)` helper but explicitly says "do not bundle into this diff."
- **Cross**: not flagged (provider error).
- **Judgment**: Per CLAUDE.md "Surgical Changes" — out of scope for this fix. Track only.
- **Action Required**: None for this PR. Log as deferred refactor in `NEXT_STEPS.md` if not already tracked.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Double `"LLM prior:"` prefix in rendered bullets | Medium | ACCEPT | Critic + diff verify |
| 2 | Regression test fixture mismatches producer shape | Medium | ACCEPT | Critic + diff verify |
| 3 | `verified=False` provenance dropped in bullet | Medium | ACCEPT | Critic + diff verify |
| 4 | Three near-identical loop blocks (drift risk) | Low | DEFER | Critic only |

### Recommendations

- Fix #1 by stripping the producer prefix in the consumer (preserves title field semantics for other readers like `_build_evidence_summary` at researcher.py:663). One-line change.
- Fix #2 by reshaping the fixture to producer output and re-asserting the cleaned single-prefix form. Locks regression in.
- Fix #3 by appending `(unverified)` marker conditional on `item.get("verified") is False`. Aligns rendered docs with derived_notes annotation.
- Re-run `tests/test_work_item_generator_references.py` after edits.
- Re-run cross-review (Tier 3) once the OpenAI Codex provider is available — current verdict is critic-only with my diff verification standing in for the second opinion.
- Defer #4 to a follow-up refactor; do not bundle.