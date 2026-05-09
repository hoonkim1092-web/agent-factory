# Code Review: work_item_generator

> Source: core/work_item_generator.py
> Date: 2026-05-07 00:41
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

WARN = High/Medium findings only. No Critical blockers. Can merge with documented risks.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [High] `domain_specs_summary` type not validated — crash or silent corruption

- **Critic**: "`_clean(v)` converts dict/list to Python repr string if `state_machine` is not str" (Finding 3)
- **Cross**: "`_fallback_impl_design()` calls `.get()` directly on `domain_specs_summary`; if it's not a dict (e.g. `"domain_specs_summary": "..."`), raises `AttributeError`" (Finding 1 — ACCEPT)
- **Judgment**: Two independent reviewers flagged the same zone (line 423–424). Critic caught the output corruption case; Cross caught the crash case. The diff introduces `_specs_sum = project_brief.get("domain_specs_summary") or {}` — the `or {}` fallback handles `None` but **not** a non-dict non-falsy value (e.g. a string `"..."` is truthy and `.get()` will raise). Higher severity (crash) wins.
- **Action Required**:
  ```python
  _specs_sum_raw = project_brief.get("domain_specs_summary")
  _specs_sum = _specs_sum_raw if isinstance(_specs_sum_raw, dict) else {}
  _state_machine = _clean(_specs_sum.get("state_machine")
                          if isinstance(_specs_sum.get("state_machine"), str) else "")
  ```

#### 2. [ACCEPT] [Medium] Magic number `800` without named constant

- **Critic**: "800 has no module-level constant; comment says '프롬프트 크기 제한' but this is written into the saved fallback doc, not the LLM prompt" (Finding 1)
- **Cross**: Not flagged
- **Judgment**: Single reviewer, but evidence is directly in the diff (`_state_machine[:800]`). The comment is factually wrong (this is a doc truncation limit, not a prompt limit), which makes the magic number doubly confusing. Strong enough to accept.
- **Action Required**: Add `_STATE_MACHINE_FALLBACK_LIMIT = 800` at module top; fix comment to "fallback 문서 Phase Flow 최대 길이".

#### 3. [ACCEPT] [Medium] Truncation without marker — output cut mid-sentence

- **Critic**: "800자 초과 시 아무 표시 없이 절단 → downstream agent가 잘린 phase를 완전한 spec으로 오독 가능" (Finding 2)
- **Cross**: Not flagged
- **Judgment**: Single reviewer, but the risk is concrete and traceable: `_state_machine[:800]` with no ellipsis or notice. Downstream `implementation-design.md` readers (agents, reviewers) have no signal that content was dropped. Accept on strong evidence.
- **Action Required**:
  ```python
  if len(_state_machine) > _STATE_MACHINE_FALLBACK_LIMIT:
      _phase_text = _state_machine[:_STATE_MACHINE_FALLBACK_LIMIT].rsplit("\n", 1)[0]
      _phase_text += "\n*(state machine content truncated)*"
  else:
      _phase_text = _state_machine
  ```

#### 4. [ACCEPT] [Medium] Mandatory section not structurally enforced after LLM generation

- **Critic**: Not flagged
- **Cross**: "Prompt marks `Event Sequence / Phase Flow` as mandatory, but `_generate_and_refine()` only scans forbidden tokens; LLM can silently omit the section without triggering any retry or error" (Finding 2 — ACCEPT)
- **Judgment**: Single reviewer, but evidence is solid: line 640 adds `"Event Sequence / Phase Flow는 반드시 작성 (생략 불가)"` to the prompt instruction, yet lines 858–884 only refine on forbidden-token hits. There is no structural check that the section exists in the output. Prompt-only enforcement is not enforcement.
- **Action Required**: Add a post-generation structural check in `_generate_and_refine()` or a dedicated validator:
  ```python
  if "## Event Sequence / Phase Flow" not in result["text"]:
      # treat as forbidden-token hit and retry, or raise
  ```
  Or update `scripts/prompts/doc_critic.txt` to require this section — but prefer a code-level check.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `domain_specs_summary` type not validated | High | ACCEPT | Both |
| 2 | Magic number `800` without named constant | Medium | ACCEPT | Critic |
| 3 | Truncation without marker | Medium | ACCEPT | Critic |
| 4 | Mandatory section not structurally enforced | Medium | ACCEPT | Cross |

---

### Recommendations

- Fix #1 first (crash path) — add `isinstance` guard before `.get()` on both `domain_specs_summary` and `state_machine`. Add a regression test with `"domain_specs_summary": "plain string"`.
- Fix #2 and #3 together — they share the same line; extract the constant and add the truncation marker in one edit.
- Fix #4 — add a structural post-check for `## Event Sequence / Phase Flow` in the LLM output validation path; do not rely on prompt wording alone.
- Cross Finding 3 (template mismatch) was correctly rejected — no action needed; the template is not used in the automated code path.