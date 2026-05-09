# Design Review: 2026-05-09-warning-registry-and-gate-escalation-design

> Source: docs/2026-05-09-warning-registry-and-gate-escalation-design.md
> Date: 2026-05-09 09:47
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] `e2e_command_missing` hardcodes phase and makes phase-aware escalation invalid
   - Section: `WarningRegistry.record(rule_id="e2e_command_missing", count=len(missing_e2e), affected_phase="build", affected_ids=missing_e2e)`
   - Issue: Current code at `core/work_item_generator.py:1048-1059` only collects missing task IDs and does not preserve each task’s actual `phase`. Meanwhile `core/project_task_board.py:476-493` stores per-task `phase`. Hardcoding every missing command as `build` means P2 will block scope/design/planning omissions as build failures, and cannot distinguish code_review/cross_validate/verify tasks.
   - Suggestion: Record per-phase buckets, e.g. one `WarningRecord` per affected phase with `affected_ids` for that phase, or add `affected_items=[{"task_id": ..., "phase": ...}]` and derive `affected_phase` during evaluation.

2. [High] Phase enum conflicts with real board phases and with the rollout summary
   - Section: `affected_phase: str # "scope" | "design" | "build" | "test" | "verify" | "integration"`
   - Issue: The real board phase order is `{"scope", "build", "integrate", "code_review", "cross_validate", "verify"}` in `core/project_task_board.py:17`. The design uses `test` and `integration`, while §0 says P2 blocks `build/verify/code_review/cross_validate`. This will either miss real phases or create policy entries that never match.
   - Suggestion: Align the schema and `config/escalation_policy.yaml` to current board phases: `scope`, `build`, `integrate`, `code_review`, `cross_validate`, `verify`. If `test`/`integration` are new phases, the design must include the board migration and parser compatibility.

3. [High] Owner drift migration assumes mismatch details that the helper does not return
   - Section: `detect_owner_drift ... bool 반환만 ... 호출처 ... count=len(mismatched), affected_ids=[module_id]`
   - Issue: `core/project_task_board.py:227-248` returns only `bool` and exits on the first mismatch. `core/project_pipeline.py:1401-1406` only knows the module ID and cannot compute `len(mismatched)` or affected task IDs from the helper result.
   - Suggestion: Either change `detect_owner_drift()` to return a structured list while preserving a bool wrapper, or add a new helper such as `collect_owner_drift(module, board, task_map) -> list[dict]` and use that for registry records.

4. [High] Runtime storage path is repo-relative, not workspace-scoped, breaking multi-PC/frozen expectations
   - Section: `runtime/warnings/...`
   - Issue: Current runtime convention for persistent per-workspace runtime state is `<workspace>/.af_runtime/...`, exposed via `core/continuity/runtime_paths.py` and used by control-plane files. `core/config_paths.py:34-39` also changes `BASE_DIR` under PyInstaller frozen builds. A repo-relative `runtime/warnings` risks mixing projects, depending on CWD, and writing beside `dist/af/af.exe` in frozen mode.
   - Suggestion: Store project records under `workspace_runtime_dir(workspace) / "warnings"`. If a global aggregate is still required, define an explicit `BASE_DIR`/user-cache location and document frozen write permissions.

5. [Medium] Lock module path is still wrong
   - Section: `jsonl append는 core/file_io.locked_file 사용`
   - Issue: `locked_file` is defined in `core/file_lock.py:37-92`, not `core/file_io.py`. `core/file_io.py` only contains YAML/text helpers.
   - Suggestion: Correct the design to `from core.file_lock import locked_file` and ensure tests cover import in source and frozen builds.

6. [Medium] New frozen-build modules are not listed for `af.spec`
   - Section: `core/warning_registry.py`, `core/escalation_evaluator.py` 신규
   - Issue: `af.spec` currently has explicit hiddenimports for existing modules such as `core.approval_gate`, `core.research_verifier`, `core.file_lock`, `core.project_task_board`, `core.work_item_generator`, and `core.plan_verifier`, but not the two new modules. The design checklist asks “Does this require af.spec hiddenimports update?” but the P1 scope omits it.
   - Suggestion: Add `core.warning_registry` and `core.escalation_evaluator` to `af.spec`, or explain why they are guaranteed to be statically imported and collected.

### Missing from Design

- Exact workspace/path resolution API for warning storage, especially source vs frozen build behavior.
- A concrete schema for multi-phase records or task-level phase payloads.
- How `_summary.json` is rebuilt if jsonl append succeeds but summary update fails.
- How `false_positive_override` is written safely and who owns that mutation path.
- Tests for phase enum compatibility with `project_task_board.py` phases.

### Positive Observations

- The design correctly preserves existing user-visible warning paths: logger warnings and `evidence["_warnings"]` remain intact.
- Linking `_decision.md` from `approval-gate.md` avoids changing the gate’s five-section parser contract in `core/approval_gate.py`.