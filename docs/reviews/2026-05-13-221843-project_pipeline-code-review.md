# Code Review: project_pipeline

> Source: core/project_pipeline.py
> Date: 2026-05-13 22:18
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

The diff's stated purpose — wiring `blast_radius` and `work_kind` into the domain gate — is not achieved. Both reviewers independently confirmed the domain gate remains permanently unreachable for the same root cause as before. Two additional pre-existing regressions were discovered during context exploration.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [High] `blast_radius` and `work_kind` sourced from wrong dict — domain gate still dead

- **Critic**: "`project_brief` never contains `blast_radius`. The only producer is `ControlPlaneIntake().normalize()` which is never called from this pipeline. Gate file always stores `blast_radius: \"\"`. Condition at `approval_gate.py:233` remains permanently unreachable."
- **Cross**: "`generate_work_items()` receives `work_kind`/`blast_radius` from `project_brief`, but `ControlPlaneIntake.normalize()` is the code that computes `NormalizedRequest.work_kind` and `change_impact['blast_radius']` at `core/control/intake.py:69`. If the values only live in `NormalizedRequest`, the domain-review approval guard is not activated."
- **Judgment**: Both reviewers independently reached the same conclusion with the same code path. `project_brief` is produced by `research_project_brief()` (an LLM call) and is augmented only with `requested_role`, `route`, and `generated_at` (`project_pipeline.py:818-820`). Neither `blast_radius` nor `work_kind` is ever written there. The diff moves a `None` pointer — not a working value.
- **Action Required**: Call `ControlPlaneIntake().normalize()` in `prepare_brief()` or `prepare_documents()`, store the result on `PreparedBrief`/`PreparedProject`, and pass `prepared.normalized.change_impact.get("blast_radius", "")` and `prepared.normalized.work_kind` to `generate_work_items()`. Deduplicate against the existing `_recall_from_memory` call at `project_pipeline.py:709-710`.

---

#### 2. [ACCEPT] [High] `MaintenancePipeline._full_prepare()` calls `prepare()` without required `workspace` arg

- **Critic**: not flagged
- **Cross**: "`_full_prepare()` calls `self._pipeline.prepare(task_input)` at `maintenance_pipeline.py:164`, but `ProjectPipeline.prepare()` requires `workspace` at `project_pipeline.py:1206`. Exception is caught and silently converted to an error dict at `maintenance_pipeline.py:189`."
- **Judgment**: Pre-existing issue surfaced during context exploration; not introduced by this diff. However, the evidence is concrete — a required positional/keyword arg is missing, and the broad `except` makes it invisible in tests. Cross reviewer's evidence is unambiguous.
- **Action Required**: Fix call to `self._pipeline.prepare(task_input, workspace=self._workspace, route=getattr(normalized, "route", {}) or {})`. Add a regression test for this path.

---

#### 3. [ACCEPT] [High] `PDCA /plan` constructs `ProjectPipeline` with incompatible signature

- **Critic**: not flagged
- **Cross**: "`pdca_commands.py:242` constructs `ProjectPipeline(workspace=..., model_router=...)`, but the actual constructor is `ProjectPipeline(mr, agent_mgr, research_agent, procurer, ...)` at `project_pipeline.py:123`. All exceptions are caught at `pdca_commands.py:256`, so `/plan` silently falls back to direct LLM planning."
- **Judgment**: Pre-existing issue surfaced during review. Constructor mismatch is verified against the diff context and the cited line numbers. The broad swallowing means this misconfiguration has never failed visibly.
- **Action Required**: Either inject the factory-configured pipeline or construct with the full required dependency list. Remove or narrow the bare `except` so constructor errors are observable.

---

#### 4. [ACCEPT] [Medium] `str(x or "")` double-conversion silently swallows falsy non-empty values

- **Critic**: "The `or \"\"` short-circuits on any falsy value including `0`, `False`, `[]`. Combined with outer `str()`, creates a misleading impression that non-string types are handled. Use `(project_brief.get("work_kind") or "")` without `str()`, or `str(project_brief.get("work_kind", ""))`."
- **Cross**: not flagged
- **Judgment**: Accepted at Medium because the pattern is in the diff being reviewed. The immediate risk is low since the source is always `None` today (Finding 1), but the pattern should not propagate as a template. One reviewer, evidence is in the diff.
- **Action Required**: Change to `project_brief.get("work_kind") or ""` (drop redundant `str()`). Same for `blast_radius`.

---

### Summary Table

| # | Title | Severity | Verdict | Source | Pre-existing? |
|---|-------|----------|---------|--------|--------------|
| 1 | `blast_radius`/`work_kind` wrong source, gate dead | High | ACCEPT | Both | No (this diff) |
| 2 | `MaintenancePipeline.prepare()` missing workspace | High | ACCEPT | Cross | Yes |
| 3 | PDCA `/plan` incompatible constructor | High | ACCEPT | Cross | Yes |
| 4 | `str(x or "")` double-conversion | Medium | ACCEPT | Critic | No (this diff) |

---

### Recommendations

- **Fix Finding 1 first** — the entire point of this PR. Wire `ControlPlaneIntake().normalize()` into `prepare_brief()`/`PreparedBrief`, then pass fields forward. This is the only change that makes the domain gate reachable.
- **File separate tickets for F2 and F3** — they are pre-existing and out of scope for this diff, but the silent-exception pattern in both makes them high priority. Don't fix them here; don't ignore them.
- **Apply F4 fix in the same commit as F1** — it's a one-line change per call site and prevents the `str(x or "")` pattern from being copied elsewhere.
- **After fixing F1**, verify `approval_gate.py:233` is reachable by adding an integration test that passes `blast_radius="system_wide"` through the full `prepare → generate_work_items → gate.initialize()` path.