# Code Review: agent_worker

> Source: core/agent_worker.py
> Date: 2026-05-17 10:33
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] Task-load error path still writes `result.json` non-atomically
   - File: `core/agent_worker.py:49`
   - Code: `with open(args.result_file, "w", encoding="utf-8") as fh:`
   - Issue: The normal result path was fixed with `tempfile + os.replace`, but the early `task_json_load_error` path still uses direct truncate-and-write. A crash here can leave corrupt `result.json`, repeating the known C2 pattern.
   - Suggestion: Extract a shared `_write_result_atomic(result_path, payload)` helper and use it for both success/failure paths.

2. [High] Result-write failure is silently swallowed during task-load failure
   - File: `core/agent_worker.py:52`
   - Code: `except Exception: pass`
   - Issue: If the worker cannot write the error result, it hides the real I/O failure. The caller then only sees a missing result file and `worker_exited_code_1`, losing the actual cause.
   - Suggestion: Catch `Exception as write_exc`, log the result path and exception, and exit with a distinct reason where possible.

3. [High] Failed final result publish exits as if the worker completed normally
   - File: `core/agent_worker.py:104`
   - Code: `except Exception as exc: print(f"[Worker:{role}] result.json 쓰기 실패: {exc}")`
   - Issue: After a result-write failure, `main()` continues and exits with status 0. `dynamic_orchestrator.py` will report `worker_exited_code_0` with no result file, which is misleading and makes the real failure hard to diagnose.
   - Suggestion: Clean up any temp file, print/log context, then `sys.exit(1)` or return a dedicated fatal worker-publish error.

4. [Medium] Timeout cleanup still hides unreaped process failures
   - File: `core/dynamic_orchestrator.py:721`
   - Code: `except Exception: pass`
   - Issue: The new `proc.wait(timeout=5)` is good, but swallowing `TimeoutExpired` means a process that survives `kill()` is silently ignored. This repeats the silent cleanup pattern from the checklist.
   - Suggestion: Catch `subprocess.TimeoutExpired` separately, log/return `worker_timeout_kill_failed`, and only suppress narrow cleanup errors with context.

### Comparison with Known Issues

- This change partially addresses the known `agent_worker.py` non-atomic `result.json` write from `docs/reviews/2026-05-17-014614-dynamic_orchestrator-code-review.md`.
- It still repeats the same C2 pattern in the task-load error path.
- It also repeats the known “silent fallback” pattern through `except Exception: pass` in worker error reporting and process cleanup.

### Positive Observations

- The main worker result path now uses a same-directory temp file plus `os.replace`, which is the right atomic-write shape.
- The caller now fails fast on corrupt result JSON after the worker exits, avoiding the previous one-hour wait.