# Design Review: 2026-05-09-p2-e2e-command-block-activation-design

> Source: docs/2026-05-09-p2-e2e-command-block-activation-design.md
> Date: 2026-05-09 22:46
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] User edits cannot clear the block before `execute()`
   - Section: "`project_pipeline.execute()` 진입 시 block 체크 추가" and "`round-trip은 best-effort... BLOCK 또는 override 흐름`"
   - Issue: The proposed block check runs immediately after `gate.is_execution_open()` and before `sync_board_from_work_items()` currently updates the board ([core/project_pipeline.py](/Users/hoon/workTree/agent-factory/core/project_pipeline.py:1267)). Even if the user edits `implementation-tasks.md` to add `e2e_command`, `_decision.json` was generated earlier during `prepare`, and `execute()` will read the stale blocking decision. Current parser/sync also ignores `e2e_command` entirely: `parse_implementation_tasks()` documents and extracts task_id/owner/phase/deps/acceptance/artifacts only ([core/work_item_parser.py](/Users/hoon/workTree/agent-factory/core/work_item_parser.py:103), [core/work_item_parser.py](/Users/hoon/workTree/agent-factory/core/work_item_parser.py:153)); `sync_board_from_work_items()` never copies `e2e_command` into matched or new tasks ([core/work_item_parser.py](/Users/hoon/workTree/agent-factory/core/work_item_parser.py:239)).
   - Suggestion: Before checking the block decision in `execute()`, sync docs into the task board, parse and persist `e2e_command`, recompute missing warnings/summary/decision, then read `_decision.json`. Alternatively require `af warning-repair` after edits and make that explicit in the gate/report, but that is a worse UX than automatic recompute.

2. [High] The markdown backfill design does not integrate with the existing parser/source-of-truth path
   - Section: "`_backfill_e2e_from_tasks_md(tasks_content: str, task_board: dict)` ... `implementation-tasks.md`의 `e2e_command:` 라인을 추출해 task_board에 반영"
   - Issue: `work_item_generator._make_checklist()` emits `e2e_command` lines ([core/work_item_generator.py](/Users/hoon/workTree/agent-factory/core/work_item_generator.py:194)), but the existing reusable parser ignores those lines. Adding a separate best-effort parser in `work_item_generator.py` creates a second parser with different behavior from `core/work_item_parser.py`, so prepare-time LLM output and execute-time user edits will diverge.
   - Suggestion: Extend `parse_implementation_tasks()` to parse `e2e_command`, and extend `sync_board_from_work_items()` to copy it for matched and new tasks. Then have prepare-time backfill reuse that parser instead of adding a separate markdown extractor.

3. [High] `read_block_decision()` fails open on corrupt decision files
   - Section: "`except (OSError, json.JSONDecodeError): return False, None`"
   - Issue: This makes a malformed `_decision.json` equivalent to “not blocked.” That is unsafe for a policy gate. The design already makes `_decision.json` the machine-readable enforcement artifact, so corruption, partial writes, or incompatible schema should not silently permit execution.
   - Suggestion: Missing file can be fail-open only if no warning summary exists. JSON decode/schema errors should fail closed with `reason="escalation_decision_unreadable"` and point to `_decision.md`/`_decision.json`, or recompute decision from `_summary.json` during `execute()`.

4. [High] Truthy placeholders defeat the rule instead of proving an executable e2e path
   - Section: "`build | f\"pytest -k {task_id} -q\" | 통과`" and "`LLM이 `# TODO:` 형식으로 채우면 `_clean()`이 truthy → BLOCK 회피`"
   - Issue: The rule name is `e2e_command_missing`, but P2’s stated goal is to avoid empty validation commands. A fake `pytest -k <task_id>` or `# TODO:` string clears the block without any evidence that the command exists or runs. This creates a policy gate that mostly checks non-empty text, not executable validation. It also risks later runtime failures if generated `task_id` values do not correspond to pytest selectors.
   - Suggestion: Treat known placeholders and TODO markers as missing for BLOCK purposes, or add a separate `e2e_command_placeholder` warning. For build/integrate defaults, only auto-fill commands when the repo actually has pytest config/tests; otherwise leave empty and block with clear remediation.

5. [Medium] Override writes are underspecified for concurrent access
   - Section: "`_overrides.json` 에 entry append" and "`remove_override(args.workspace, args.slug, args.rule)`"
   - Issue: The design adds mutable `_overrides.json`, but does not specify use of `core.file_lock.locked_file`. Existing warning records use locked append and summary uses `_summary.json.lock` ([core/warning_registry.py](/Users/hoon/workTree/agent-factory/core/warning_registry.py:173)). Concurrent `warning-override`, `warning-summary`, and prepare can race, causing lost overrides or inconsistent decisions.
   - Suggestion: Define `_overrides.json.lock`, atomic temp-file replace, and summary lock ordering. Reuse `locked_file` and state whether override writes trigger summary recompute while holding or after releasing the override lock.

6. [Medium] Frozen build impact is listed but not fully designed
   - Section: "`af.spec hiddenimports — core.escalation_decision_report, core.warning_overrides 추가`"
   - Issue: Adding hidden imports is necessary but not sufficient. `_load_policy()` reads `config/escalation_policy.yaml` via `BASE_DIR` ([core/escalation_evaluator.py](/Users/hoon/workTree/agent-factory/core/escalation_evaluator.py:14)), and `af.spec` does include `config` as datas, but the design does not specify a frozen-build test for `af warning-override`, `warning-summary`, and pipeline execute against bundled policy.
   - Suggestion: Add an acceptance case that runs the frozen `dist/af/af.exe` or platform equivalent for `warning-summary` and `warning-override`, verifying policy load and hidden imports.

### Missing from Design

- A recomputation path after the user edits `implementation-tasks.md`.
- Parser changes in `core/work_item_parser.py` for `e2e_command`.
- Fail-closed behavior for corrupt `_decision.json`.
- Locking/atomicity rules for `_overrides.json`.
- A concrete rule for distinguishing real commands from TODO/placeholders.
- Frozen-build acceptance coverage beyond `af.spec` edits.

### Positive Observations

- The design correctly identifies the current P1 stub: `evaluate()` always returns `block=False` ([core/escalation_evaluator.py](/Users/hoon/workTree/agent-factory/core/escalation_evaluator.py:62)).
- It correctly separates approval state from policy block state; `approval_gate.md` currently only renders the decision report path, not the report itself ([core/approval_gate.py](/Users/hoon/workTree/agent-factory/core/approval_gate.py:350)).