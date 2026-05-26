# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-26 17:44
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

Cross-verified `core/dogfood.py:695` — code is correctly interpolated (`f"...{state.base_ref[:8]}→{cur_ref[:8]}"`). Cross-review Finding #3 is a false positive from arrow-character display corruption. All Critic findings stand.

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [Critical] `_is_crlf_only_diff` misclassifies untracked files as CRLF noise
- **Critic**: Untracked files always return empty stdout from `git diff -- <path>`, so they're filtered into `crlf_only` and dropped from `real_dirty`/`stage_files`. AI-creates-new-file (the common case) becomes `merge_status="no_changes"`.
- **Cross**: Reproduced directly — `git diff --ignore-cr-at-eol -- newfile.txt` returns 0 lines for untracked files. Confirms new-file regression.
- **Judgment**: Both flagged with reproduced evidence. `core/dogfood.py:599-602` applies the filter indiscriminately to `all_dirty` which includes the untracked set from `git ls-files --others` (line 588-589). This silently breaks the primary dogfood scenario.
- **Action Required**: Split tracked vs untracked before applying `_is_crlf_only_diff`. Either:
  - Apply filter only to `diff.stdout` (tracked); union untracked unconditionally into `real_dirty`, or
  - Guard inside `_is_crlf_only_diff` via `git ls-files --error-unmatch -- <path>` and return `False` for untracked.

#### 2. [ACCEPT] [High] `committed_changed` gated by `dogfood_commit_created` — pre-existing AI commits bypass policy
- **Critic**: At `core/dogfood.py:635-643`, `committed_changed` only computes when finalize itself created a commit. If AI executor already committed (common case), `pre_finalize_head == head`, `committed_changed=[]`, `merge_status="no_changes"` — opposite of the comment's stated intent.
- **Cross**: Same finding — `_default_ai_executor()` runs provider in worktree which may commit; downstream `_check_merge_policy()` reads empty `changed_files` from `merge_report.json` and skips denied/allowed path enforcement.
- **Judgment**: Both flagged. Comment at line 634 explicitly says "survives AI-commit advances" but gate logic contradicts it.
- **Action Required**: Compute `committed_changed` whenever `state.base_ref` is set and `head != state.base_ref`. Keep `dogfood_commit_created` as separate telemetry only.

#### 3. [ACCEPT] [High] `scope_violations` enforcement introduced without `MergePolicy` opt-in toggle
- **Critic**: Prior code marked scope as "logged only; merge gate enforcement in later phase". This PR introduces BLOCK at `core/dogfood.py:681-683` without adding a `MergePolicy` flag. Plan-allowlist-narrow + AI-side helper/fixture additions → silent BLOCK with no callsite signal.
- **Cross**: not flagged.
- **Judgment**: ACCEPT — Critic evidence is strong (policy semantic change without API surface). `MergePolicy` at lines 213-227 has no corresponding toggle, so callers cannot opt-in/opt-out as phases evolve.
- **Action Required**: Add `MergePolicy.enforce_scope_violations: bool = True` (or `False` for phased rollout) and gate the BLOCK on it: `if policy.enforce_scope_violations and scope_violations:`.

#### 4. [ACCEPT] [Medium] `dogfood_commit_created` signal computed but not propagated to gate
- **Critic**: At `core/dogfood.py:697-701`, comment says "verify a *new* commit was created" but check is `dogfood_commit == base_ref`. The stronger `dogfood_commit_created` signal exists in finalize but isn't persisted to `DogfoodState`, so policy can't use it.
- **Cross**: not flagged.
- **Judgment**: ACCEPT — comment/code intent mismatch is real. Either weaken the comment or surface the flag. Lower severity than #2/#3 since the current check is reasonable in practice.
- **Action Required**: Clarify intent. Option A: change comment to `# require dogfood_commit advanced from base_ref`. Option B: persist `state.dogfood_commit_created` and check it.

#### 5. [ACCEPT] [Medium] N+1 git subprocess in `_is_crlf_only_diff`
- **Critic**: One subprocess per file at `core/dogfood.py:599-601`. Windows fork ~50-150ms/call; compounds with Finding #1 (every untracked file gets a wasted call).
- **Cross**: not flagged.
- **Judgment**: ACCEPT — real perf concern, simple set-difference fix exists.
- **Action Required**: Replace per-file loop with set difference: `all_modified - real_modified` where both come from single `git diff --name-only [--ignore-cr-at-eol] HEAD` calls.

#### 6. [REJECT] Source-advanced diagnostic missing brace
- **Critic**: not flagged.
- **Cross**: Claims line 695 reads `{state.base_ref[:8]}??cur_ref[:8]}` (missing `{` before `cur_ref`).
- **Judgment**: REJECT — verified `core/dogfood.py:695` reads `f"source branch advanced: {state.base_ref[:8]}→{cur_ref[:8]}"`. Both expressions interpolate correctly. Cross-review likely saw garbled `→` arrow character in their terminal.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Untracked files filtered as CRLF noise | Critical | ACCEPT | Both |
| 2 | committed_changed gated by dogfood_commit_created | High | ACCEPT | Both |
| 3 | scope_violations BLOCK without MergePolicy flag | High | ACCEPT | Critic |
| 4 | dogfood_commit_created not used in gate | Medium | ACCEPT | Critic |
| 5 | N+1 git subprocess perf | Medium | ACCEPT | Critic |
| 6 | source-advanced diagnostic brace | — | REJECT | Cross |

### Recommendations

1. **Fix #1 first** (Critical, blocks merge): untracked-file split in finalize. Re-run dogfood end-to-end with an AI-creates-new-file scenario to confirm `stage_files` and `merge_status="ready"`.
2. **Fix #2** (High, regression): always compute `committed_changed` when `state.base_ref` set; decouple from `dogfood_commit_created`.
3. **Fix #3** (High, policy API): add `MergePolicy.enforce_scope_violations` flag — pick default after deciding rollout pace.
4. **Fix #4** (Medium): align comment with check, or persist `dogfood_commit_created` if stricter semantic is wanted.
5. **Fix #5** (Medium): batch the CRLF detection into 2 `git diff --name-only` calls.
6. **Add test coverage**: `tests/test_dogfood_isolation.py` (27 passing per Cross) doesn't exercise untracked-file path under CRLF filter. Add a regression test that creates an untracked file and asserts it survives `finalize_dogfood_result`.
7. **Cross-review's terminal encoding** garbled the `→` arrow — note for future reviews on Windows.