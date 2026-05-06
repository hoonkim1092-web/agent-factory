# Design Review: 2026-05-03-phase2-verdict-label-spec

> Source: docs/2026-05-03-phase2-verdict-label-spec.md
> Date: 2026-05-03 23:06
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

> **Note**: Cross Review provider returned an error (codex usage limit, recovery 2026-05-05 15:37 KST). Aggregation proceeds based on Critic Review only, which carries strong code/line references. Per §1 line 9 of the design document itself, **v4 cross-review must be re-run before Phase 2 commit** — this final verdict remains provisional until cross-review completes.

### Aggregated Findings (8 total + 4 design gaps)

#### 1. [ACCEPT] [Critical] §5.5 `_log_hook_event()` signature mismatch — implementation impossible
- **Critic**: spec calls `_log_hook_event(workspace, "verdict_fallback", {...})` but actual signature at `scripts/hook_runner.py:100` is `(builtin: str, file: str, exit_code: int, error: str = "")`. Function body writes a fixed line — no dict payload path exists. v4 as written would raise TypeError or pollute hook_events.log.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. Direct code reference (line 100), exact signature mismatch demonstrated. This single finding is sufficient to BLOCK.
- **Action Required**: §5.5 must specify either (a) a new `_log_hook_event_structured(workspace, event_type, payload)` writing to `hook_structured.jsonl`, or (b) a signature-compatible call form. Critic recommends (a).

#### 2. [ACCEPT] [High] §5.3 wrapper integration target mis-stated
- **Critic**: §5.3 claims `is_gate_blocked()`, `record_review_done()`, `_compute_round_summary()` will use the wrapper, but `is_gate_blocked()` reads `r.get("verdict")` only, `record_review_done()` takes verdict as a parameter, and `_compute_round_summary()` doesn't exist. The single real content-parser is `hook_runner.py:_post_agent_record()` L338-344.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. Specific function-by-function evidence in review_gate.py. Following the spec literally would leave the actual collision site untouched.
- **Action Required**: Rewrite §5.3 to designate `hook_runner.py:_post_agent_record` L339-344 as the unique caller; keep review_gate.py functions unchanged. Sync §7.3 step 2.

#### 3. [ACCEPT] [High] §5.5 verdict_fallback fires false-positive on every af-test-runner completion
- **Critic**: af-test-runner output `[af-test-runner] PASS: N tests passed` matches neither `_VERDICT_RE` nor `_VERDICT_HEADER_RE` → silent "pass" fallback always taken. Every T1 completion would emit `verdict_fallback`, saturating §9.1's "≥ 1 event/week" trigger and rendering the monitoring signal useless.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. Concrete output format reference (af-test-runner.md:78) and integration with `_apply_test_gap_verdict()` at hook_runner.py:349.
- **Action Required**: Gate fallback logging by agent — exclude `af-test-runner` (T1 verdict comes from test-gap analyzer). Restrict §9.1 monitoring trigger to T2/T3.

#### 4. [ACCEPT] [High] §5.3 last-match fallback risks af-critic regression
- **Critic**: af-critic does not adopt fence (§5.2 unchanged) but allows verdict on first or last line (af-critic.md:92), and uses `Verdict: PASS (...)` markers in body (critic.md:51). Switching fence-absent fallback to last-match can prefer in-body quotation over the genuine first-line verdict.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. Cross-references to af-critic.md show concrete regression cases.
- **Action Required**: Decide explicitly — either (a) keep first-match for fence-absent agents and require fence on cross-review with a `verdict_fallback` event for out-of-fence verdict lines, or (b) keep last-match but add af-critic regression test in §7.2 + rationale in §4.

#### 5. [ACCEPT] [Medium] §4.3 severity-missing fail-safe BLOCK is too aggressive for `[ACCEPT-ADV]`/`[BONUS]`
- **Critic**: Same §4.3 defines `[ACCEPT-ADV]` as always WARN, but row "(severity missing → fail-safe default) → BLOCK" overrides this for advisory-only labels, contradicting policy intent.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. Internal contradiction within §4.3 is unambiguous.
- **Action Required**: Split fail-safe by label: `[ACCEPT]`/`[ACCEPT★]` + missing → BLOCK; `[ACCEPT-ADV]`/`[BONUS]` + missing → WARN. Update §7.1 scenario 9 to use `[ACCEPT★]`.

#### 6. [ACCEPT] [Medium] §5.1 fence collision still possible — fence text quoted in body
- **Critic**: G7 mitigation assumes LLM never quotes fence markers. But Step 5 prompts encourage prior-round quotation, the v4 doc itself quotes the fence at lines 268-272, and future review replies will naturally cite fence markers.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. The design document quoting its own fence marker (self-evidence) is a strong demonstration of the risk.
- **Action Required**: Use `re.findall(...)[-1]` to take the last fence pair; add Step 5 guidance to escape fence markers when quoting; add a fake-fence + real-fence collision case to §7.2.

#### 7. [ACCEPT] [Medium] §8 self-host bootstrap problem undefined
- **Critic**: review_gate.py / hook_runner.py / review_metrics_logger.py are core review-gate infrastructure. Self-validating them on the same review-gate is a chicken-and-egg problem; if hook_runner breaks, the gate cannot decide whether to block.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. The Phase-2 commit mechanically depends on the very files being changed — no rollback path is specified.
- **Action Required**: Add bootstrap plan to §8: (a) initial stage with `AF_SKIP_REVIEW_GATE=1`, (b) self-test via §9.4 + `pytest tests/test_review_gate*.py tests/test_review_metrics_logger.py`, (c) only push after pass. Tie this to §9 rollback as a precondition.

#### 8. [ACCEPT] [Low] §9.4 pytest `-k "collision or fence"` matches zero tests today
- **Critic**: Those tests don't exist yet (added in §7.2). pytest exits 5 (no tests collected); user may misread as PASS.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. Easy fix, but a real gotcha.
- **Action Required**: Annotate §9.4 as "post-implementation"; mark §8 step 2 (test addition) as a precondition.

#### Design Gaps (from Critic "Missing")

- **G-A**: §5.5 / §9.1 must add a paragraph on T1 verdict path (test_gap analyzer) interaction with fallback logging — directly tied to Finding #3.
- **G-B**: §5.3 or §5.5 must declare the single source of truth for `_extract_verdict_from_content()` returning `None` (e.g., "None → silent 'pass' + verdict_fallback event").
- **G-C**: §10 must specify how `docs/reviews/` 30 historical entries are treated for the §9.1 baseline (parsed / excluded / manually labeled).
- **G-D**: §6 (non-goals) or §5 must declare frozen-build implications for hook_runner import path.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `_log_hook_event` signature mismatch | Critical | ACCEPT | Critic |
| 2 | §5.3 wrapper target mis-stated | High | ACCEPT | Critic |
| 3 | verdict_fallback false-positive on T1 | High | ACCEPT | Critic |
| 4 | last-match fallback regresses af-critic | High | ACCEPT | Critic |
| 5 | severity-missing fail-safe over-blocks advisory | Medium | ACCEPT | Critic |
| 6 | fence body-quotation collision | Medium | ACCEPT | Critic |
| 7 | self-host bootstrap undefined | Medium | ACCEPT | Critic |
| 8 | §9.4 pytest filter matches zero tests | Low | ACCEPT | Critic |
| G-A | T1 fallback interaction missing | — | ACCEPT | Critic |
| G-B | None-return contract missing | — | ACCEPT | Critic |
| G-C | retroactive 30-review baseline policy | — | ACCEPT | Critic |
| G-D | frozen-build path implications | — | ACCEPT | Critic |

### Recommendations

Before implementation:
1. **Resolve Finding #1 first** — it alone makes v4 unbuildable. Pick option (a): new `_log_hook_event_structured` + `hook_structured.jsonl` sink, and update §5.5 + `review_metrics_logger` aggregation accordingly.
2. **Rewrite §5.3** to name `hook_runner.py:_post_agent_record` L339-344 as the sole call site; remove fictitious `_compute_round_summary` reference.
3. **Decide fallback policy** (Finding #4) explicitly — first-match vs last-match — and pin the rationale in §4 with a §7.2 regression case.
4. **Make `verdict_fallback` agent-aware** (Finding #3) — exclude T1, restrict §9.1 trigger to T2/T3.
5. **Split severity-missing fail-safe by finding label** (Finding #5).
6. **Add bootstrap protocol to §8** (Finding #7) — `AF_SKIP_REVIEW_GATE=1` first stage + self-test gate before push.
7. **Re-run af-cross-review on v5** once codex usage limit recovers (≥ 2026-05-05 15:37 KST). Per §1 line 9, this is a Phase-2 commit precondition; the present aggregation cannot substitute for it.
8. Address gaps G-A through G-D in v5 to remove ambiguity for the implementer.