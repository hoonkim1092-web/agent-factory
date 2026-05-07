# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-07 15:21
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. Two Medium issues are directly in the diff. Two pre-existing issues surfaced by the cross reviewer.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [Medium] `or` coercion silently re-runs detection on explicitly-empty domain
- **Critic**: "When `research_plan.domain == ""`, `or` triggers `_detect_domain` again — the distinction between 'not yet checked' and 'checked, found empty' is lost."
- **Cross**: Not flagged.
- **Judgment**: This is the actual diff line. Old code: `research_plan.domain if research_plan else ""` — preserves `""` as a deliberate result. New code: `(...) or ResearchRouter()._detect_domain(task_input)` — re-runs detection when domain is empty string. The behavioral difference is real and subtle. Currently non-breaking (re-detection returns `""` for non-poker), but the semantics are wrong: `""` means "detected, no match" and should not trigger a second detection pass.
- **Action Required**: Use explicit sentinel to distinguish the two states:
  ```python
  prev_domain = research_plan.domain if research_plan else None
  if prev_domain is None:
      prev_domain = ResearchRouter()._detect_domain(task_input)
  ```

#### 2. [ACCEPT] [Medium] Private method called from outside the class
- **Critic**: "`ResearchRouter()._detect_domain(task_input)` bypasses the public API boundary. IDE/linters won't flag breakage if `_detect_domain` is renamed or moved."
- **Cross**: Not flagged.
- **Judgment**: Directly in the diff. The public path `ResearchRouter().plan(task_input)` already calls `_detect_domain` internally. The existing call at line 914 uses `.plan()` correctly; this new call at line 909 breaks the convention within the same function. Critic confirms `_detect_domain` has no instance state dependency, making it even cheaper to expose as a public method.
- **Action Required**: Add `def detect_domain(self, request: str) -> str: return self._detect_domain(request)` to `ResearchRouter`, then use `ResearchRouter().detect_domain(task_input)` at line 909.

#### 3. [ACCEPT] [High] Non-web sources lost in `_emit_evidence_files`, breaking claim-source links *(pre-existing)*
- **Critic**: Not flagged.
- **Cross**: "`_emit_evidence_files()` at line 641 keeps only `source_type=='web'`. Claims backed by `local_001`/`llm_001` source IDs lose their valid-source mapping."
- **Judgment**: Not in this diff, but cross reviewer traced the full path: `_build_source_pack()` (line 401) generates web/local/llm sources → `_synthesize_structured_evidence()` (line 471) references all IDs in the prompt → `_emit_evidence_files()` (line 641) discards non-web entries. The evidence chain is coherent. This is a pre-existing defect surfaced during review. Severity is High because it silently corrupts the evidence output.
- **Action Required**: File a separate bug. In `_emit_evidence_files()`, include all source types in `valid_source_ids` and serialized output; apply authority/confidence differentials by type rather than by filtering.

#### 4. [HOLD] [Medium] `trust_score` semantics diverge between collection and storage *(pre-existing)*
- **Critic**: Not flagged.
- **Cross**: "`_collect_web_references` (line 376) sets `trust_score` as authority (0.0/0.4), but `_emit_evidence_files` (line 648) overwrites it with `relevance_score`. Same field name, different meaning."
- **Judgment**: Not in this diff. Evidence of the field divergence is credible, but the downstream consumer of this JSON is unspecified. Cannot determine blast radius without knowing what reads `trust_score` from stored evidence files.
- **Question for Author**: What consumes the `trust_score` field from the emitted `evidence.json`? Is it displayed in UI, used in scoring, or only informational? This determines whether the overwrite is a silent defect or a harmless rename.

---

### Summary Table

| # | Title | Severity | Verdict | Source | In Diff |
|---|-------|----------|---------|--------|---------|
| 1 | `or` coercion re-runs detection on empty domain | Medium | ACCEPT | Critic | Yes |
| 2 | Private method called from outside class | Medium | ACCEPT | Critic | Yes |
| 3 | Non-web sources lost in `_emit_evidence_files` | High | ACCEPT | Cross | No (pre-existing) |
| 4 | `trust_score` semantics diverge | Medium | HOLD | Cross | No (pre-existing) |

---

### Recommendations

- **Before merge**: Fix Finding 1 (sentinel pattern instead of `or`) and Finding 2 (expose `detect_domain` as public method) — both are in the diff, both are small, low-risk changes.
- **File separate issues**: Finding 3 (non-web source loss) and Finding 4 (trust_score semantics) are pre-existing and outside the scope of this diff. Track them independently.
- **Finding 4**: Resolve the HOLD by identifying what consumes the emitted `trust_score` field before deciding whether to split the field.