"""Tests for dogfood worktree isolation + auto-merge lifecycle (§17 Step 16).

Covers design §16 test requirements:
  1. prepare_isolated_worktree records fields
  2. IMPLEMENT/VERIFY use worktree_workspace cwd
  3. Runtime artifacts in runtime_workspace
  4. FINALIZE creates dogfood_commit
  5. Auto-merge succeeds (clean source, all gates pass)
  6. Auto-merge blocks when source is dirty
  7. Auto-merge blocks when source branch advanced
  8. Auto-merge blocks on denied path
  9. Auto-merge blocks on conflict; worktree intact
 10. --merge manual stops at merge-ready
 11. --merge never completes without merging
 12. Cleanup refuses unmerged worktrees without force (API contract)
 13. CWD-independent status via _default_runtime_workspace
 14. MERGE crash recovery: already-ancestor → merged without re-merge
 15. git reset --merge used (not merge --abort) in conflict check
 16. prepare_isolated_worktree retries once on GitWorktreeError
 17. require_plan_triad_pass=False allows merge even when Triad skipped
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from core.dogfood import (
    DogfoodPhase,
    DogfoodState,
    GitWorktreeError,
    MergePolicy,
    _check_merge_policy,
    _cleanup_partial_isolation,
    _default_runtime_workspace,
    _default_worktree_workspace,
    _dogfood_root,
    _run_isolate_phase,
    _run_merge_phase,
    _safe_to_cleanup_partial_isolation,
    block_run,
    create_run,
    finalize_dogfood_result,
    merge_dogfood_branch,
    prepare_isolated_worktree,
    run_all,
    save_state,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(
    tmp_path: Path,
    phase: DogfoodPhase = DogfoodPhase.ISOLATE,
    isolation_status: str = "pending",
    merge_mode: str = "auto_policy",
) -> DogfoodState:
    state = create_run(
        "test isolation task",
        str(tmp_path),
        run_id="iso-test-001",
        runtime_workspace=str(tmp_path / ".runtime"),
        merge_mode=merge_mode,
    )
    state.phase = phase
    state.worktree_workspace = str(tmp_path / "worktree")
    state.dogfood_branch = "dogfood/iso-test-001"
    state.isolation_status = isolation_status
    return state


def _fake_git_ok(args, cwd, **kwargs):
    """Stub git that always succeeds."""
    result = MagicMock()
    result.returncode = 0
    result.stdout = ""
    result.stderr = ""
    return result


def _fake_git_dirty(args, cwd, **kwargs):
    """Stub git status --porcelain that reports dirty workspace."""
    result = MagicMock()
    result.returncode = 0
    if "status" in args and "--porcelain" in args:
        result.stdout = "M core/dogfood.py\n"
    elif "branch" in args and "--show-current" in args:
        result.stdout = "main"
    elif "rev-parse" in args:
        result.stdout = "abc1234def5678"
    else:
        result.stdout = ""
    return result


def _make_git_clean(branch="main", base_ref="abc1234def5678"):
    """Return a git stub that reports clean source and given branch/ref."""
    def _stub(args, cwd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        if "status" in args and "--porcelain" in args:
            result.stdout = ""  # clean
        elif "branch" in args and "--show-current" in args:
            result.stdout = branch
        elif "rev-parse" in args and "HEAD" in args:
            result.stdout = base_ref
        elif "worktree" in args and "add" in args:
            # Create the worktree directory so Path.exists() passes
            wt = args[-2] if len(args) >= 3 else cwd
            Path(wt).mkdir(parents=True, exist_ok=True)
            result.stdout = ""
        else:
            result.stdout = ""
        return result
    return _stub


# ---------------------------------------------------------------------------
# §16 Test 1: prepare_isolated_worktree records fields
# ---------------------------------------------------------------------------

def test_prepare_isolated_worktree_records_fields(tmp_path):
    state = _make_state(tmp_path)
    git_stub = _make_git_clean(branch="feature-branch", base_ref="deadbeef1234")

    with patch("core.dogfood._git", side_effect=git_stub):
        prepare_isolated_worktree(state)

    assert state.source_branch == "feature-branch"
    assert state.base_ref == "deadbeef1234"
    assert state.dogfood_branch == "dogfood/iso-test-001"
    assert state.worktree_workspace != ""
    assert state.isolation_status == "ready"


# ---------------------------------------------------------------------------
# §16 Test 2: IMPLEMENT and VERIFY use worktree_workspace cwd
# ---------------------------------------------------------------------------

def test_implement_uses_worktree_cwd(tmp_path, monkeypatch):
    import core.dogfood as df
    state = _make_state(tmp_path, phase=DogfoodPhase.IMPLEMENT, isolation_status="ready")
    state.worktree_workspace = str(tmp_path / "worktree")

    captured_cwd: list[str] = []

    def _fake_runner(cmd, cwd):
        captured_cwd.append(cwd)
        return True, "ok"

    monkeypatch.setattr(df, "_command_runner", _fake_runner)
    plan = {"steps": [{"id": "S1", "commands": ["echo hi"]}]}
    df._run_implement_phase(state, {"plan_dict": plan})

    assert captured_cwd == [state.worktree_workspace]


def test_verify_uses_worktree_cwd(tmp_path, monkeypatch):
    import core.dogfood as df
    state = _make_state(tmp_path, phase=DogfoodPhase.VERIFY, isolation_status="ready")
    state.worktree_workspace = str(tmp_path / "worktree")

    captured_cwd: list[str] = []

    def _fake_runner(cmd, cwd):
        captured_cwd.append(cwd)
        return True, "ok"

    monkeypatch.setattr(df, "_command_runner", _fake_runner)
    df._run_verify_phase(state, {"commands": ["pytest"]})

    assert captured_cwd == [state.worktree_workspace]


def test_implement_falls_back_to_source_when_not_isolated(tmp_path, monkeypatch):
    import core.dogfood as df
    state = _make_state(tmp_path, phase=DogfoodPhase.IMPLEMENT, isolation_status="pending")
    state.worktree_workspace = ""

    captured_cwd: list[str] = []

    def _fake_runner(cmd, cwd):
        captured_cwd.append(cwd)
        return True, "ok"

    monkeypatch.setattr(df, "_command_runner", _fake_runner)
    df._run_implement_phase(state, {"plan_dict": {"steps": [{"id": "S1", "commands": ["x"]}]}})

    assert captured_cwd == [state.source_workspace]


# ---------------------------------------------------------------------------
# §16 Test 3: Runtime artifacts in runtime_workspace
# ---------------------------------------------------------------------------

def test_runtime_artifacts_in_runtime_workspace(tmp_path):
    state = _make_state(tmp_path)
    from core.dogfood import _artifact_path
    path = _artifact_path(state, "some_artifact.json")
    assert str(path).startswith(state.runtime_workspace)


# ---------------------------------------------------------------------------
# §16 Test 4: FINALIZE creates dogfood_commit
# ---------------------------------------------------------------------------

def test_finalize_records_dogfood_commit(tmp_path):
    state = _make_state(tmp_path, phase=DogfoodPhase.FINALIZE, isolation_status="ready")
    state.worktree_workspace = str(tmp_path / "worktree")
    Path(state.worktree_workspace).mkdir(parents=True, exist_ok=True)
    state.base_ref = "base001"

    rev_count = {"n": 0}

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        if "branch" in args and "--show-current" in args:
            r.stdout = state.dogfood_branch
        elif "rev-parse" in args and "HEAD" in args:
            rev_count["n"] += 1
            r.stdout = "oldsha" if rev_count["n"] == 1 else "newsha"
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            r.stdout = "real content change"  # not CRLF-only
        elif "diff" in args and "--name-only" in args and ".." in " ".join(args):
            r.stdout = "core/utils.py"
        elif "diff" in args and "--name-only" in args:
            r.stdout = "core/utils.py"
        elif "ls-files" in args:
            r.stdout = ""
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        finalize_dogfood_result(state)

    assert state.dogfood_commit == "newsha"
    assert state.merge_status == "ready"


def test_finalize_selective_staging_uses_plan_allowlist(tmp_path):
    """P3: finalize stages only files present in plan artifacts + tests_required."""
    import json
    state = _make_state(tmp_path, phase=DogfoodPhase.FINALIZE, isolation_status="ready")
    state.worktree_workspace = str(tmp_path / "worktree")
    Path(state.worktree_workspace).mkdir(parents=True, exist_ok=True)
    state.base_ref = "base001"

    plan = {
        "steps": [
            {"id": "S1", "artifacts": ["core/utils.py", "Master_Blueprint.md"], "tests_required": ["tests/test_utils.py"]},
        ]
    }
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    state.plan_path = str(plan_file)

    staged: list[list] = []
    rev_count = {"n": 0}

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        if "branch" in args and "--show-current" in args:
            r.stdout = state.dogfood_branch
        elif "rev-parse" in args and "HEAD" in args:
            rev_count["n"] += 1
            r.stdout = "oldsha" if rev_count["n"] == 1 else "newsha"
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            r.stdout = "real content change"  # not CRLF-only
        elif "diff" in args and "--name-only" in args and ".." in " ".join(args):
            r.stdout = "core/utils.py"  # committed file after commit
        elif "diff" in args and "--name-only" in args:
            r.stdout = "core/utils.py\nrun_output.txt"
        elif "ls-files" in args:
            r.stdout = ""
        elif args[0] == "add":
            staged.append(list(args))
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        report = finalize_dogfood_result(state)

    # Only the allowed file should be staged
    assert any("core/utils.py" in " ".join(a) for a in staged)
    assert not any("run_output.txt" in " ".join(a) for a in staged)
    assert report["changed_files"] == ["core/utils.py"]
    assert "run_output.txt" in report["scope_violations"]


def test_finalize_runs_final_docs_sync_before_staging(tmp_path):
    """FINALIZE syncs generated docs after review pass and stages them with code."""
    import json
    import core.dogfood as df

    state = _make_state(tmp_path, phase=DogfoodPhase.FINALIZE, isolation_status="ready")
    state.worktree_workspace = str(tmp_path / "worktree")
    Path(state.worktree_workspace).mkdir(parents=True, exist_ok=True)
    state.base_ref = "base001"

    plan = {"steps": [{"id": "S1", "artifacts": ["core/utils.py"], "tests_required": []}]}
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    state.plan_path = str(plan_file)

    staged: list[list] = []
    rev_count = {"n": 0}

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        if "branch" in args and "--show-current" in args:
            r.stdout = state.dogfood_branch
        elif "rev-parse" in args and "HEAD" in args:
            rev_count["n"] += 1
            r.stdout = "oldsha" if rev_count["n"] == 1 else "newsha"
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            r.stdout = "real content change"
        elif "diff" in args and "--name-only" in args and ".." in " ".join(args):
            r.stdout = "core/utils.py\nMaster_Blueprint.md\ndocs/code_review/code-review.md"
        elif "diff" in args and "--name-only" in args:
            r.stdout = "core/utils.py\nMaster_Blueprint.md\ndocs/code_review/code-review.md"
        elif "ls-files" in args:
            r.stdout = ""
        elif args[0] == "add":
            staged.append(list(args))
        return r

    with patch("core.dogfood._git", side_effect=_git_stub), \
            patch("core.dogfood._run_final_docs_sync",
                  return_value=["Master_Blueprint.md", "docs/code_review/code-review.md"]) as sync:
        report = finalize_dogfood_result(state)

    sync.assert_called_once_with(state)
    staged_flat = " ".join(" ".join(a) for a in staged)
    assert "core/utils.py" in staged_flat
    assert "Master_Blueprint.md" in staged_flat
    assert "docs/code_review/code-review.md" in staged_flat
    assert report["scope_violations"] == []
    assert report["final_docs_synced"] == [
        "Master_Blueprint.md",
        "docs/code_review/code-review.md",
    ]


def test_finalize_fallback_stages_all_when_no_plan(tmp_path):
    """P3: when plan_path is absent, all changed files are staged (no scope violations)."""
    import json
    state = _make_state(tmp_path, phase=DogfoodPhase.FINALIZE, isolation_status="ready")
    state.worktree_workspace = str(tmp_path / "worktree")
    Path(state.worktree_workspace).mkdir(parents=True, exist_ok=True)
    state.plan_path = ""  # no plan
    state.base_ref = "base001"

    staged: list[list] = []
    rev_count = {"n": 0}

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        if "branch" in args and "--show-current" in args:
            r.stdout = state.dogfood_branch
        elif "rev-parse" in args and "HEAD" in args:
            rev_count["n"] += 1
            r.stdout = "oldsha" if rev_count["n"] == 1 else "newsha"
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            r.stdout = "real content change"  # not CRLF-only
        elif "diff" in args and "--name-only" in args and ".." in " ".join(args):
            r.stdout = "core/utils.py\nrun_output.txt"
        elif "diff" in args and "--name-only" in args:
            r.stdout = "core/utils.py\nrun_output.txt"
        elif "ls-files" in args:
            r.stdout = ""
        elif args[0] == "add":
            staged.append(list(args))
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        report = finalize_dogfood_result(state)

    assert report["scope_violations"] == []
    assert set(report["changed_files"]) == {"core/utils.py", "run_output.txt"}


# ---------------------------------------------------------------------------
# §16 Tests 5-9: Merge policy checks
# ---------------------------------------------------------------------------

def _make_merge_state(tmp_path, dogfood_commit="abc123") -> DogfoodState:
    state = _make_state(tmp_path, phase=DogfoodPhase.MERGE)
    state.source_branch = "main"
    state.base_ref = "base001"
    state.dogfood_commit = dogfood_commit
    state.merge_status = "ready"
    return state


def test_check_merge_policy_clean_source_passes(tmp_path):
    state = _make_merge_state(tmp_path)
    policy = MergePolicy(mode="auto_policy")

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""  # clean
        if "rev-parse" in args:
            r.stdout = state.base_ref
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        ok, reason = _check_merge_policy(state, policy, changed_files=[])

    assert ok is True


def test_check_merge_policy_dirty_source_blocks(tmp_path):
    state = _make_merge_state(tmp_path)
    policy = MergePolicy(mode="auto_policy", require_clean_source=True)

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = "M core/dogfood.py" if "status" in args else state.base_ref
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        ok, reason = _check_merge_policy(state, policy, changed_files=[])

    assert ok is False
    assert "dirty" in reason


def test_check_merge_policy_source_advanced_blocks(tmp_path):
    state = _make_merge_state(tmp_path, dogfood_commit="abc123")
    state.base_ref = "base001"
    policy = MergePolicy(allow_source_advanced=False)

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        if "status" in args:
            r.stdout = ""  # clean
        elif "rev-parse" in args:
            r.stdout = "newref999"  # advanced from base001
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        ok, reason = _check_merge_policy(state, policy, [])

    assert ok is False
    assert "advanced" in reason


def test_check_merge_policy_denied_path_blocks(tmp_path):
    state = _make_merge_state(tmp_path)
    policy = MergePolicy(denied_paths=["skills/registry.yaml"])

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = "" if "status" in args else state.base_ref
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        ok, reason = _check_merge_policy(state, policy, ["skills/registry.yaml"])

    assert ok is False
    assert "denied" in reason


def test_check_merge_policy_scope_violations_blocks(tmp_path):
    """scope_violations (non-CRLF dirty outside plan allowlist) must block merge."""
    state = _make_merge_state(tmp_path)
    policy = MergePolicy(mode="auto_policy")

    with patch("core.dogfood._git"):
        ok, reason = _check_merge_policy(
            state, policy, changed_files=["core/utils.py"],
            scope_violations=["run_output.txt"],
        )

    assert ok is False
    assert "scope_violations" in reason
    assert "run_output.txt" in reason


def test_check_merge_policy_dogfood_commit_equals_base_ref_blocks(tmp_path):
    """require_dogfood_commit must reject when dogfood_commit == base_ref (no new commit)."""
    state = _make_merge_state(tmp_path, dogfood_commit="base001")  # same as base_ref
    state.base_ref = "base001"
    # disable other checks so only require_dogfood_commit fires
    policy = MergePolicy(
        mode="auto_policy",
        require_dogfood_commit=True,
        require_clean_source=False,
        allow_source_advanced=True,
    )

    with patch("core.dogfood._git"):
        ok, reason = _check_merge_policy(state, policy, changed_files=[])

    assert ok is False
    assert "dogfood_commit" in reason


def test_finalize_crlf_only_files_excluded_from_scope_violations(tmp_path):
    """Files that differ only in CRLF/LF are excluded from scope_violations and not staged."""
    import json
    state = _make_state(tmp_path, phase=DogfoodPhase.FINALIZE, isolation_status="ready")
    state.worktree_workspace = str(tmp_path / "worktree")
    Path(state.worktree_workspace).mkdir(parents=True, exist_ok=True)
    state.base_ref = "base001"

    plan = {"steps": [{"id": "S1", "artifacts": ["core/utils.py"], "tests_required": []}]}
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    state.plan_path = str(plan_file)

    staged: list[list] = []
    rev_count = {"n": 0}

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        if "branch" in args and "--show-current" in args:
            r.stdout = state.dogfood_branch
        elif "rev-parse" in args and "HEAD" in args:
            rev_count["n"] += 1
            r.stdout = "oldsha" if rev_count["n"] == 1 else "newsha"
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            filepath = args[-1]
            # core/utils.py has real changes; syncCompyne/foo.py is CRLF-only
            r.stdout = "" if "syncCompyne" in filepath else "real diff output"
        elif "diff" in args and "--name-only" in args and ".." in " ".join(args):
            r.stdout = "core/utils.py"
        elif "diff" in args and "--name-only" in args:
            r.stdout = "core/utils.py\nsyncCompyne/foo.py"
        elif "ls-files" in args:
            r.stdout = ""
        elif args[0] == "add":
            staged.append(list(args))
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        report = finalize_dogfood_result(state)

    # CRLF-only file must not appear in scope_violations or staged
    assert "syncCompyne/foo.py" not in report["scope_violations"]
    assert not any("syncCompyne" in " ".join(a) for a in staged)
    # real change file must be staged and committed
    assert any("core/utils.py" in " ".join(a) for a in staged)
    assert report["all_dirty_files"] == ["core/utils.py", "syncCompyne/foo.py"]


# ---------------------------------------------------------------------------
# §16 Test 10: --merge manual stops at merge-ready
# ---------------------------------------------------------------------------

def test_run_merge_phase_manual_sets_ready_and_complete(tmp_path):
    """manual mode: pipeline finishes COMPLETE but merge_status='ready' (git merge pending)."""
    state = _make_merge_state(tmp_path)
    state.merge_mode = "manual"
    state.phase = DogfoodPhase.MERGE

    result = _run_merge_phase(state, merge_mode="manual")

    assert result["merge_status"] == "ready"
    # Phase reaches COMPLETE so run_all loop exits — 'dogfood merge' does the git merge.
    assert state.phase == DogfoodPhase.COMPLETE
    assert state.merged_commit == ""  # no actual git merge yet


# ---------------------------------------------------------------------------
# §16 Test 11: --merge never completes without merging
# ---------------------------------------------------------------------------

def test_run_merge_phase_never_completes_without_merge(tmp_path):
    state = _make_merge_state(tmp_path)
    state.merge_mode = "never"
    state.phase = DogfoodPhase.MERGE

    result = _run_merge_phase(state, merge_mode="never")

    assert result["merge_status"] == "never"
    assert state.phase == DogfoodPhase.COMPLETE
    assert state.merged_commit == ""  # no actual merge


# ---------------------------------------------------------------------------
# §16 Test 12: Cleanup refuses unmerged dogfood worktrees without force
# ---------------------------------------------------------------------------

def test_safe_to_cleanup_only_when_not_ready(tmp_path):
    state = _make_state(tmp_path, isolation_status="failed")
    Path(state.worktree_workspace).mkdir(parents=True, exist_ok=True)

    assert _safe_to_cleanup_partial_isolation(state) is True


def test_safe_to_cleanup_false_when_ready(tmp_path):
    state = _make_state(tmp_path, isolation_status="ready")
    Path(state.worktree_workspace).mkdir(parents=True, exist_ok=True)

    assert _safe_to_cleanup_partial_isolation(state) is False


# ---------------------------------------------------------------------------
# §16 Test 13: CWD-independent status via _default_runtime_workspace
# ---------------------------------------------------------------------------

def test_default_runtime_workspace_uses_run_id(tmp_path, monkeypatch):
    monkeypatch.setenv("AF_DOGFOOD_ROOT", str(tmp_path))
    rt_ws = _default_runtime_workspace("my-run-123")
    assert "my-run-123" in rt_ws
    assert rt_ws.endswith("runtime")


def test_default_runtime_workspace_cwd_independent(tmp_path, monkeypatch):
    monkeypatch.setenv("AF_DOGFOOD_ROOT", str(tmp_path))
    # Should not depend on CWD
    rt1 = _default_runtime_workspace("run-abc")
    rt2 = _default_runtime_workspace("run-abc")
    assert rt1 == rt2


# ---------------------------------------------------------------------------
# §16 Test 14: MERGE crash recovery (already-ancestor → merged)
# ---------------------------------------------------------------------------

def test_merge_crash_recovery_already_ancestor(tmp_path):
    state = _make_merge_state(tmp_path, dogfood_commit="abc123")
    state.source_workspace = str(tmp_path)

    call_log: list[str] = []

    def _git_stub(args, cwd, **kwargs):
        call_log.append(" ".join(args))
        r = MagicMock()
        r.returncode = 0
        r.stdout = "newhead567"
        if "merge-base" in args and "--is-ancestor" in args:
            r.returncode = 0  # dogfood_commit IS an ancestor
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        merge_dogfood_branch(state)

    assert state.merge_status == "merged"
    assert state.phase == DogfoodPhase.COMPLETE
    # No actual merge command issued (only merge-base check + HEAD)
    assert not any("merge --no-ff" in c for c in call_log)


# ---------------------------------------------------------------------------
# §16 Test 15: git reset --merge used (not merge --abort)
# ---------------------------------------------------------------------------

def test_conflict_check_uses_reset_merge_not_abort(tmp_path):
    state = _make_merge_state(tmp_path)
    state.source_workspace = str(tmp_path)

    call_log: list[str] = []

    def _git_stub(args, cwd, check=True, **kwargs):
        call_log.append(" ".join(args))
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        if "merge-base" in args and "--is-ancestor" in args:
            r.returncode = 1  # NOT an ancestor → proceed with merge
        elif "status" in args and "--porcelain" in args:
            r.stdout = ""  # clean
        elif "rev-parse" in args:
            r.stdout = state.base_ref
        elif "merge" in args and "--no-commit" in args:
            if check:
                raise subprocess.CalledProcessError(1, "git merge", "", "conflict")
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        merge_dogfood_branch(state)

    assert state.merge_status == "conflict"
    # reset --merge must appear in call log
    assert any("reset --merge" in c for c in call_log)
    # merge --abort must NOT appear
    assert not any("merge --abort" in c for c in call_log)


# ---------------------------------------------------------------------------
# §16 Test 16: prepare_isolated_worktree retries once on GitWorktreeError
# ---------------------------------------------------------------------------

def test_prepare_isolated_worktree_retries_once(tmp_path):
    state = _make_state(tmp_path, isolation_status="pending")
    wt_path = tmp_path / "worktree"
    state.worktree_workspace = str(wt_path)

    attempt_count = {"n": 0}

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        if "status" in args and "--porcelain" in args:
            r.stdout = ""  # clean
        elif "branch" in args and "--show-current" in args:
            r.stdout = "main"
        elif "rev-parse" in args:
            r.stdout = "abc123"
        elif "worktree" in args and "add" in args:
            attempt_count["n"] += 1
            if attempt_count["n"] == 1:
                # Simulate partial creation then failure: create dir so cleanup triggers
                wt_path.mkdir(parents=True, exist_ok=True)
                raise subprocess.CalledProcessError(128, "git worktree add", "", "already exists")
            else:
                # Second attempt succeeds; dir already exists
                pass
        elif "worktree" in args and "remove" in args:
            # Cleanup removes the dir
            import shutil
            if wt_path.exists():
                shutil.rmtree(str(wt_path), ignore_errors=True)
        elif "branch" in args and "-D" in args:
            pass
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        prepare_isolated_worktree(state)

    assert attempt_count["n"] == 2
    assert state.isolation_status == "ready"


# ---------------------------------------------------------------------------
# §16 Test 17: require_plan_triad_pass=False allows merge even when skipped
# ---------------------------------------------------------------------------

def test_merge_policy_triad_pass_not_required(tmp_path):
    state = _make_merge_state(tmp_path)
    # require_plan_triad_pass=False — gate does not check Triad result
    policy = MergePolicy(require_plan_triad_pass=False, mode="auto_policy")

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        if "status" in args:
            r.stdout = ""  # clean
        elif "rev-parse" in args:
            r.stdout = state.base_ref
        elif "merge" in args and "--no-commit" in args:
            pass  # no conflict
        elif "merge" in args and "--no-ff" in args:
            pass
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        ok, reason = _check_merge_policy(state, policy, [])

    # Should not be blocked by Triad gate (gate only blocks if explicitly checked)
    assert ok is True or "triad" not in reason.lower()


# ---------------------------------------------------------------------------
# MergePolicy dataclass defaults
# ---------------------------------------------------------------------------

def test_merge_policy_defaults():
    policy = MergePolicy()
    assert policy.mode == "auto_policy"
    assert policy.require_clean_source is True
    assert policy.allow_source_advanced is False
    assert policy.require_plan_triad_pass is True
    assert policy.require_dogfood_commit is True
    assert ".af_runtime/" in policy.denied_paths


# ---------------------------------------------------------------------------
# run_all with merge_mode="never" completes
# ---------------------------------------------------------------------------

def test_run_all_merge_never_reaches_complete(tmp_path, monkeypatch):
    import core.dogfood as df

    monkeypatch.setattr(df, "_run_interview_phase",
        lambda s, artifact, **kw: artifact or {"goal": "stub"})
    monkeypatch.setattr(df, "_run_research_brief_phase",
        lambda s, artifact: {"questions": []})
    monkeypatch.setattr(df, "_run_research_phase", lambda s, ctx: ctx)
    monkeypatch.setattr(df, "_run_spec_phase",
        lambda s, interview_artifact, research_artifact: {
            "intent": interview_artifact.get("goal", ""), "scope": [],
            "success_criteria": [], "constraints": [], "approval_policy": "",
            "research_findings": [], "supplemental": [], "gaps": [],
            "risk_hints": [], "assumptions": [],
        })
    monkeypatch.setattr(df, "_run_premortem_phase",
        lambda s, spec_dict: {"spec_intent": "", "risks": []})
    monkeypatch.setattr(df, "_run_plan_phase",
        lambda s, spec_dict, premortem_dict, **kw: {
            "intent": "", "steps": [], "completion_criteria": [],
            "approval_points": [], "verification_requirements": [], "unresolved_risks": [],
        })
    monkeypatch.setattr(df, "_run_isolate_phase",
        lambda s: {"isolation_status": "ready"})
    monkeypatch.setattr(df, "_run_implement_phase",
        lambda s, context: {"executed": [], "failures": [], "skipped_no_commands": [], "ok": True})
    monkeypatch.setattr(df, "_run_verify_phase",
        lambda s, context: {"passed": True, "commands_run": [], "failures": []})
    monkeypatch.setattr(df, "_run_finalize_phase",
        lambda s: {"merge_status": "ready"})

    state = run_all(
        "test never", str(tmp_path),
        interview_artifact={"goal": "test never"},
        runtime_workspace=str(tmp_path / "rt"),
        merge_mode="never",
    )
    assert state.phase == DogfoodPhase.COMPLETE
    assert state.merge_status == "never"


# ---------------------------------------------------------------------------
# run_all with merge_mode="manual" does NOT infinite-loop
# ---------------------------------------------------------------------------

def _stub_all_phases(monkeypatch, merge_mode="auto_policy"):
    import core.dogfood as df

    monkeypatch.setattr(df, "_run_interview_phase",
        lambda s, artifact, **kw: artifact or {"goal": "stub"})
    monkeypatch.setattr(df, "_run_research_brief_phase",
        lambda s, artifact: {"questions": []})
    monkeypatch.setattr(df, "_run_research_phase", lambda s, ctx: ctx)
    monkeypatch.setattr(df, "_run_spec_phase",
        lambda s, iv, ra: {
            "intent": iv.get("goal", ""), "scope": [], "success_criteria": [],
            "constraints": [], "approval_policy": "", "research_findings": [],
            "supplemental": [], "gaps": [], "risk_hints": [], "assumptions": [],
        })
    monkeypatch.setattr(df, "_run_premortem_phase",
        lambda s, spec: {"spec_intent": "", "risks": []})
    monkeypatch.setattr(df, "_run_plan_phase",
        lambda s, spec, pm, **kw: {
            "intent": "", "steps": [], "completion_criteria": [],
            "approval_points": [], "verification_requirements": [], "unresolved_risks": [],
        })
    monkeypatch.setattr(df, "_run_isolate_phase",
        lambda s: {"isolation_status": "ready"})
    monkeypatch.setattr(df, "_run_implement_phase",
        lambda s, ctx: {"executed": [], "failures": [], "skipped_no_commands": [], "ok": True})
    monkeypatch.setattr(df, "_run_verify_phase",
        lambda s, ctx: {"passed": True, "commands_run": [], "failures": []})
    monkeypatch.setattr(df, "_run_finalize_phase",
        lambda s: {"merge_status": "ready"})


def test_run_all_merge_manual_terminates(tmp_path, monkeypatch):
    """run_all with merge_mode='manual' must not infinite-loop; exits COMPLETE."""
    import core.dogfood as df
    _stub_all_phases(monkeypatch, merge_mode="manual")
    # _run_merge_phase is NOT mocked — uses the real implementation

    state = run_all(
        "test manual", str(tmp_path),
        interview_artifact={"goal": "test manual"},
        runtime_workspace=str(tmp_path / "rt"),
        merge_mode="manual",
    )
    assert state.phase == DogfoodPhase.COMPLETE
    assert state.merge_status == "ready"   # git merge not performed
    assert state.merged_commit == ""


# ---------------------------------------------------------------------------
# DogfoodState.workspace property backward compat
# ---------------------------------------------------------------------------

def test_workspace_property_returns_source_workspace(tmp_path):
    state = DogfoodState(
        run_id="test",
        task="t",
        phase=DogfoodPhase.PENDING,
        source_workspace=str(tmp_path),
        runtime_workspace=str(tmp_path / "rt"),
    )
    assert state.workspace == str(tmp_path)
    assert state.workspace == state.source_workspace


def test_from_dict_backward_compat_workspace_key(tmp_path):
    data = {
        "run_id": "r1",
        "task": "t",
        "phase": "pending",
        "workspace": str(tmp_path),    # legacy key
        "runtime_workspace": str(tmp_path / "rt"),
    }
    state = DogfoodState.from_dict(data)
    assert state.source_workspace == str(tmp_path)
    assert state.workspace == str(tmp_path)
