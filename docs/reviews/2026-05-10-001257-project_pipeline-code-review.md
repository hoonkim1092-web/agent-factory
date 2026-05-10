# Code Review: project_pipeline

> Source: core/project_pipeline.py
> Date: 2026-05-10 00:12
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### Findings

1. [High] User edits cannot clear an existing escalation block
   - File: `core/project_pipeline.py:1277`
   - Code: `blocked, block_decision = gate.read_block_decision()`
   - Issue: The block check runs before `sync_board_from_work_items()` at `core/project_pipeline.py:1294`. If a user follows the returned message and edits `implementation-tasks.md` to add `e2e_command`, execute still reads the old `_decision.json` before importing the edited work item state or recomputing warnings. The run can remain blocked even after the documented fix.
   - Suggestion: Before `read_block_decision()`, reconcile edited work-item docs into the board and recompute the warning summary/decision, or add a targeted pre-block refresh for `e2e_command_missing`.

2. [High] `implementation-tasks.md` parser drops `e2e_command`
   - File: `core/work_item_parser.py:153`
   - Code: `if key == "task_id" and val:`
   - Issue: The parser handles `task_id`, owner, phase, dependencies, acceptance, artifacts, and target files, but not `e2e_command`. Even if the block check is moved after sync, user-provided `e2e_command` values are not copied into `task_board`, so the missing-command warning can persist.
   - Suggestion: Parse `e2e_command` in `parse_implementation_tasks()` and preserve it in `sync_board_from_work_items()` when matching tasks.

3. [High] Other approval-gated execution path bypasses escalation block
   - File: `core/control/maintenance_pipeline.py:313`
   - Code: `if not gate.is_execution_open():`
   - Issue: `ProjectPipeline.execute()` now enforces `read_block_decision()`, but `MaintenancePipeline` has its own approval gate check and never reads block decisions. Any maintenance execution guarded only by this path can proceed despite an active `_decision.json` block.
   - Suggestion: Centralize approval + escalation policy validation in `ApprovalGate`, or add `read_block_decision()` checks to every `is_execution_open()` caller.

4. [Medium] Corrupt summary silently disables the block
   - File: `core/approval_gate.py:194`
   - Code: `except (OSError, json.JSONDecodeError): return False, None`
   - Issue: The newly added execute check depends on `read_block_decision()`, but a malformed or unreadable `_summary.json` fail-opens. That creates a bypass for escalation enforcement exactly when the warning state is inconsistent.
   - Suggestion: For an existing `_summary.json` parse/read error, fail closed or rebuild the summary before allowing execution.

### Comparison with Known Issues

- This repeats the known review pattern in `docs/reviews/2026-05-10-000320-2026-05-09-p2-e2e-command-block-activation-design-design-review.md`: block enforcement occurs before work-item reconciliation, and other `is_execution_open()` callers are not covered.
- It also matches the known “silent fallback” concern from `docs/code_review/code-review.md`: corrupted warning state can be hidden by returning `(False, None)`.

### Positive Observations

- The new `ProjectPipeline.execute()` return shape is explicit: `ok=False`, `reason="escalation_block"`, `blocking_rules`, and a decision report path.
- `PreparedProject.gate()` correctly passes `runtime_workspace=self.workspace`, so split `doc_root` mode is considered for the warning registry lookup.