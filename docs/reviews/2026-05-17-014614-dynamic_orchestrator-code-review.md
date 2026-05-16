# Code Review: dynamic_orchestrator

> Source: core/dynamic_orchestrator.py
> Date: 2026-05-17 01:46
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] Worker result writes are non-atomic and can leave a corrupt `result.json`
   - File: `core/agent_worker.py:93`
   - Code: `with open(args.result_file, "w", encoding="utf-8") as fh:`
   - Issue: The terminal worker writes `result.json` directly. If the process is interrupted mid-write, `DynamicOrchestrator` may see an existing but partial JSON file.
   - Suggestion: Write to a temp file in the same directory, flush/close it, then `os.replace(tmp, args.result_file)`.

2. [High] Corrupt result file can make orchestrator wait for the full 1-hour timeout
   - File: `core/dynamic_orchestrator.py:706`
   - Code: `if os.path.exists(result_file): ... except (json.JSONDecodeError, OSError): continue`
   - Issue: Once `result_file` exists but contains invalid JSON, the loop keeps retrying. The process-exit check only runs when the file does not exist, so an already-exited worker with a corrupt result file waits until `max_wait = 3600.0`.
   - Suggestion: After JSON load failure, check `proc.poll()`. If the worker has exited, return a clear `worker_result_corrupt` error instead of continuing.

3. [Critical] Crash log write is non-atomic
   - File: `core/dynamic_orchestrator.py:1233`
   - Code: `with crash_path.open("w", encoding="utf-8") as handle:`
   - Issue: This repeats the known C2/M10 pattern from `code-review.md`: direct overwrite can truncate `crash.log` during a crash or secondary failure.
   - Suggestion: Use `tempfile.NamedTemporaryFile(..., dir=crash_path.parent, delete=False)` and `os.replace()`.

4. [Medium] Timed-out worker process is killed but not reaped
   - File: `core/dynamic_orchestrator.py:716`
   - Code: `proc.kill()`
   - Issue: `Popen.kill()` without `proc.wait()` can leave a zombie process until parent exit, and cleanup errors are not surfaced.
   - Suggestion: Call `proc.kill()` then `proc.wait(timeout=...)`, with guarded cleanup/logging.

### Comparison with Known Issues

- The change partially addresses the lineage-runtime split: `get_lineage_ledger(state_workspace)` now matches `FSALoop.run_mission(..., runtime_workspace=state_workspace)`.
- It repeats known file-write risks from `docs/code_review/code-review.md`: C2/M10 non-atomic JSON/log writes.
- It leaves the known M6 terminal polling issue in place and makes it more visible because `result.json` is now routed through the runtime workspace.

### Positive Observations

- `task.json` is now written atomically in `_run_agent_in_terminal()` using `NamedTemporaryFile` plus `os.replace`.
- The runner path correctly preserves separate `workspace` and `runtime_workspace` for in-thread and terminal execution.