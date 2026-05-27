# Design Review: 2026-05-25-dogfood-isolation-auto-merge-design

> Source: docs/2026-05-25-dogfood-isolation-auto-merge-design.md
> Date: 2026-05-25 01:15
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] `shell=False` policy is not implementable with the current plan schema
   - Section: "`shell=False` is the mandatory execution policy for all plan commands after the Architect returns" and "CommandSpec schema ... is out of scope"
   - Issue: Current `core/planner.py:34` stores `commands: list[str]`, and `core/dogfood.py:169-181` defines `_command_runner(cmd: str, cwd: str)` using `subprocess.run(cmd, shell=True)`. `core/dogfood.py:448` and `core/dogfood.py:474` pass raw plan command strings directly. Without a structured argv schema, switching to `shell=False` is not safe or portable, especially on Windows where quoted PowerShell/Python commands cannot be reliably split from strings.
   - Suggestion: Bring `CommandSpec` into this design, or make executable plan commands non-executable until a structured schema exists. Required shape should be something like `{argv: list[str], cwd_policy, timeout, env}` and all generated commands must validate before `IMPLEMENT`.

2. [High] `af dogfood` CLI ownership is unresolved for the actual entrypoint
   - Section: "`af dogfood run \"<task>\"`", "`af dogfood merge <run_id>`", "`af dogfood cleanup <run_id>`"
   - Issue: The live dogfood parser is in `agent_launcher.py:903-932`, and dispatch is in `agent_launcher.py:968-1027`. But the main `af` stage-1 dispatcher in `run_factory_cli.py` has `_STAGE1_DISPATCH` entries for `interview`, `resume`, nightly commands, skills, etc., and no `dogfood` entry. The design says `af dogfood ...` but does not specify whether implementation belongs in `agent_launcher.py`, `run_factory_cli.py`, or both. This is a frozen-build risk because `af.exe dogfood --help` may not route to the parser the design assumes.
   - Suggestion: Add a CLI ownership section. If `af` means `run_factory_cli.py`, add a `dogfood` stage-1 dispatch target there and tests for source and frozen paths. If `agent_launcher.py` is authoritative, document how `af.exe` reaches it.

3. [High] Merge dry-run can pollute the source workspace on crash
   - Section: "`git -C <source_workspace> merge --no-commit --no-ff dogfood/<run_id>`" followed by "`git -C <source_workspace> reset --merge`"
   - Issue: The conflict check intentionally mutates the source worktree/index before cleanup. If the process dies between those commands, the maintainer’s source workspace can be left in an in-progress merge or with index/worktree changes. The crash recovery in §9 only checks whether `dogfood_commit` is already an ancestor of `HEAD`; it does not detect or recover an interrupted dry-run merge.
   - Suggestion: Run conflict checks in a temporary worktree/throwaway clone, or add startup recovery that detects `MERGE_HEAD`, staged changes, and source `HEAD == base_ref` before performing `git reset --merge`.

4. [High] Merge target branch validation is underspecified
   - Section: "`Merge into source_branch if allowed.`"
   - Issue: The design records `source_branch`, but the merge commands use only `git -C <source_workspace> merge ...`. They do not explicitly verify that `source_workspace` is currently on `state.source_branch` immediately before the merge. If a maintainer changes branches after the dogfood run starts, the policy may merge the dogfood branch into the wrong checked-out branch.
   - Suggestion: Before policy checks and before actual merge, require `git branch --show-current == state.source_branch` and `git rev-parse HEAD == state.base_ref` unless the future drift policy is active. Do not auto-checkout silently.

5. [High] Active run registry lacks safe concurrent write semantics
   - Section: "`%USERPROFILE%\\.af-dogfood\\registry.json`" and "Multiple runs against the same source workspace: allowed"
   - Issue: Multiple dogfood runs can register at the same time, but the design does not require file locking or atomic read-modify-write for `registry.json`. The project already has `core/file_lock.py:38` `locked_file()`, and prior review context flags non-atomic JSON writes as a known failure pattern. Existing dogfood state also writes fixed `.tmp` paths in `core/dogfood.py:192-197`, while phase artifacts use direct `Path.write_text()` at `core/dogfood.py:665-667`.
   - Suggestion: Require `locked_file()` around registry and per-run state writes, use unique temp files plus `os.replace`, and define corrupt registry recovery behavior.

6. [Medium] Triad pass gate is weakened by treating skipped/stub Triad as PASS
   - Section: "`require_plan_triad_pass` checks that the PLAN-phase Triad approved the plan" and "If Triad was skipped ... the gate still passes"
   - Issue: Current `core/triad.py:190-198` default critic returns PASS with no findings, and `core/triad.py:280-286` approves when no Critical finding remains. There is no artifact-level distinction between a real Critic run, stub mode, or intentionally skipped Triad. That makes `require_plan_triad_pass=True` mostly cosmetic in environments where the real agent is unavailable.
   - Suggestion: Add `triad_mode` / `critic_executor` / `skipped_reason` to the Triad artifact. Default auto-merge should require either a real Triad PASS or an explicit policy opt-out.

### Missing from Design

- Exact migration plan for existing `DogfoodState.workspace` tests and callers in `tests/test_dogfood.py`, `tests/test_dogfood_cli.py`, and `agent_launcher.py`.
- Recovery behavior for interrupted `FINALIZE` after `git add -A` but before commit.
- Atomic/locked write contract for `dogfood_state.json`, phase artifacts, `merge_report.json`, and `registry.json`.
- Exact source branch/current branch validation before merge.
- CLI routing ownership between `run_factory_cli.py` and `agent_launcher.py`.

### Positive Observations

- The design correctly moves runtime state out of the source repo into `%USERPROFILE%\.af-dogfood`, which addresses the existing `.af_runtime` coupling in `core/dogfood.py:213-217`.
- The denied path default includes `skills/registry.yaml`, matching the project’s known self-run pollution risk documented in `Master_Blueprint.md`.