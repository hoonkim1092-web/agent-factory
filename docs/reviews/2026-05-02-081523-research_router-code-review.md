# Code Review: research_router

> Source: core/research_router.py
> Date: 2026-05-02 08:15
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

The diff is a no-op (`core/research_router.py` not yet created), so there is nothing to block on in the change itself. However, the Cross Review surfaced **3 high-confidence integration bugs in existing production files** that must be resolved before or alongside the implementation of `core/research_router.py`. These are not hypothetical — they are observable gaps between the written code and the intended design.

---

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [High] `detect_complexity_gaps()` is never called in the production path
- **Critic**: not flagged (no diff to inspect)
- **Cross**: `core/research_router.py:174` — only test code calls `detect_complexity_gaps()`; `ProjectPipeline` flows through `ResearchVerifier.verify_with_retry()` → `Researcher.collect_project_evidence()` → `gap_to_mode()` without ever invoking the router detector
- **Judgment**: Strong evidence. The call chain is traced across three files (`core/project_pipeline.py:664`, `core/research_verifier.py:246`, `core/researcher.py:522`). Poker/mobile multi-client fixtures can pass tests via `_simulate_final_mode()` while the live pipeline stays on `fast_synthesis` — a silent correctness gap.
- **Action Required**: Wire `ResearchRouter().detect_complexity_gaps(task_input, evidence, plan.mode)` into the production retry boundary (after initial evidence collection), and merge the typed gaps with verifier gaps before the retry path.

#### 2. [ACCEPT] [High] `ProjectPipeline._evidence_fn` swallows `TypeError`, breaking `ResearchVerifier`'s legacy fallback
- **Critic**: not flagged
- **Cross**: `core/project_pipeline.py:653-660` catches all exceptions internally; `ResearchVerifier` at `core/research_verifier.py:247` expects `TypeError` to surface so it can retry without `hint_gaps`, but never sees it
- **Judgment**: Strong evidence. The existing test coverage uses a `**kwargs` dummy — not a legacy callable (`lambda task_input, workspace=None`). The fallback is dead code in practice.
- **Action Required**: Either inspect the callable for `hint_gaps`/`**kwargs` support before calling and strip unsupported kwargs upfront, or let `TypeError` propagate so `ResearchVerifier`'s catch block works as written.

#### 3. [ACCEPT] [High] Escalation in `Researcher` partially mutates `ResearchPlan`, leaving derived flags stale
- **Critic**: not flagged
- **Cross**: `core/researcher.py:526-532` updates `mode`, `requires_web`, `requires_notebooklm` but not `requires_tavily_extract`, `requires_deep_source_pack`, or `risk_level`
- **Judgment**: Strong evidence. `ResearchRouter._select_mode()` derives all six fields together at `core/research_router.py:249-257`; the escalation path only updates three. A serialized plan can have `mode="deep_source_research"` alongside `requires_deep_source_pack=False` and `risk_level="normal"` — internally inconsistent.
- **Action Required**: Add a router-owned `escalate(plan, gaps)` or `plan_for_mode(request, mode)` method that recomputes all derived fields atomically. Replace the three-field mutation in `Researcher` with that helper.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `detect_complexity_gaps()` not wired in production | High | ACCEPT | Cross |
| 2 | `_evidence_fn` swallows `TypeError`, breaks verifier fallback | High | ACCEPT | Cross |
| 3 | Partial `ResearchPlan` mutation leaves derived flags stale | High | ACCEPT | Cross |

---

### Recommendations

- **Before writing `core/research_router.py`**: Fix finding #3 first — the `ResearchPlan` mutation bug is in `core/researcher.py` and is independent of the new file. Introduce the `escalate()` helper there.
- **During implementation of `core/research_router.py`**: Address finding #1 by making `detect_complexity_gaps()` a mandatory step in the production retry path, not just a test utility.
- **In the same PR**: Fix finding #2 in `core/project_pipeline.py` so the verifier's `TypeError` fallback actually works.
- **Reminder (Critic)**: When `core/research_router.py` is committed, add `"core.research_router"` to `af.spec` `hiddenimports` in the same commit to avoid a frozen-build miss (recurring pattern M9).