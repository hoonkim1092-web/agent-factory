# Dogfood Isolation and Auto-Merge Lifecycle

Date: 2026-05-25
Version: v2
Status: Draft
Audience: Agent Factory maintainers, dogfood pipeline implementers

## 1. Summary

Dogfood runs must execute self-modifying Agent Factory work in an isolated git worktree, then merge the verified result back into the source branch through an automated policy gate.

This is not an MVP-only safety wrapper. It is the production lifecycle for AF-on-AF work:

```text
source workspace
-> isolated dogfood branch/worktree
-> implement, verify, review
-> commit dogfood result
-> policy-gated merge back to source branch
-> complete or blocked
```

The default target behavior should be automation:

```text
--merge auto-policy
```

`auto-policy` means "merge automatically only when every policy check passes." It does not mean unconditional merge. Any conflict, source drift, forbidden path, missing PASS artifact, or dirty source state blocks the merge and leaves the dogfood branch available for inspection.

## 2. Problem

Current dogfood execution uses one workspace concept for too many things:

- Source code under active development.
- Runtime state and phase artifacts.
- Command execution cwd.
- Future AI-generated edits.
- Verification and review output.

That coupling is unsafe once dogfood connects real research and real agent executors. A failed self-modifying run can leave partial edits, generated artifacts, logs, or retry output in the maintainer's working copy.

Simple isolation alone is not enough. If dogfood edits a disconnected copy, the result has no clean path back to the source branch. The isolation model must preserve git connectivity and define how verified changes are merged.

## 3. Core Decision

Dogfood isolation is branch-based:

```text
source workspace:
  D:\warkSpaces\agent-factory
  branch: <source_branch>

dogfood worktree:
  %USERPROFILE%\.af-dogfood\<run_id>\worktree
  branch: dogfood/<run_id>

runtime workspace:
  %USERPROFILE%\.af-dogfood\<run_id>\runtime
  state, logs, phase artifacts, merge reports
```

The worktree is created from the source workspace with `git worktree add -b dogfood/<run_id> <base_ref>`.

The dogfood branch is the connection between isolation and merge. Dogfood edits and commits only on `dogfood/<run_id>`. The source branch receives the result only through the merge lifecycle.

The runtime root `%USERPROFILE%\.af-dogfood` is global and CWD-independent. This ensures that `af dogfood status <run_id>` works correctly regardless of the caller's working directory.

## 4. State Model

`DogfoodState` should stop treating `workspace` as a single overloaded field. It should carry explicit source, worktree, and runtime paths.

Required fields:

```python
@dataclass
class DogfoodState:
    run_id: str
    task: str
    phase: DogfoodPhase

    source_workspace: str
    source_branch: str
    base_ref: str

    worktree_workspace: str | None
    dogfood_branch: str

    runtime_workspace: str

    isolation_status: str  # pending | ready | failed | cleaned
    merge_status: str      # none | ready | merged | conflict | policy_rejected | failed
    merge_mode: str        # auto_policy | manual | never

    dogfood_commit: str | None
    merged_commit: str | None
    last_failure: str | None
```

Compatibility rule:

- Existing callers that pass `workspace` should map it to `source_workspace`. Add a `workspace` property alias: `@property def workspace(self): return self.source_workspace`.
- Runtime paths must default to `%USERPROFILE%\.af-dogfood\<run_id>\runtime` regardless of CWD.
- Command execution after isolation must use `worktree_workspace`, not `source_workspace`.

`_default_runtime_workspace(run_id)` must take `run_id` as the sole argument. It must not accept or use `workspace`. This prevents CWD-dependent path construction.

## 5. Phase Model

The dogfood phase sequence should make isolation and merge visible in state and status output.

```text
PENDING
INTERVIEW
RESEARCH_BRIEF
RESEARCH
SPEC
PREMORTEM
PLAN        ← Triad runs here (正反合 plan review)
ISOLATE
IMPLEMENT
VERIFY
REVIEW
FINALIZE
MERGE
COMPLETE
```

Failure states:

```text
BLOCKED
```

`ISOLATE` creates the branch/worktree. `FINALIZE` commits and checks merge readiness. `MERGE` performs the policy-gated merge.

Triad runs in the PLAN phase only. It reviews the plan before execution begins. There is no post-REVIEW Triad step. Future post-implementation review by an LLM agent is a separate work item.

## 6. Isolation Lifecycle

`prepare_isolated_worktree(state)` should do the following:

1. Resolve `source_workspace` to a git repository root.
2. Read `source_branch` with `git branch --show-current`.
3. Read `base_ref` with `git rev-parse HEAD`.
4. Refuse to continue when the source worktree is dirty. There is no supported dirty-run mode. The caller must commit or stash before starting dogfood.
5. Compute:

```text
dogfood_branch = dogfood/<run_id>
worktree_workspace = %USERPROFILE%\.af-dogfood\<run_id>\worktree
runtime_workspace = %USERPROFILE%\.af-dogfood\<run_id>\runtime
```

6. Create the dogfood branch and worktree with one internal retry:

```python
def prepare_isolated_worktree(state):
    for attempt in range(2):
        try:
            git worktree add <worktree_workspace> -b dogfood/<run_id> <base_ref>
            state.isolation_status = "ready"
            return
        except GitWorktreeError:
            if attempt == 0 and _safe_to_cleanup_partial_isolation(state):
                _cleanup_partial_isolation(state)
                continue
            state.isolation_status = "failed"
            raise
```

7. Persist the state immediately after creation.

The retry is local to `prepare_isolated_worktree()`. There is no `isolate_attempts` field on `DogfoodState`.

After this point:

- IMPLEMENT runs in `worktree_workspace`.
- VERIFY runs in `worktree_workspace`.
- REVIEW inspects `worktree_workspace` and the dogfood branch diff.
- Runtime artifacts are written only to `runtime_workspace`.

## 7. Finalize Lifecycle

`finalize_dogfood_result(state)` should run only after VERIFY and REVIEW have passed.

It should:

1. Confirm `worktree_workspace` exists and is on `dogfood_branch`.
2. Confirm there are source changes to commit.
3. Reject forbidden runtime/source pollution.
4. Stage allowed changes.
5. Commit the dogfood result.
6. Record `dogfood_commit`.
7. Generate a `merge_report.json`.

Commit command:

```powershell
git -C <worktree_workspace> add -A
git -C <worktree_workspace> commit -m "dogfood: <task summary>"
```

If there are no source changes, FINALIZE may mark the run complete without merge only when the requested task was non-mutating. For self-modifying runs, no diff should be treated as blocked unless the plan explicitly expected no source change.

## 8. Auto-Merge Policy

The default merge mode should be:

```text
auto_policy
```

Policy object:

```python
@dataclass
class MergePolicy:
    mode: Literal["auto_policy", "manual", "never"] = "auto_policy"
    require_clean_source: bool = True
    allow_source_advanced: bool = False
    require_verify_pass: bool = True
    require_review_pass: bool = True
    require_plan_triad_pass: bool = True
    require_dogfood_commit: bool = True
    allowed_paths: list[str] = field(default_factory=list)
    denied_paths: list[str] = field(default_factory=lambda: [
        ".af_runtime/",
        "runtime/",
        "skills/registry.yaml",
    ])
```

`require_plan_triad_pass` checks that the PLAN-phase Triad approved the plan before execution. It is an opt-out safety gate, defaulting to `True`. If Triad was skipped (e.g., stub mode with no findings), the gate still passes.

`allowed_paths=[]` means "all tracked source paths are allowed except denied paths." A stricter caller may pass an allowlist for targeted changes.

Auto-merge is allowed only when all checks pass:

```text
source workspace is clean
source branch is still at base_ref, unless allow_source_advanced=True
dogfood branch has a committed result
changed files do not match denied paths
changed files match allowed_paths when allowlist is non-empty
VERIFY passed
REVIEW passed
PLAN Triad approved (when require_plan_triad_pass=True)
merge dry-run has no conflicts
runtime artifacts are outside the source diff
```

Any failed check sets:

```text
merge_status = policy_rejected | conflict | failed
phase = BLOCKED
```

The dogfood branch and worktree must remain available for inspection unless cleanup is explicitly requested.

## 9. Merge Lifecycle

`merge_dogfood_branch(state, policy)` should:

1. Acquire a MERGE mutex lock scoped to `source_workspace`. Only one merge into the same source branch may proceed at a time. Concurrent runs against different source branches need no mutex.
2. Load and validate the latest state.
3. Verify the dogfood commit exists.
4. Run crash recovery: check `git merge-base --is-ancestor <dogfood_commit> HEAD` on `source_workspace`. If the dogfood commit is already an ancestor of HEAD, the merge completed in a prior interrupted run. Set `merge_status = merged`, `merged_commit = HEAD`, `phase = COMPLETE`, and return without re-merging.
5. Run policy checks.
6. Run a conflict check.
7. Merge into `source_branch` if allowed.
8. Persist the merge result.
9. Release the mutex.

Conflict check:

```powershell
git -C <source_workspace> merge --no-commit --no-ff dogfood/<run_id>
git -C <source_workspace> reset --merge
```

Use `git reset --merge` (not `git merge --abort`) for cleanup. `--abort` requires `MERGE_HEAD` to exist, which is absent when the merge ends "Already up to date." `reset --merge` is safe in both the conflict and no-conflict cases and does not depend on merge state.

Actual merge:

```powershell
git -C <source_workspace> merge --no-ff dogfood/<run_id>
```

On success:

```text
merge_status = merged
phase = COMPLETE
merged_commit = <source HEAD after merge>
```

On conflict:

```text
merge_status = conflict
phase = BLOCKED
last_failure = "merge_conflict"
```

On policy rejection:

```text
merge_status = policy_rejected
phase = BLOCKED
last_failure = <specific policy failure>
```

## 10. Source Drift Policy

`base_ref` is the source branch commit where the dogfood branch started.

Default policy:

```text
allow_source_advanced = False
```

That means auto-merge is blocked if the source branch moved after the dogfood run started. This avoids merging a result that was verified against an older source state.

Future advanced policy:

```text
allow_source_advanced = True
```

When enabled, dogfood should rebase or merge the latest source branch into `dogfood/<run_id>`, rerun VERIFY/REVIEW, then attempt merge again. This should be a separate implementation step, not the initial auto-merge behavior.

## 11. Runtime and Source Boundaries

Runtime artifacts must not be committed into `dogfood/<run_id>` unless explicitly declared as source outputs.

Runtime-only examples:

```text
dogfood_state.json
interview.json
research.json
spec.json
premortem.json
plan.json
verify.json
review.json
merge_report.json
logs/
```

Source outputs are normal repository files such as:

```text
core/*.py
tests/*.py
docs/*.md
af.spec
Master_Blueprint.md
```

The merge report must separate:

```json
{
  "source_workspace": "...",
  "worktree_workspace": "...",
  "runtime_workspace": "...",
  "source_branch": "...",
  "dogfood_branch": "...",
  "base_ref": "...",
  "dogfood_commit": "...",
  "changed_files": [],
  "denied_path_hits": [],
  "policy_checks": {},
  "merge_status": "ready"
}
```

## 12. Triad Contract

Triad runs in the PLAN phase only. The Critic attacks the plan and returns a `TriadCriticReport`. The Architect resolves findings and returns a `(final_plan, decisions)` tuple.

The Architect is read-only with respect to plan commands. It may annotate decisions, restructure steps, or flag concerns, but it must not modify or inject shell commands into the final plan. The command list in `final_plan` must be identical to `initial_plan` unless the Architect explicitly documents which command it changed and why in its decision record.

This is a contract constraint, not a runtime restoration. There is no silent command restoration at execution time. Violation of the contract is reported as `TriadContractError` (a distinct exception type from `TriadBlockedError`).

```python
class TriadContractError(RuntimeError):
    """Raised when Architect output violates a contract constraint."""
```

`shell=False` is the mandatory execution policy for all plan commands after the Architect returns. This ensures no LLM-generated string reaches the shell directly. CommandSpec schema (structured command representation) is out of scope for this document and tracked as a separate work item.

Approval logic:

- `approved = True` when no Critical finding remains unresolved (not REJECTed by Architect).
- High-severity findings with HOLD status do not block `approved`. They remain in the decision record for review.
- If a High-severity HOLD is known to affect command correctness, the plan phase should set `last_failure` and block before ISOLATE.

The `require_plan_triad_pass` policy gate in §8 checks `TriadResult.approved`. A WARN-only Critic report with no Critical findings produces `approved=True` and passes the gate.

## 13. Active Run Registry

The active run registry tracks concurrent dogfood runs in a file at:

```text
%USERPROFILE%\.af-dogfood\registry.json
```

Each entry contains:

```json
{
  "run_id": "...",
  "pid": 12345,
  "started_at": 1716550000,
  "source_workspace": "...",
  "source_branch": "...",
  "phase": "IMPLEMENT"
}
```

Stale detection: an entry is stale when the recorded `pid` is not alive or `started_at` is older than the configured timeout (default: 24 hours). Stale entries are removed silently at next registry access.

Concurrent run behavior:

- Multiple runs against different source branches: allowed with no warning.
- Multiple runs against the same source workspace: allowed with a warning logged to the run's runtime log.
- MERGE phase: mutex-protected per source workspace (§9, step 1). Only one merge at a time per source branch.

There is no heartbeat. Liveness is checked only at registry read time using `pid + started_at_epoch`.

## 14. CLI Contract

Default run:

```powershell
af dogfood run "<task>"
```

Equivalent behavior:

```text
--merge auto-policy
```

Explicit modes:

```powershell
af dogfood run "<task>" --merge auto-policy
af dogfood run "<task>" --merge manual
af dogfood run "<task>" --merge never
```

Manual merge command:

```powershell
af dogfood merge <run_id>
```

Status:

```powershell
af dogfood status <run_id>
```

Status must resolve the run using only `run_id` and the global runtime root `%USERPROFILE%\.af-dogfood`. It must not depend on the caller's CWD. The `workspace` argument to `_default_runtime_workspace()` must not exist in this implementation.

Cleanup:

```powershell
af dogfood cleanup <run_id>
```

Expected status output should include:

```text
run_id
phase
source_branch
dogfood_branch
base_ref
dogfood_commit
merge_mode
merge_status
last_failure
worktree_workspace
runtime_workspace
```

## 15. Cleanup Policy

Cleanup should never delete source work by default.

Allowed cleanup targets:

- Runtime logs and phase artifacts after a retention period.
- Dogfood worktree after merge success.
- Dogfood branch after merge success, only when explicitly requested or configured.

Blocked cleanup:

- Deleting an unmerged dogfood branch.
- Deleting a worktree with uncommitted changes.
- Deleting runtime artifacts for BLOCKED runs unless `--force` is explicit.

Recommended commands:

```powershell
git -C <source_workspace> worktree remove <worktree_workspace>
git -C <source_workspace> branch -d dogfood/<run_id>
```

Use `branch -D` only for explicit forced cleanup.

## 16. Test Plan

Required tests:

1. `prepare_isolated_worktree` records source branch, base ref, dogfood branch, worktree path, and runtime path.
2. IMPLEMENT and VERIFY use `worktree_workspace`, not `source_workspace`.
3. Runtime artifacts are written only under `runtime_workspace`.
4. FINALIZE creates a dogfood commit and records `dogfood_commit`.
5. Auto-merge succeeds when source is clean, unchanged from `base_ref`, and all gates pass.
6. Auto-merge blocks when source workspace is dirty.
7. Auto-merge blocks when source branch advanced after `base_ref`.
8. Auto-merge blocks on denied path changes.
9. Auto-merge blocks on merge conflict and leaves worktree/branch intact.
10. `--merge manual` stops at merge-ready without merging.
11. `--merge never` completes verification/finalize but never attempts source merge.
12. Cleanup refuses unmerged or dirty dogfood worktrees without force.
13. `af dogfood status <run_id>` succeeds regardless of caller's CWD.
14. MERGE crash recovery: when dogfood commit is already ancestor of source HEAD, returns `merged` without re-merging.
15. `git reset --merge` is used (not `git merge --abort`) in conflict check cleanup.
16. `prepare_isolated_worktree` retries once on GitWorktreeError and succeeds on second attempt.
17. `require_plan_triad_pass=False` allows merge even when Triad was skipped.

Integration smoke:

```powershell
python -m pytest tests/test_dogfood.py tests/test_dogfood_cli.py tests/test_dogfood_integration.py
```

Packaging impact check:

- Any new runtime module must be added to `af.spec` hidden imports.
- Frozen CLI smoke should include `af.exe dogfood --help`, `af.exe dogfood run --help`, and `af.exe dogfood merge --help` when packaging is in scope.

## 17. Implementation Order

Recommended implementation sequence:

1. Add state fields and serialization compatibility (`source_workspace`, `worktree_workspace`, `runtime_workspace`, `isolation_status`, `merge_status`, `merge_mode`, `dogfood_commit`, `merged_commit`). Add `workspace` property alias for backward compatibility.
2. Change `_default_runtime_workspace(run_id)` to use global `%USERPROFILE%\.af-dogfood` root (no `workspace` argument).
3. Add merge mode CLI parsing.
4. Add `prepare_isolated_worktree` with one-retry internal loop.
5. Route IMPLEMENT, VERIFY, and REVIEW cwd/diff logic to `worktree_workspace`.
6. Add FINALIZE phase and dogfood branch commit creation.
7. Add merge policy checks with `require_plan_triad_pass`.
8. Add active run registry.
9. Add MERGE phase with mutex, crash recovery, conflict check (`reset --merge`), and `auto_policy`.
10. Add `dogfood merge <run_id>` for manual or retryable merge.
11. Add cleanup command.
12. Update `Master_Blueprint.md` and `af.spec` if new modules are introduced.

## 18. Non-Goals

This design does not require:

- Copying files between source and dogfood folders.
- Patch-first finalization as the normal path.
- Unconditional automatic merge.
- Rebase-on-drift in the first implementation.
- Automatic deletion of blocked dogfood branches.
- Post-REVIEW Triad (LLM review of worktree diff) — future work item.
- CommandSpec structured command schema — separate work item.
- Heartbeat-based liveness for the run registry.

Patch export may remain useful for debugging, but the primary product path is branch/worktree plus policy-gated merge.

## 19. Acceptance Criteria

The feature is complete when:

- `dogfood run` creates and uses a real git worktree on `dogfood/<run_id>`.
- Source, worktree, and runtime paths are distinct in state and status output.
- IMPLEMENT/VERIFY/REVIEW never execute in the source workspace after isolation.
- PASS runs create a dogfood commit.
- `auto_policy` merges to the source branch only when all policy checks pass.
- Policy failures block without losing the dogfood branch or worktree.
- Manual merge and cleanup commands exist.
- `af dogfood status <run_id>` works from any CWD.
- MERGE crash recovery is idempotent.
- Tests cover success, source drift, dirty source, denied path, conflict, manual mode, never mode, cleanup refusal, CWD-independent status, and crash recovery.
