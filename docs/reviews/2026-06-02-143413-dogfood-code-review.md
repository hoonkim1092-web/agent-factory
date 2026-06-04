# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-06-02 14:34
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This touches dogfood execution, shell/subprocess behavior, merge/audit state, and runtime persistence.

### Findings

1. [Critical] Raw plan commands are executed through shell-backed runners
   - File: `core/dogfood.py:351`
   - Code: `ps_cmd = (f"try {{ & {{ {cmd} }} }} catch {{ exit 1 }}; "`
   - Issue: `cmd` flows from `core/planner.py:533` `verification_requirements=verify_cmds` into `core/dogfood.py:1629` `_command_runner(cmd, cwd)`. On Windows it is interpolated into a PowerShell command string; on Unix it runs with `shell=True` at `core/dogfood.py:363`. Premortem/planner commands include repo-derived paths and generated strings, and POSIX `shlex.quote()` is not PowerShell escaping.
   - Suggestion: Replace string commands with argv lists or a constrained command schema. For Windows, avoid `-Command` string interpolation; for Unix, use `shell=False`. Reject or require approval for commands outside a fixed allowlist.

2. [High] Phase trace write failures are silently dropped
   - File: `core/dogfood.py:2087`
   - Code: `except Exception:\n        pass`
   - Issue: `_append_phase_trace()` is the audit trail for phase inputs, outputs, exceptions, blocked reasons, and LLM usage. Any permission, encoding, disk, or path failure erases that evidence without changing run state or surfacing diagnostics. This repeats the known silent-fallback pattern from `docs/code_review/code-review.md`.
   - Suggestion: At minimum print/log the exception with run_id and phase. In `strict_contract` or merge-capable runs, consider failing closed or recording a state-level `last_failure` when trace persistence fails.

3. [Medium] `save_state()` uses a fixed temp path and weaker persistence than the artifact writer
   - File: `core/dogfood.py:536`
   - Code: `tmp = path.with_suffix(".tmp")`
   - Issue: The state writer does not use a unique temp file and does not fsync before replace, while `atomic_write_json()` below has the stronger pattern. A concurrent/manual dogfood operation for the same run can contend on the same `.tmp`, and a crash can lose the latest state update.
   - Suggestion: Route `save_state()` through `atomic_write_json()` or use `tempfile.NamedTemporaryFile(..., dir=path.parent, delete=False)` plus fsync and `os.replace`.

4. [Medium] Verification failures discard command output
   - File: `core/dogfood.py:1629`
   - Code: `ok, _ = _command_runner(cmd, cwd)`
   - Issue: `_run_verify_phase()` records only the failed command string, not stdout/stderr. When dogfood blocks on verification, operators lose the concrete failure reason even though `_default_command_runner()` returned it.
   - Suggestion: Capture output and include a capped snippet in `failures`, or add a structured `failure_outputs` field.

### Comparison with Known Issues

- The shell-backed command path repeats the documented C4-adjacent risk: generated plan/premortem command strings reach subprocess execution.
- The phase-trace handler repeats the known H3 silent fallback pattern.
- The fixed temp state write is related to the documented non-atomic/fragile persistence patterns, although artifacts now mostly use `atomic_write_json()`.

### Positive Observations

- `merge_dogfood_branch()` now routes default policy construction through `build_merge_policy()`, preserving denied paths and plan-derived allowed paths.
- `finalize_dogfood_result()` correctly separates untracked files from CRLF-only tracked noise before staging.