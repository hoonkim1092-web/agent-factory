# Code Review: work_item_generator

> Source: core/work_item_generator.py
> Date: 2026-05-04 15:35
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

Cross Review failed with a provider error (truncated stdin), so aggregation relies on Critic findings + diff evidence only. No Critical patterns present; the diff is a small, symmetric addition to `_reference_bullets()`. Two Medium findings are concrete enough to ACCEPT on Critic + diff evidence alone; one Medium is HOLD pending cross-verification; two Low items are accepted as advisory.

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [Medium] Double-prefix in production output
- **Critic**: `label` comes from `item["title"]` which `_collect_llm_prior_knowledge()` already prefixes with `[LLM prior]` (researcher.py:630), so rendered line becomes `- LLM prior: [LLM prior] Concept: foo`. Test fixture uses a hand-stripped title and misses this.
- **Cross**: not available (provider error)
- **Judgment**: Verified in diff + researcher.py:630 reference. The rendering redundancy is real on production data; the test gap is real.
- **Action Required**: Either strip the leading `[LLM prior] ` from `label` in work_item_generator.py:95, or drop the `LLM prior:` bullet prefix. Add a test fixture using the actual researcher-produced title shape (`"[LLM prior] X: …"`).

#### 2. [ACCEPT] [Medium] Unverified-evidence signal not surfaced
- **Critic**: `verified=False, weight=0.4, source_type="llm_prior"` metadata (researcher.py:633-636) is dropped at render time, so the downstream LLM cannot distinguish citation-backed claims from model-recall claims — defeating the purpose of the upstream P3 G3 metadata split.
- **Cross**: not available
- **Judgment**: This is the strongest finding. It directly undermines the work-item that motivated the change. Diff confirms only `title` + `excerpt` are emitted.
- **Action Required**: Append `(unverified)` to the line, or render a separate `### Unverified prior knowledge` subsection.

#### 3. [HOLD] [Medium] Dead `url` fallback path
- **Critic**: `_collect_llm_prior_knowledge()` always writes `"url": ""` and a non-empty `"title"`, so `or item.get("url")` is unreachable for this slot.
- **Cross**: not available
- **Judgment**: Code-evidence supports the claim, but it's stylistic — copy-paste from the web_references block. Without a second opinion confirming there's no future caller injecting urls into `llm_prior_references`, prefer to keep the defensive fallback.
- **Question for Author**: Will any future producer ever populate `url` for an llm_prior item, or is `title` truly the only contract?

#### 4. [ACCEPT] [Low] Master_Blueprint.md not updated in the same diff
- **Critic**: CLAUDE.md mandates Blueprint update in the same commit; §12 has no entry, §0 doesn't reflect `_reference_bullets` LLM-prior path.
- **Cross**: not available
- **Judgment**: Direct CLAUDE.md rule violation, verifiable via `git diff Master_Blueprint.md` (empty).
- **Action Required**: Add §12 entry such as `feat(work_item): _reference_bullets emits llm_prior_references slot (P3 G3 follow-up)`.

#### 5. [ACCEPT] [Low] Shared `limit=8` may starve LLM prior
- **Critic**: Local → Web → LLM prior ordering against shared budget; with ≥8 local refs the new code path is unreachable.
- **Cross**: not available
- **Judgment**: Behaviorally accurate. Likely intentional (verified > unverified), but undocumented.
- **Action Required**: Add a one-line comment documenting the policy ("LLM prior fills only slots verified sources don't claim"), or accept as-is in the §12 entry.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Double-prefix in rendered bullet | Medium | ACCEPT | Critic+Diff |
| 2 | Unverified-evidence signal lost | Medium | ACCEPT | Critic+Diff |
| 3 | Dead `url` fallback for llm_prior | Medium | HOLD | Critic |
| 4 | Blueprint not updated | Low | ACCEPT | Critic+Rule |
| 5 | LLM prior starved by shared limit | Low | ACCEPT | Critic |

### Recommendations
- Strip the upstream `[LLM prior] ` prefix in `label` (or drop the bullet's `LLM prior:` prefix) to fix #1; extend `tests/test_work_item_generator_references.py` with a fixture mirroring the real researcher title shape.
- For #2, append a verification marker (e.g., `(unverified)`) or split into a separate subsection so downstream LLMs respect the `verified=False, weight=0.4` contract.
- Add the §12 history entry to `Master_Blueprint.md` in the same commit (#4).
- Document the priority/starvation policy in a one-line comment near the new loop (#5).
- Re-run af-cross-review (Tier 3) — current Cross Review aborted with a provider error; do not consider this verdict final until a second independent review completes successfully.