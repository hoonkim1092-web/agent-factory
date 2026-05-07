# Code Review: project_pipeline

> Source: core/project_pipeline.py
> Date: 2026-05-07 09:16
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

High findings exist (stale file write after in-memory mutation). No Critical issues. Can merge with documented risks but the persistence bug warrants a follow-up fix.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [High] Enriched `research_plan` not persisted to `project_brief.json`
- **Critic**: "In-place mutation of caller-owned `project_brief`" — flags side effect risk
- **Cross**: "Enriched `research_plan` is not persisted to `project_brief_path` or research brief JSON" — files written at lines 795–804 **before** this injection at line 893; `agent_launcher.py:417–419` prints the stale on-disk brief to the user
- **Judgment**: Both reviewers flag the same mutation. Cross provides concrete line-number evidence of write order. This is a real bug: downstream consumers (user-visible output, checkpoint readers) see a brief that lacks the injected `research_plan`. ACCEPT at High.
- **Action Required**: Either (a) move the injection into `prepare_brief()` before both file writes, or (b) re-write `project_brief_path` immediately after injection at line 896.

---

#### 2. [ACCEPT] [Medium] Partial `research_plan` without `domain` still bypasses domain gate
- **Critic**: Not flagged
- **Cross**: "If a caller provides a partial `research_plan` without `domain`, `_domain` remains empty and C1 spec/coverage enforcement is skipped" — evidenced by `core/researcher.py:1235–1244` not requiring a full plan, and `project_pipeline.py:900` reading only `["research_plan"]["domain"]`
- **Judgment**: Single reviewer, but the evidence is specific and code-grounded. The current guard is all-or-nothing (`not project_brief.get("research_plan")`): if the caller pre-populates even an empty dict `{}`, the injection is skipped entirely, leaving `_domain` unset. Real functional gap. ACCEPT.
- **Action Required**: Replace wholesale-replace logic with a field-level merge that preserves evidence `domain` even when `project_brief` already has a partial `research_plan`:
  ```python
  brief_plan = project_brief.get("research_plan") if isinstance(project_brief.get("research_plan"), dict) else {}
  evidence_plan = research_evidence.get("research_plan") if isinstance(research_evidence.get("research_plan"), dict) else {}
  merged = {**evidence_plan, **brief_plan}
  if evidence_plan.get("domain"):
      merged["domain"] = evidence_plan["domain"]
  if merged:
      project_brief["research_plan"] = merged
  ```

---

#### 3. [ACCEPT] [Medium] Non-dict truthy `research_evidence` passes type guard, risks `AttributeError`
- **Critic**: "Bare truthiness check passes non-empty strings or mock objects; `.get()` on a non-dict raises `AttributeError`"
- **Cross**: Not explicitly flagged (Cross finding #1 implicitly uses `isinstance` in its suggestion)
- **Judgment**: Single reviewer, but the defect is mechanically sound. `and research_evidence:` admits any truthy value; `research_evidence.get(...)` then fails if it is not a dict. Practically rare in production but triggered by integration test stubs and malformed evidence objects. ACCEPT at Medium.
- **Action Required**: `if not project_brief.get("research_plan") and isinstance(research_evidence, dict):`

---

#### 4. [ACCEPT] [Medium] Falsy non-None `research_plan` silently replaced with `{}`
- **Critic**: "`or {}` swallows `False`, `0`, `[]`, etc. — matches the H3 silent-fallback anti-pattern already registered in the codebase"
- **Cross**: Not flagged independently (rejected test-coverage concern is unrelated)
- **Judgment**: Single reviewer, but the H3 precedent in the codebase makes this a known category. An upstream LLM parse failure returning `research_plan: []` would be silently discarded here with no log/warning. Medium severity matches existing codebase classification. ACCEPT.
- **Action Required**: Explicit `None` check instead of `or {}`:
  ```python
  _rp_from_ev = research_evidence.get("research_plan")
  if _rp_from_ev is not None and _rp_from_ev:
      project_brief["research_plan"] = _rp_from_ev
  ```

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Enriched `research_plan` not persisted to disk | High | ACCEPT | Both |
| 2 | Partial `research_plan` bypasses domain gate | Medium | ACCEPT | Cross |
| 3 | Non-dict truthy `research_evidence` risks `AttributeError` | Medium | ACCEPT | Critic |
| 4 | Falsy non-None `research_plan` silently dropped | Medium | ACCEPT | Critic |

---

### Recommendations

1. **Fix #1 first** (High) — move `research_plan` injection before the `project_brief.json` write in `prepare_brief()`, or add a re-write after line 896. Without this, the on-disk state diverges from the in-memory state used for spec generation.
2. **Combine fixes #2 + #3 + #4** — replace the 5-line injection block with the field-level merge from finding #2's suggestion; it already uses `isinstance` (fixes #3) and avoids `or {}` (fixes #4).
3. **Add a test** covering the `PreparedBrief(research_evidence={"research_plan": {"domain": "poker"}}, project_brief={})` → `prepare_documents()` boundary — Cross confirmed existing regression tests do not exercise this path.