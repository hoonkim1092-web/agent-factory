# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-06 19:17
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

BLOCK = Critical finding (Finding 1) must be fixed before merge. Three additional High findings compound the risk.

---

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [Critical] `__file__` in `_load_domain_manifest` breaks frozen build
- **Critic**: "`Path(__file__).parent.parent` in a PyInstaller binary resolves to `dist/`, not the repo root — `_load_domain_manifest` silently returns `None` for every domain in production."
- **Cross**: Not flagged.
- **Judgment**: Strong evidence. `core/config_paths.py:36-39` already defines the frozen-safe `BASE_DIR` pattern — this is the third new `__file__` occurrence in `core/` without the guard. The fix is one import away and directly mirrors existing practice.
- **Action Required**:
  ```python
  from core.config_paths import BASE_DIR
  path = Path(BASE_DIR) / "config" / "coverage_manifests" / f"{domain}.yaml"
  ```

---

#### 2. [ACCEPT] [High] `required_fields` returned without list-type guard — silent corruption on malformed YAML
- **Critic**: "If `required_fields` is a string, iterating it in `_identify_unmet_gaps` produces individual characters, each likely found in `all_text` — gaps go undetected. If it's an int, `TypeError` at runtime."
- **Cross**: Not flagged directly (Cross Finding 2 is about schema completeness, a different concern).
- **Judgment**: Clear code path: `data.get("required_fields")` returns whatever the YAML contains; the `isinstance(data, dict)` guard does not protect the value type. The `if not domain_checklist:` check at line 617 passes for a non-empty string.
- **Action Required**: `core/researcher.py:607-608`
  ```python
  fields = data.get("required_fields")
  return fields if isinstance(fields, list) else None
  ```

---

#### 3. [ACCEPT] [High] `sufficient` flag goes stale — gap recovery penalized as failure
- **Critic**: "`local_refs` is never updated inside the loop, so `_is_sufficient(local_refs, ...)` returns the same value every iteration — the `break` on `sufficient` can never fire after round 0."
- **Cross**: "After web refs fill all checklist gaps, `unmet=[]` causes a break, but `sufficient` remains `False`. `ResearchVerifier` at `core/research_verifier.py:93` consumes `sufficiency_gate_passed` and emits `sufficiency_gate_not_passed` at line 132, penalizing successfully recovered evidence."
- **Judgment**: Both reviewers converge on the same defect from different angles. Critic identifies that the per-round `sufficient` check is structurally dead; Cross identifies that the downstream consumer is materially harmed. Combined: gap recovery via web refs is invisible to `ResearchVerifier`, making the B1 loop feature produce incorrect audit output.
- **Action Required**: After the `if not unmet: break` path exits, set `sufficient = True` (or a separate `recovered = True` flag) so `sufficiency_gate_passed` reflects the actual coverage outcome. Also consider whether `_is_sufficient` should incorporate `web_refs` or be moved outside the loop as a pre-check.

---

#### 4. [ACCEPT] [High] Escalation self-call drops domain and scores
- **Critic**: Not flagged.
- **Cross**: "The router-gap retry at `core/researcher.py:930` calls `collect_project_evidence(..., hint_gaps=router_gaps)` without `research_plan=research_plan`. On the recursive call, `research_plan is None`, so `prev_domain` becomes `''` at line 779 and `ResearchPlan.for_mode()` rebuilds the plan without the domain/scores already computed."
- **Judgment**: This is not inside the diff but is triggered by a code path adjacent to the new `unmet_gaps` changes. Evidence cites specific line numbers and the data-flow consequence is clear — domain identity and router scores are silently discarded on retry.
- **Action Required**: Pass `research_plan=research_plan` into the recursive call at line 930; preserve `secondary_modes`/`scores` when calling `ResearchPlan.for_mode(...)` on the recursive path.

---

#### 5. [ACCEPT] [Medium] Coverage manifest schema mostly ignored — `match_keywords` and `trigger` unused
- **Critic**: Not flagged.
- **Cross**: "`_load_domain_manifest()` returns only `required_fields`, but `poker.yaml` defines `match_keywords` and `trigger`. The checker matches raw snake_case IDs (`hand_ranking`) against source text; actual source text contains configured keywords (`royal flush`, `small blind`), so real gaps are missed."
- **Judgment**: Not a crash risk but the feature delivers substantially less value than the manifest schema intends. The schema contract is established in the YAML; the implementation honors only one of three declared fields.
- **Action Required**: Load full manifest; match each `required_fields` entry against its corresponding `match_keywords` list; respect `trigger.min_research_depth`.

---

#### 6. [ACCEPT] [Medium] Raw `domain` used in path construction — unvalidated path component
- **Critic**: "`f\"{domain}.yaml\"` is appended without stripping directory components. A value like `\"../config\"` resolves to an unintended file; no error is raised if the file is valid YAML."
- **Cross**: Not flagged.
- **Judgment**: `domain` is currently set by internal router logic with a limited vocabulary, so exploitation risk is low today. As the domain vocabulary grows, a mis-classified value could silently load a wrong config. Applying `Path(domain).name` is zero-cost insurance.
- **Action Required**: `core/researcher.py:604`
  ```python
  safe = Path(domain).name
  if not safe or safe != domain:
      return None
  path = Path(BASE_DIR) / "config" / "coverage_manifests" / f"{safe}.yaml"
  ```

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `__file__` breaks frozen build | Critical | ACCEPT | Critic |
| 2 | `required_fields` list-type guard missing | High | ACCEPT | Critic |
| 3 | `sufficient` flag stale / gap recovery penalized | High | ACCEPT | Both |
| 4 | Escalation self-call drops domain + scores | High | ACCEPT | Cross |
| 5 | Manifest schema mostly ignored | Medium | ACCEPT | Cross |
| 6 | Raw `domain` in path — unvalidated component | Medium | ACCEPT | Critic |

---

### Recommendations

1. **Fix Finding 1 first** — replace `Path(__file__).parent.parent` with `from core.config_paths import BASE_DIR` across the entire new code block. This is a one-line import and a one-line path change.
2. **Fix Finding 2 alongside** — add `isinstance(fields, list)` guard in `_load_domain_manifest`; it's two lines and prevents a class of silent corruption bugs.
3. **Fix Finding 3** — after the `while` loop exits via `unmet=[]`, set `sufficient = True` if `unmet` is empty (meaning coverage was achieved via web refs). Alternatively, refactor `_is_sufficient` to accept and consider `web_refs`.
4. **Fix Finding 4** — pass `research_plan=research_plan` to the recursive escalation call at line 930 before this branch ships.
5. **Defer Findings 5 and 6** — both are Medium and advisory: Finding 5 is a feature-depth issue that can be a follow-up; Finding 6 is a defensive hygiene item with low current risk. Document them in the work-item backlog.