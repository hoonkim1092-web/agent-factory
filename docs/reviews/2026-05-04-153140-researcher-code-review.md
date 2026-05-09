# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-04 15:31
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

The diff is a clean dead-branch removal — both removed `elif AF_RESEARCH_LLM_FALLBACK=="1"` branches called `self._collect_llm_prior_knowledge(task_input)` with identical args as their `else` siblings, so behavior is preserved. However, the cross reviewer was unavailable (provider error), so findings rest on the critic + diff inspection alone. Two Medium-severity gaps remain: documentation drift and a missing regression test for the second simplified branch.

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [Medium] Documentation/Blueprint drift — `AF_RESEARCH_LLM_FALLBACK` still presented as an active toggle
- **Critic**: Master_Blueprint.md:1280 + docs/plans/2026-05-04-research-system-improvement.md:169-170, 289 + NEXT_STEPS.md:17, 20, 89, 144, 157 still describe the env var as a meaningful switch, even though the code now ignores it.
- **Cross**: not flagged (provider error — review unavailable)
- **Judgment**: ACCEPT. Evidence is direct: the diff strips both `elif os.getenv("AF_RESEARCH_LLM_FALLBACK") == "1":` branches but ships no doc update. CLAUDE.md mandates "코드 수정 + Blueprint 업데이트는 같은 커밋". A user setting this var will get behavior they don't expect (no off-switch).
- **Action Required**: In the same commit, (a) rewrite Master_Blueprint.md:1280 to drop the env var reference, (b) update docs/plans/2026-05-04-research-system-improvement.md:169-170, 289 to mark the toggle as removed, (c) add a §12 entry recording `AF_RESEARCH_LLM_FALLBACK` is now a no-op, (d) update NEXT_STEPS.md lines 17/20/89/144/157 accordingly.

#### 2. [ACCEPT] [Medium] Test coverage gap — second simplified branch (`elif not sufficient:`) is unverified
- **Critic**: `core/researcher.py:717-722` (`not sufficient` + no Tavily) has no regression test. `TestG3TavilyUnsetFallbackPath` only exercises the `requires_web=True` path. NEXT_STEPS.md:144 already flags this gap.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. The two parallel blocks were modified together but only one is tested. Future divergence between them would go silent.
- **Action Required**: Add a regression case asserting `mode != fast_synthesis` AND `requires_web=False` AND `not sufficient` AND `TAVILY_API_KEY` unset → `llm_prior_references` is populated.

#### 3. [ACCEPT] [Low] Asymmetric comment between two structurally identical blocks
- **Critic**: L714-716 has comment `# Tavily 미설정: LLM prior로 fallback (verified=False, weight=0.4 메타데이터 보존)`; L719-722 calls the same function with same args but has no comment. Readers may infer differing intent.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT but Low — cosmetic, not a behavior risk. Per Karpathy 3 (Surgical Changes), don't add cleanup beyond the task; the simplest fix is a one-line comment mirror.
- **Action Required**: Either duplicate the comment on the second `else:` block, or omit both (since the function name is self-describing). Do not extract a helper just for symmetry — that's over-engineering for two callers.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Doc/Blueprint drift on AF_RESEARCH_LLM_FALLBACK | Medium | ACCEPT | Critic only |
| 2 | Missing regression test for `not sufficient` branch | Medium | ACCEPT | Critic only |
| 3 | Asymmetric fallback comment | Low | ACCEPT | Critic only |

### Recommendations
- **Block-level**: None. WARN — merge is acceptable with the doc/test follow-ups in the same commit per project policy.
- Update Master_Blueprint.md, docs/plans/2026-05-04-research-system-improvement.md, NEXT_STEPS.md to reflect that `AF_RESEARCH_LLM_FALLBACK` is now a no-op (or remove all references).
- Add a regression test for the `not sufficient` + Tavily-unset path; without it the symmetry of the two simplified blocks is asserted only by code reading.
- Mirror the fallback comment on the second `else` block (or drop both) — cheap consistency win.
- **Cross-review provider error**: re-run cross-review when the provider is available; current verdict is single-reviewer only and should not be treated as full 2-reviewer consensus.