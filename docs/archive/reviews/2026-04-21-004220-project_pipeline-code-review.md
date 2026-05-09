# Code Review: project_pipeline

> Source: core/project_pipeline.py
> Date: 2026-04-21 00:42
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

High findings exist (one directly introduced by this diff). No Criticals from the diff itself; two pre-existing High-severity regressions flagged by cross review are surfaced for tracking.

---

### Aggregated Findings (7 total)

#### 1. [ACCEPT] [High] `list()` on string deliverable yields character-by-character patterns
- **Critic**: "If `deliverables` is a plain string, `list(...)` produces individual characters, polluting the ledger with 1-char keys."
- **Cross**: not flagged
- **Judgment**: Directly introduced by this diff. YAML templates regularly produce `deliverables` as a bare string. `list("API endpoint handler")` → `['A','P','I',' ',...]`. The `_seen` dedup doesn't prevent this because the characters are individually distinct. High confidence bug.
- **Action Required**: `_deliverables = _mod.get("deliverables") or []; if isinstance(_deliverables, str): _deliverables = [_deliverables]`, then iterate over `_deliverables`.

#### 2. [ACCEPT] [Medium] Batch exception silently discards all entries, breaking per-module isolation
- **Critic**: "A single exception in `record_role_batch` discards all N entries; the old per-module try/except preserved partial writes."
- **Cross**: not flagged individually, but finding #2 (PDCA silent swallowing) is a parallel pattern
- **Judgment**: The comment explicitly claims per-module isolation but the implementation no longer provides it. The batch call is atomic — one failure drops everything. Evidence is in the diff: the per-module try/except was replaced with a single outer try/except.
- **Action Required**: On exception from `record_role_batch`, fall back to individual `record_role_success/failure` calls with per-entry try/except to preserve the stated isolation guarantee.

#### 3. [ACCEPT] [Medium] `_seen` resets per module — cross-module duplicate patterns enter batch with conflicting `owner_role`
- **Critic**: "`_seen` is scoped inside `for _mod in ...`, so two modules sharing a deliverable name both insert the same pattern key with different owner roles."
- **Cross**: not flagged
- **Judgment**: Directly visible in the diff: `_seen: set[str] = set()` is inside the module loop. Whether `record_role_batch` resolves conflicts deterministically is unknown from this diff, making silent last-write-wins behavior likely.
- **Action Required**: Hoist `_seen` above the module loop, OR document and verify that `record_role_batch` handles conflicting role assignments for the same key deterministically.

#### 4. [ACCEPT] [Low] Batch failure log loses all diagnostic context
- **Critic**: "Old warning included the failing `_pattern`; new message logs nothing about batch contents."
- **Cross**: not flagged
- **Judgment**: Straightforward regression in observability. Prior code logged `[%s]` with the pattern name; new code logs only the exception.
- **Action Required**: `logger.warning("strategy ledger 배치 기록 실패 [%d entries, project=%s]: %s", len(_batch), _project_id, _exc)`

#### 5. [ACCEPT] [High] Control-plane wrappers incompatible with 2-phase `prepare()`/`execute()` API (pre-existing)
- **Critic**: not flagged
- **Cross**: "`maintenance_pipeline.py:163-186` coerces non-dict return to empty placeholder; `supervisor.py:95-100` passes `str` where `PreparedProject` is expected."
- **Judgment**: Not introduced by this diff, but this diff's broader context (the 2-phase refactor) created the mismatch. Strong evidence: cross reviewer traced both call sites with line numbers. Runtime crashes on both maintenance and supervisor paths.
- **Action Required**: Update `MaintenancePipeline` and `RuntimeSupervisor` to use `prepare(task_input=..., workspace=...)` → `PreparedProject` → `execute(prepared=...)`.

#### 6. [ACCEPT] [High] PDCA `/plan` silently falls back to raw LLM due to stale constructor call (pre-existing)
- **Critic**: not flagged
- **Cross**: "`pdca_commands.py:242` calls `ProjectPipeline(workspace=..., model_router=...)` but current constructor requires `mr`, `agent_mgr`, `research_agent`, `procurer`; broad except swallows the TypeError."
- **Judgment**: Pre-existing regression. Strong evidence: cross reviewer identified exact constructor signature mismatch and the fallback path. The broad except makes this invisible in logs.
- **Action Required**: Inject shared `AgentFactory.project_pipeline` into PDCA or fix the constructor call; narrow the exception handler so contract breaks are visible.

#### 7. [ACCEPT] [Medium] Structural gate `"work_item"` rubric is missing — gate is a no-op (pre-existing)
- **Critic**: not flagged
- **Cross**: "`RubricCompiler.evaluate()` returns `pass_with_warnings` when no rubric exists; only `architecture_plan.yaml` and `research_report.yaml` are shipped; `prepare()` ignores the missing-rubric warning."
- **Judgment**: Pre-existing gap. The new `run_structural_gate(..., "work_item")` call in `prepare()` provides no actual validation until the rubric is authored.
- **Action Required**: Add a `rubrics/work_item.yaml` rubric, or treat "missing rubric" as a gate error rather than a silent pass.

---

### Summary Table

| # | Title | Severity | Verdict | Source | In Diff? |
|---|-------|----------|---------|--------|----------|
| 1 | `list()` on string deliverable | High | ACCEPT | Critic | Yes |
| 2 | Batch exception drops all entries | Medium | ACCEPT | Critic | Yes |
| 3 | `_seen` per-module cross-module dupes | Medium | ACCEPT | Critic | Yes |
| 4 | Batch failure log missing context | Low | ACCEPT | Critic | Yes |
| 5 | Control-plane / 2-phase API mismatch | High | ACCEPT | Cross | Pre-existing |
| 6 | PDCA `/plan` silent constructor failure | High | ACCEPT | Cross | Pre-existing |
| 7 | Structural gate no-op (missing rubric) | Medium | ACCEPT | Cross | Pre-existing |

---

### Recommendations

- **Must fix before merge (#1)**: Guard `deliverables` type — `if isinstance(_deliverables, str): _deliverables = [_deliverables]`. This is a direct data corruption bug introduced by this diff.
- **Should fix before merge (#2)**: Add a fallback loop so a batch failure degrades to per-entry writes, restoring the isolation the comment promises.
- **Should fix before merge (#3)**: Hoist `_seen` above the module loop to prevent conflicting role assignments for shared deliverable names.
- **Fix in follow-up (#4)**: Restore diagnostic info to the warning log.
- **Track separately (#5, #6)**: Control-plane API mismatch and PDCA silent fallback are pre-existing regressions from the 2-phase refactor — file as separate work items and fix before the next integration test run.
- **Track separately (#7)**: Author `rubrics/work_item.yaml` or fail-fast on missing rubric; the gate as written validates nothing.