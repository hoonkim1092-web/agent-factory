# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-04 15:31
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: **WARN**

Cross review is unavailable (provider error — only stdin echo returned, no findings produced). Final verdict relies on the critic review alone, with diff cross-checked. Code-side cleanup is correct and complete; remaining items are documentation/coverage follow-throughs from the prior round, not runtime defects.

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] Master_Blueprint.md deprecation entry missing — violates same-commit rule
- **Critic**: Env var `AF_RESEARCH_LLM_FALLBACK` was a documented kill-switch (`Master_Blueprint.md:1280`, `docs/plans/2026-05-04-research-system-improvement.md:289`); removal must accompany a §12 deprecation entry per CLAUDE.md "코드 수정 + Blueprint 업데이트는 같은 커밋."
- **Cross**: not flagged (provider error).
- **Judgment**: Diff confirms `Master_Blueprint.md` is unmodified. CLAUDE.md rule is explicit and the prior critic round (`docs/reviews/2026-05-04-151344-researcher-code-review.md:26`) made it a documented requirement. ACCEPT on critic evidence alone.
- **Action Required**: Append §12 entry: `2026-05-04 | (unreleased) | refactor(researcher): AF_RESEARCH_LLM_FALLBACK 폐기 — toggle on/off 양 분기가 동일 호출이라 의미 상실. TAVILY 미설정 시 LLM prior 항상 호출(verified=False, weight=0.4 보존).` Same commit as the code change. Update §0 if the env var is listed.

#### 2. [ACCEPT] [Medium] Second mutation site (`elif not sufficient`) has zero regression coverage
- **Critic**: Diff modifies both branches at `core/researcher.py:710-722`, but the only G3 test (`tests/test_research_system_regression.py:90-120`) uses `ResearchPlan.for_mode("fresh_lookup")` (`requires_web=True`), exercising only line 710-716. The `archive_research` path (`requires_web=False`) hitting line 717-722 is untested.
- **Cross**: not flagged (provider error).
- **Judgment**: Verifiable from diff + cited test fixture. Prior critic's Finding 2 was ACCEPTED but not addressed in this round. Coverage gap is real.
- **Action Required**: Add `TestG3TavilyUnsetFallbackPathArchive` mirroring the existing G3 case but with `ResearchPlan.for_mode("archive_research")` + `_is_sufficient=False` to exercise the second branch. ~5 LoC.

#### 3. [HOLD] [Medium] Two elif branch bodies are now byte-identical — duplication invites drift
- **Critic**: After removal, `core/researcher.py:710-716` and `:717-722` have identical bodies; only entry conditions differ. Same pattern as M5 in `code-review.md` (`agent_runner.py:352-489`).
- **Cross**: not flagged (provider error).
- **Judgment**: Diff confirms the duplication. However, collapsing to `elif research_plan.requires_web or not sufficient:` changes semantics subtly — the two branches were intentionally separate decision paths in the original logic ("fresh_lookup/deep/live: Tavily ON sufficiency gate 무시" vs. "archive_research: 기존 sufficiency gate 유지"). The collapse merges those intents. HOLD pending author decision: keep separate-with-comments (preserves intent) or collapse (eliminates duplication).
- **Question for Author**: Should the two branches stay separate (intent-preserving) or collapse (simplicity-first)? If Finding 2 test is added, the separate-branch case becomes defensible.

#### 4. [ACCEPT] [Low] Stale env-var references in plan docs
- **Critic**: `docs/plans/2026-05-04-research-system-improvement.md:169-170, 289` still describe `AF_RESEARCH_LLM_FALLBACK=1` as a runtime opt-in / kill-switch.
- **Cross**: not flagged (provider error).
- **Judgment**: Verifiable; plan doc misleads operators. Low severity (historical doc), but trivial to annotate.
- **Action Required**: Annotate lines 169-170 and 289 with "(폐기 2026-05-04)" or strike-through. Same commit recommended.

#### 5. [HOLD] [Low] No silent-deprecation warning at runtime
- **Critic**: Operators with `AF_RESEARCH_LLM_FALLBACK=1` (or `=0`) in environment receive no signal that the variable is ignored.
- **Cross**: not flagged (provider error).
- **Judgment**: Optional per critic. Project has no documented stance on deprecation warnings. HOLD — author preference call.
- **Question for Author**: Emit one-time `logger.warning(...)` at module import if env var is set, or rely on Master_Blueprint §12 entry alone?

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Master_Blueprint §12 deprecation entry missing | High | ACCEPT | Critic (cross unavailable) |
| 2 | `elif not sufficient` branch has no regression test | Medium | ACCEPT | Critic (cross unavailable) |
| 3 | Two elif branch bodies are byte-identical | Medium | HOLD | Critic (cross unavailable) |
| 4 | Stale env-var refs in plan doc | Low | ACCEPT | Critic (cross unavailable) |
| 5 | No runtime deprecation warning | Low | HOLD | Critic (cross unavailable) |

### Recommendations

- **Same commit**: add Master_Blueprint §12 entry (Finding 1) + annotate `docs/plans/2026-05-04-research-system-improvement.md` (Finding 4). These satisfy the CLAUDE.md same-commit rule.
- **Same commit or follow-up**: add `TestG3TavilyUnsetFallbackPathArchive` (Finding 2) — closes the prior round's accepted-but-unaddressed coverage gap.
- **Defer to author**: branch collapse (Finding 3) and runtime deprecation warning (Finding 5) — neither blocks; pick based on simplicity-first vs. intent-preservation preference.
- **Re-run cross review**: provider returned only the prompt echo (Codex stdin error). Re-invoke `af-cross-review` to confirm no findings were missed before merge — current verdict is single-reviewer.