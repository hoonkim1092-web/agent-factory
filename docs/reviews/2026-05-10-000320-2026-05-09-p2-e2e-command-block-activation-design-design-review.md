# Design Review: 2026-05-09-p2-e2e-command-block-activation-design

> Source: docs/2026-05-09-p2-e2e-command-block-activation-design.md
> Date: 2026-05-10 00:03
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] Editing `e2e_command` cannot actually clear the BLOCK
   - Section: “사용자는 (a) 각 task의 `e2e_command` 필드를 실제 명령으로 채운 후 재실행”
   - Issue: Current design blocks in `project_pipeline.execute()` before `sync_board_from_work_items()` runs. Existing warnings are append-only JSONL, and `WarningRegistry.summarize()` only scans prior records, so a user edit to `implementation-tasks.md` will not remove the old `e2e_command_missing` decision. Also `core/work_item_parser.py:153-169` does not parse `e2e_command` at all, so even the later sync would not import the fix.
   - Evidence: [project_pipeline.py](/Users/hoon/workTree/agent-factory/core/project_pipeline.py:1267) checks approval before sync; [work_item_parser.py](/Users/hoon/workTree/agent-factory/core/work_item_parser.py:153) parses task attributes but not `e2e_command`; [warning_registry.py](/Users/hoon/workTree/agent-factory/core/warning_registry.py:220) rebuilds summary only from JSONL.
   - Suggestion: Add a pre-block reconciliation step: parse `e2e_command` from `implementation-tasks.md`, sync it into the board, recompute current missing state, and write a fresh decision from current board state. Add an acceptance test: generated TODO block → user edits all commands → rerun execute → no `escalation_block`.

2. [High] Enforcement is scoped only to `ProjectPipeline.execute()`, leaving other approval-gated paths inconsistent
   - Section: “`project_pipeline.execute()` 진입 차단 — `is_execution_open() and not block_decision.block` 보장”
   - Issue: `core/control/maintenance_pipeline.py` has its own approval gate check and only calls `gate.is_execution_open()`. If maintenance execution can proceed after this check without `ProjectPipeline.execute()`, escalation BLOCK is bypassed. `run_factory_cli.py resume` also performs a pre-execute approval check that knows nothing about block decisions, so its UX and failure messaging diverge.
   - Evidence: [maintenance_pipeline.py](/Users/hoon/workTree/agent-factory/core/control/maintenance_pipeline.py:310), [run_factory_cli.py](/Users/hoon/workTree/agent-factory/run_factory_cli.py:377).
   - Suggestion: Either centralize gate+block validation in `ApprovalGate` or add explicit `read_block_decision()` checks to every approval-gated caller, especially maintenance and resume. Add grep-based acceptance for all `is_execution_open()` call sites.

3. [High] Claimed summary/decision atomicity is false for readers
   - Section: “`_summary.json` 락 안에서 함께 실행 (atomic 보장)”
   - Issue: The design writes `_summary.json` first, then `_decision.json`. Readers in `read_block_decision()` do not acquire `_summary.json.lock`, so they can observe a new P2 `_summary.json` with no matching decision and fail-closed as `decision_missing`. That creates transient false BLOCKs during normal summarize.
   - Evidence: Current summary write is separate `os.replace` at [warning_registry.py](/Users/hoon/workTree/agent-factory/core/warning_registry.py:173); proposed reader pseudocode reads files directly without locking.
   - Suggestion: Make the reader take the same summary lock, or write a complete decision first and only publish the P2 `escalation_phase` marker after decision publication. Document the intended transient behavior if fail-closed during regeneration is acceptable.

4. [Medium] Backfill parser will miss non-`T-NNN` task IDs used by existing board tasks
   - Section: “task_id 매칭: 해당 e2e_command 라인 직전 최대 5줄에서 `task_id: T-NNN` 탐색”
   - Issue: Existing `_task_template()` / `_normalize_tasks()` generate safe IDs like `<module>_<phase>_<index>`, not necessarily `T-001`. `_make_checklist()` prints the actual task ID from the board, so fallback/generated docs can contain non-`T-NNN` IDs. The proposed regex silently skips those, leaving missing warnings even when commands exist.
   - Evidence: [project_task_board.py](/Users/hoon/workTree/agent-factory/core/project_task_board.py:497), [work_item_generator.py](/Users/hoon/workTree/agent-factory/core/work_item_generator.py:183).
   - Suggestion: Use the same `safe_id`-compatible grammar as `parse_implementation_tasks()`: match any non-empty `task_id:` value, then normalize with `safe_id()`.

5. [Medium] Multi-root workspace guidance is under-specified for override commands
   - Section: “`af warning-override --workspace . --slug ...`”
   - Issue: `PreparedProject.gate()` stores warning decisions under `runtime_workspace=self.workspace`, while work-item docs may live under a separate `doc_root`. In multi-PC or target-path workflows, `--workspace .` can write `_overrides.json` to the wrong root and fail to unblock.
   - Evidence: [project_pipeline.py](/Users/hoon/workTree/agent-factory/core/project_pipeline.py:94) passes `runtime_workspace=self.workspace`.
   - Suggestion: `_decision.md` should render the exact override command with the resolved runtime workspace path, or `warning-override` should support resolving from `approval-gate.md` / work-item path.

### Missing from Design

- A resolution model for append-only warnings: how a previously recorded `e2e_command_missing` becomes non-blocking after the current board is fixed.
- Updates to `core/work_item_parser.py` for `e2e_command` round-trip parsing.
- Coverage for all `is_execution_open()` callers, not just `ProjectPipeline.execute()`.
- Locking/read consistency contract for `_summary.json` + `_decision.json`.
- Multi-root override UX using the actual runtime workspace.

### Positive Observations

- The design correctly identifies that `ApprovalGate.initialize()` should remain a reader/rendering concern and keeps `WarningRegistry.summarize()` responsible for decision generation.
- The frozen build impact is explicitly called out with `af.spec` hiddenimports for the two new modules.