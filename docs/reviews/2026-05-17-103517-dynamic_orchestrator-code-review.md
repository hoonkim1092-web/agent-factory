# Code Review: dynamic_orchestrator

> Source: core/dynamic_orchestrator.py
> Date: 2026-05-17 10:35
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### Findings

1. [High] Timed-out worker may keep running after reported failure
   - File: `core/dynamic_orchestrator.py:720`
   - Code: `proc.kill()`
   - Issue: The code kills only the direct worker process, then swallows any wait failure. In terminal mode this worker can have spawned provider CLI child processes that may continue mutating the workspace after the orchestrator records `worker_timeout`.
   - Suggestion: Terminate the process group/tree, especially on Windows with `CREATE_NEW_CONSOLE`; after `wait()`, verify `proc.poll() is not None` and report/handle any still-running process.

2. [High] New corrupt-result reason is misclassified as implementation failure
   - File: `core/dynamic_orchestrator.py:714`
   - Code: `return {"ok": False, "reason": "worker_result_corrupt"}`
   - Issue: `core/failure_classifier.py` knows `worker_timeout` and `worker_exited_code`, but not `worker_result_corrupt`. `_execute_agent_task()` will treat this IPC/result-file corruption as an implementation failure, potentially invoking evaluator/FSA retry logic for an infrastructure failure.
   - Suggestion: Add `worker_result_corrupt` to `_INFRA_PATTERNS`, or return a reason already covered by the classifier.

3. [Medium] Cleanup path silently hides process-wait failures
   - File: `core/dynamic_orchestrator.py:722`
   - Code: `proc.wait(timeout=5)`
   - Issue: The following broad `except Exception: pass` hides `TimeoutExpired`, OS errors, and interrupted waits. This repeats the known “silent fallback” pattern from `code-review.md`, making timeout cleanup failures invisible.
   - Suggestion: Catch `subprocess.TimeoutExpired` explicitly, log the pid/returncode, and record a distinct reason such as `worker_timeout_cleanup_failed`.

4. [Medium] Hardcoded cleanup timeout has no named policy
   - File: `core/dynamic_orchestrator.py:722`
   - Code: `proc.wait(timeout=5)`
   - Issue: The new timeout is a magic number in a critical cleanup path. AF already exposes orchestration timing via env/config patterns, but this value cannot be tuned for slow Windows process teardown or provider CLI shutdown.
   - Suggestion: Introduce a named constant or env-backed setting, e.g. `WORKER_KILL_WAIT_SECONDS`.

### Comparison with Known Issues
- The crash log change addresses the known non-atomic write pattern by using `tempfile.NamedTemporaryFile(...)` plus `os.replace(...)`.
- The timeout cleanup introduces a similar known issue to `code-review.md`’s silent fallback pattern: cleanup exceptions are swallowed without context.
- The worker-result corruption path creates an AF-specific classification gap in the runtime engine.

### Positive Observations
- `crash.log` is no longer written directly to the final path, reducing torn-write risk.
- The result polling now distinguishes a corrupt finished result from an in-progress atomic write, avoiding a full 3600-second wait when the worker already exited.