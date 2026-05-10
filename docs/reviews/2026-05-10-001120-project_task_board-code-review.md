# Code Review: project_task_board

> Source: core/project_task_board.py
> Date: 2026-05-10 00:11
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### Findings

1. [High] `e2e_command` added by templates is discarded before reaching the board
   - File: `core/project_task_board.py:603`
   - Code:
     ```python
     task = {
         "task_id": _task_id,
         ...
         "artifacts": _clean_list(raw_task.get("artifacts")),
         "status": _clean_text(raw_task.get("status") or "pending") or "pending",
         "lineage_id": _clean_text(raw_task.get("lineage_id")) or _task_id,
         "notes": [],
         "updated_at": now_iso(),
     }
     ```
   - Issue: `_normalize_tasks()` preserves `raw["e2e_command"]`, and this diff adds it to `_task_template()`, but `build_project_board()` never copies it into `board["tasks"]`. Normal generated build/verify tasks still arrive at `work_item_generator._make_checklist()` with no `e2e_command`, so the P2 `e2e_command_missing` warning/block path still fires.
   - Suggestion: Add `"e2e_command": _clean_text(raw_task.get("e2e_command") or "")` to the board task dict, then add a regression test from `enrich_role_plan()` → `build_project_board()` asserting generated build/verify tasks retain the field.

2. [High] New placeholders are intentionally classified as missing and can block execution
   - File: `core/project_task_board.py:369`
   - Code:
     ```python
     "e2e_command": f"# TODO: e2e command for {slice_task_id} (build)",
     ```
   - Issue: `core/work_item_generator.py:952-960` explicitly treats empty values and `# TODO` / `#TODO` values as missing:
     ```python
     return v.startswith("# TODO") or v.startswith("#TODO")
     ```
     So if finding #1 is fixed, these new defaults still produce `e2e_command_missing` for build/verify phases, which P2 treats as blockable. This does not create a usable validation command; it creates a guaranteed missing marker.
   - Suggestion: Either leave `e2e_command` empty and let the missing-warning path report it, or generate real phase-aware commands only when the repo/tooling supports them. If placeholders are retained, ensure the gate message treats them as unresolved, not as a fix.

3. [Medium] Placeholder task IDs do not match the actual board task IDs
   - File: `core/project_task_board.py:360`
   - Code:
     ```python
     slice_task_id = f"T-{len(tasks):03d}"
     ```
   - Issue: Final IDs are assigned later in `_normalize_tasks()` as:
     ```python
     task_id = safe_id(raw.get("id") or f"{module['id']}_{phase}_{index}")
     ```
     at `core/project_task_board.py:487`. The placeholder says `T-001`, but the actual board task is usually something like `<module_id>_build_2`. This makes generated instructions and any repair/backfill workflow misleading, especially because the existing backfill code only recognizes `T-\d+` IDs.
   - Suggestion: Do not embed a guessed ID in `_task_template()`. Fill `e2e_command` after `_normalize_tasks()` has computed the real `task_id`, or use a generic placeholder without an ID.

4. [Medium] Dynamically injected review tasks get missing placeholders but bypass the warning scan
   - File: `core/project_task_board.py:1074`
   - Code:
     ```python
     "e2e_command": f"# TODO: e2e command for {cr_task_id} (code_review)",
     ```
   - Issue: `inject_review_tasks()` runs during orchestration after prepare-time `generate_work_items()` has already recorded/summarized `e2e_command_missing`. These new `code_review` / `cross_validate` tasks contain `# TODO` values that are missing by policy, but this function does not record a warning, summarize, or force a gate recompute. That creates a policy gap for dynamically added review work.
   - Suggestion: On injection, either record and summarize `e2e_command_missing` for the injected task phases, or require the dispatcher to run a pre-dispatch e2e validation check against current board state.

### Comparison with Known Issues

- This change does not address an issue listed in `docs/code_review/code-review.md`; that file only identifies `project_task_board.py` as part of the pipeline/board subsystem.
- It repeats the known e2e-gate risk documented elsewhere in the repo: placeholder `# TODO` commands are not valid e2e commands, and injected review tasks can bypass the warning scan.

### Positive Observations

- The new review-task fields use `os.path`-independent strings only, so no new Windows/Unix path handling issue is introduced.
- Review task injection still occurs inside the existing `locked_file()` transaction, so this diff does not weaken the board write concurrency model.