# Code Review: work_item_generator

> Source: core/work_item_generator.py
> Date: 2026-05-08 15:39
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] Non-atomic telemetry file write can corrupt JSON on crash/interruption  
File: [`core/work_item_telemetry.py:26`](/Users/hoon/workTree/agent-factory/core/work_item_telemetry.py:26)  
Code: `tele_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")`  
Issue: Direct overwrite is not atomic. If process dies mid-write, telemetry JSON can be truncated/corrupted (checklist: non-atomic file writes).  
Suggestion: Write to temp file in same dir + `os.replace(temp, tele_path)` under the same lock.

2. [High] Cleanup hook is specified but never wired into work-item generation flow  
File: [`core/cli_session_cleanup.py:3`](/Users/hoon/workTree/agent-factory/core/cli_session_cleanup.py:3)  
Code: `generate_work_items() 진입 시 1회 호출 (idempotent).`  
File: [`core/work_item_generator.py:824`](/Users/hoon/workTree/agent-factory/core/work_item_generator.py:824)  
Code: `def generate_work_items(...):` (no `cleanup_stale_sessions(...)` call)  
Issue: Stale CLI session artifacts are never cleaned despite explicit contract; runtime data can grow unbounded and stale session state may linger.  
Suggestion: Call `cleanup_stale_sessions(workspace)` at start of `generate_work_items()` with safe exception handling/logging.

3. [Medium] Parallel-design fallback path is effectively dead/unreachable in current call flow  
File: [`core/work_item_generator.py:690`](/Users/hoon/workTree/agent-factory/core/work_item_generator.py:690)  
Code: `elif prev_plan: ... "Feature Spec is being generated in parallel"`  
File: [`core/work_item_generator.py:885`](/Users/hoon/workTree/agent-factory/core/work_item_generator.py:885)  
Code: `prev_spec=spec_content, run_id=run_id, workspace=workspace`  
Issue: Design generator contains a `prev_plan` branch intended for spec-parallel mode, but caller always provides `prev_spec`; this branch is dead and can hide incomplete parallelization logic.  
Suggestion: Either implement the actual parallel execution path that passes `prev_plan` when spec is pending, or remove this branch/comment to avoid misleading behavior.

4. [Medium] Placeholder refine attempt metric undercounts real attempts  
File: [`core/work_item_generator.py:982`](/Users/hoon/workTree/agent-factory/core/work_item_generator.py:982)  
Code: `for attempt in range(_PLACEHOLDER_REFINE_MAX): ...`  
File: [`core/work_item_generator.py:998`](/Users/hoon/workTree/agent-factory/core/work_item_generator.py:998)  
Code: `result.placeholder_refine_attempts = attempt + 1` (only when content changed)  
Issue: If refine is attempted but output is unchanged, attempts are recorded as `0`, losing diagnostic fidelity.  
Suggestion: Increment attempt counter when refine is attempted (on each loop with forbidden tokens), not only when text diff occurs.

### Comparison with Known Issues

- `docs/code_review/code-review.md` previously noted incomplete review/integration around `cli_session_cleanup` and `work_item_telemetry` in the phase-a change context.  
- Current code still shows similar incompleteness patterns: cleanup contract not wired, telemetry path added but operational robustness/usage gaps remain.

### Positive Observations

- `_generate_and_refine()` now uses explicit keyword dispatch (`prev_plan`/`prev_spec`/`prev_design`) instead of positional-last-arg assumptions, which is safer for future signature changes.  
- `DocGenerationResult` centralizes generation metadata (provider/model/errors/fallback flags), which is a good base for observability once persistence/consumption is wired.