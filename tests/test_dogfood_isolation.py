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
    ARTIFACT_MERGE_REPORT,
    DEFAULT_DENIED_PATHS,
    DogfoodPhase,
    DogfoodState,
    GitWorktreeError,
    MergePolicy,
    _artifact_path,
    _check_merge_policy,
    _cleanup_partial_isolation,
    _default_runtime_workspace,
    _default_worktree_workspace,
    _dirty_files,
    _dogfood_root,
    _run_isolate_phase,
    _run_merge_phase,
    _safe_to_cleanup_partial_isolation,
    atomic_write_json,
    block_run,
    build_merge_policy,
    create_run,
    VALID_MERGE_MODES,
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
        elif "status" in args and "--porcelain" in args:
            r.stdout = " M core/utils.py\n"
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            r.stdout = "real content change"  # not CRLF-only
        elif "diff" in args and "--name-only" in args and ".." in " ".join(args):
            r.stdout = "core/utils.py"
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
        elif "status" in args and "--porcelain" in args:
            r.stdout = " M core/utils.py\n?? run_output.txt\n"
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            r.stdout = "real content change"  # not CRLF-only
        elif "diff" in args and "--name-only" in args and ".." in " ".join(args):
            r.stdout = "core/utils.py"
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
        elif "status" in args and "--porcelain" in args:
            r.stdout = " M core/utils.py\n M Master_Blueprint.md\n M docs/code_review/code-review.md\n"
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            r.stdout = "real content change"  # not CRLF-only
        elif "diff" in args and "--name-only" in args and ".." in " ".join(args):
            r.stdout = "core/utils.py\nMaster_Blueprint.md\ndocs/code_review/code-review.md"
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


def test_finalize_stages_review_artifacts_under_docs_reviews(tmp_path):
    """docs/reviews/<ts>-<stem>-code-review.md (dynamic filename) must be staged,
    not flagged as a scope_violation. core/review_report.py writes these during a
    run, but their timestamped names cannot match the exact-path plan allowlist.

    Uses a SKILLS-ONLY plan and forces final_docs_synced=[] so the staging is
    proven to be unconditional (a plan exists) — not reached via the core/ fallback
    nor via a doc sync. This keeps FINALIZE symmetric with build_merge_policy's
    `if allowed:` gate so the merge gate never rejects what FINALIZE stages."""
    import json
    state = _make_state(tmp_path, phase=DogfoodPhase.FINALIZE, isolation_status="ready")
    state.worktree_workspace = str(tmp_path / "worktree")
    Path(state.worktree_workspace).mkdir(parents=True, exist_ok=True)
    state.base_ref = "base001"

    plan = {"steps": [{"id": "S1", "artifacts": ["skills/dp/skill.py"], "tests_required": []}]}
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    state.plan_path = str(plan_file)

    review_doc = "docs/reviews/2026-06-01-120000-skill-code-review.md"
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
        elif "status" in args and "--porcelain" in args:
            # skills/dp/skill.py tracked-modified; review doc is untracked (??).
            # _dirty_files(include_untracked=False) adds --untracked-files=no, so
            # distinguish the two calls — the review doc must be genuinely untracked
            # (exercises the "untracked → always real" branch, no CRLF filtering).
            if "--untracked-files=no" in args:
                r.stdout = " M skills/dp/skill.py\n"
            else:
                r.stdout = f" M skills/dp/skill.py\n?? {review_doc}\n"
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            r.stdout = "real content change"  # not CRLF-only
        elif "diff" in args and "--name-only" in args and ".." in " ".join(args):
            r.stdout = f"skills/dp/skill.py\n{review_doc}"
        elif args[0] == "add":
            staged.append(list(args))
        return r

    # No doc sync ran (final_docs_synced=[]) and the plan has no core/ file, so the
    # docs/reviews exemption cannot come from final_docs_gate — it must be unconditional.
    with patch("core.dogfood._git", side_effect=_git_stub), \
            patch("core.dogfood._run_final_docs_sync", return_value=[]):
        report = finalize_dogfood_result(state)

    staged_flat = " ".join(" ".join(a) for a in staged)
    assert review_doc in staged_flat
    assert "skills/dp/skill.py" in staged_flat
    assert report["scope_violations"] == []


def test_build_merge_policy_allows_docs_reviews_dir(tmp_path):
    """build_merge_policy exposes docs/reviews/ as an allowed directory prefix so
    dogfood-generated review artifacts pass the auto-merge allowed_paths gate."""
    import json
    state = _make_state(tmp_path, phase=DogfoodPhase.MERGE)
    plan = {"steps": [{"id": "S1", "artifacts": ["core/utils.py"], "tests_required": []}]}
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    state.plan_path = str(plan_file)

    policy = build_merge_policy(state)
    assert "docs/reviews/" in policy.allowed_paths

    # Isolate the allowed_paths gate: disable the source-state gates that would
    # otherwise short-circuit before the path check (base_ref/clean-source/commit).
    review_doc = "docs/reviews/2026-06-01-120000-utils-code-review.md"
    path_only = MergePolicy(
        mode="auto_policy",
        require_clean_source=False,
        allow_source_advanced=True,
        require_dogfood_commit=False,
        allowed_paths=policy.allowed_paths,
        denied_paths=policy.denied_paths,
    )
    ok, reason = _check_merge_policy(
        state, path_only,
        changed_files=["core/utils.py", review_doc],
        scope_violations=[],
    )
    assert ok is True, reason
    assert reason == ""


def test_build_merge_policy_skills_only_plan_allows_docs_reviews(tmp_path):
    """REGRESSION (cross-review Finding #2): a skills-only (no core/) plan still
    triggers doc sync (blueprint_updater.TRIGGER_PREFIXES includes skills/), so
    FINALIZE stages docs/reviews artifacts. The merge gate must permit them too —
    otherwise FINALIZE stages a file that auto-merge then rejects."""
    import json
    state = _make_state(tmp_path, phase=DogfoodPhase.MERGE)
    plan = {"steps": [{"id": "S1", "artifacts": ["skills/dp/skill.py"], "tests_required": []}]}
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    state.plan_path = str(plan_file)

    policy = build_merge_policy(state)
    assert "docs/reviews/" in policy.allowed_paths
    assert "Master_Blueprint.md" in policy.allowed_paths

    path_only = MergePolicy(
        mode="auto_policy",
        require_clean_source=False,
        allow_source_advanced=True,
        require_dogfood_commit=False,
        allowed_paths=policy.allowed_paths,
        denied_paths=policy.denied_paths,
    )
    ok, reason = _check_merge_policy(
        state, path_only,
        changed_files=["skills/dp/skill.py",
                       "docs/reviews/2026-06-01-120000-skill-code-review.md"],
        scope_violations=[],
    )
    assert ok is True, reason


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
        elif "status" in args and "--porcelain" in args:
            r.stdout = " M core/utils.py\n?? run_output.txt\n"
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            r.stdout = "real content change"  # not CRLF-only
        elif "diff" in args and "--name-only" in args and ".." in " ".join(args):
            r.stdout = "core/utils.py\nrun_output.txt"
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


def test_check_merge_policy_allowed_path_suffix_sibling_blocks(tmp_path):
    """A file sharing a prefix with an allowed file (e.g. .bak) must NOT pass.

    Regression for the fail-open prefix match: 'core/utils.py.bak'.startswith(
    'core/utils.py') was True, letting out-of-scope siblings through the gate.
    """
    state = _make_merge_state(tmp_path)
    policy = MergePolicy(
        mode="auto_policy",
        allowed_paths=["core/utils.py"],
        require_clean_source=False,
        allow_source_advanced=True,
        require_dogfood_commit=False,
    )

    with patch("core.dogfood._git"):
        ok, reason = _check_merge_policy(
            state, policy, changed_files=["core/utils.py.bak"]
        )

    assert ok is False
    assert "allowed_paths" in reason


def test_check_merge_policy_allowed_path_exact_and_dir_boundary(tmp_path):
    """Exact file match passes; directory entry matches only on a path boundary."""
    state = _make_merge_state(tmp_path)
    policy = MergePolicy(
        mode="auto_policy",
        allowed_paths=["core/utils.py", "docs/"],
        require_clean_source=False,
        allow_source_advanced=True,
        require_dogfood_commit=False,
    )

    with patch("core.dogfood._git"):
        # exact file + file inside allowed dir → pass
        ok_pass, _ = _check_merge_policy(
            state, policy,
            changed_files=["core/utils.py", "docs/code_review/code-review.md"],
        )
        # 'docsX/...' must NOT match the 'docs/' boundary
        ok_fail, reason = _check_merge_policy(
            state, policy, changed_files=["docsX/leak.md"]
        )

    assert ok_pass is True
    assert ok_fail is False
    assert "allowed_paths" in reason


def test_build_merge_policy_empty_mode_raises(tmp_path):
    """build_merge_policy(state, '') must fail closed, not coerce to state default.

    Regression for `mode or state.merge_mode`: an explicit invalid '' silently
    became state.merge_mode (auto_policy). Now '' reaches __post_init__ → ValueError.
    """
    state = _make_merge_state(tmp_path)
    with pytest.raises(ValueError, match="invalid merge mode"):
        build_merge_policy(state, "")


def test_build_merge_policy_none_mode_uses_state_default(tmp_path):
    """mode=None keeps the 'use state default' contract."""
    state = _make_merge_state(tmp_path)
    state.merge_mode = "manual"
    policy = build_merge_policy(state, None)
    assert policy.mode == "manual"


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
        elif "status" in args and "--porcelain" in args:
            r.stdout = " M core/utils.py\n M syncCompyne/foo.py\n"
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            filepath = args[-1]
            # core/utils.py has real changes; syncCompyne/foo.py is CRLF-only
            r.stdout = "" if "syncCompyne" in filepath else "real diff output"
        elif "diff" in args and "--name-only" in args and ".." in " ".join(args):
            r.stdout = "core/utils.py"
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
    # develop_changed_paths populates the allowlist so inv1 doesn't fire first.
    state.develop_changed_paths = ["core/x.py"]

    # Provide a valid merge_report so the missing-report guard is skipped
    report_path = _artifact_path(state, ARTIFACT_MERGE_REPORT)
    atomic_write_json(report_path, {"changed_files": ["core/x.py"], "scope_violations": []})

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
    # denied_paths default is empty; callers apply DEFAULT_DENIED_PATHS explicitly
    assert policy.denied_paths == []
    assert ".af_runtime/" in DEFAULT_DENIED_PATHS
    assert "runtime/" in DEFAULT_DENIED_PATHS
    assert "skills/registry.yaml" in DEFAULT_DENIED_PATHS


# ---------------------------------------------------------------------------
# ISOLATE dirty check: CRLF-only filter
# ---------------------------------------------------------------------------

def test_prepare_isolated_worktree_crlf_only_passes(tmp_path):
    """CRLF-only diff (Windows↔Mac noise) must not block ISOLATE."""
    state = _make_state(tmp_path)

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        if "status" in args and "--porcelain" in args:
            r.stdout = " M agents/README.md\n"  # unstaged modified (porcelain v1: XY + space)
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            r.stdout = ""  # CRLF-only — no real content diff
        elif "branch" in args and "--show-current" in args:
            r.stdout = "main"
        elif "rev-parse" in args:
            r.stdout = "abc1234def5678"
        elif "worktree" in args and "add" in args:
            wt = args[-2] if len(args) >= 3 else cwd
            Path(wt).mkdir(parents=True, exist_ok=True)
        else:
            r.stdout = ""
        return r

    # Should NOT raise GitWorktreeError
    with patch("core.dogfood._git", side_effect=_git_stub):
        prepare_isolated_worktree(state)

    assert state.isolation_status == "ready"


def test_prepare_isolated_worktree_real_dirty_blocks(tmp_path):
    """Real content change (non-CRLF) must still block ISOLATE."""
    state = _make_state(tmp_path)

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        if "status" in args and "--porcelain" in args:
            r.stdout = " M core/dogfood.py\n"  # unstaged modified (porcelain v1: XY + space)
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            r.stdout = "-old line\n+new line\n"  # real content diff
        else:
            r.stdout = ""
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        with pytest.raises(GitWorktreeError, match="dirty"):
            prepare_isolated_worktree(state)


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


# ---------------------------------------------------------------------------
# PR 2 (P0-B) regression: _dirty_files / policy consistency
# ---------------------------------------------------------------------------

def test_dirty_files_returns_tracked_changes(tmp_path):
    """_dirty_files returns tracked dirty files from status --porcelain."""
    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        if "status" in args and "--porcelain" in args:
            r.stdout = " M core/utils.py\n M tests/test_utils.py\n"
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            r.stdout = "real diff"  # not CRLF-only
        else:
            r.stdout = ""
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        files = _dirty_files(str(tmp_path), include_untracked=False, ignore_crlf=False)

    assert set(files) == {"core/utils.py", "tests/test_utils.py"}


def test_dirty_files_crlf_filtered(tmp_path):
    """ignore_crlf=True must drop files where only CRLF differs."""
    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        if "status" in args and "--porcelain" in args:
            r.stdout = " M real_change.py\n M crlf_only.py\n"
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            filepath = args[-1]
            r.stdout = "" if "crlf_only" in filepath else "real diff"
        else:
            r.stdout = ""
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        files = _dirty_files(str(tmp_path), include_untracked=False, ignore_crlf=True)

    assert "crlf_only.py" not in files
    assert "real_change.py" in files


def test_dirty_files_whitespace_not_crlf(tmp_path):
    """Indent/whitespace-only change is NOT filtered — only CR/LF is filtered."""
    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        if "status" in args and "--porcelain" in args:
            r.stdout = " M indented.py\n"
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            # --ignore-cr-at-eol still shows indent change → non-empty
            r.stdout = "-    x = 1\n+        x = 1\n"
        else:
            r.stdout = ""
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        files = _dirty_files(str(tmp_path), include_untracked=False, ignore_crlf=True)

    assert "indented.py" in files


def test_dirty_files_includes_untracked(tmp_path):
    """include_untracked=True must include '??' entries from status --porcelain."""
    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        if "status" in args and "--porcelain" in args:
            if "--untracked-files=no" in args:
                r.stdout = " M tracked.py\n"  # no untracked when flag present
            else:
                r.stdout = " M tracked.py\n?? new_file.py\n"
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            r.stdout = "real diff"
        else:
            r.stdout = ""
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        files_with = _dirty_files(str(tmp_path), include_untracked=True, ignore_crlf=False)
        files_without = _dirty_files(str(tmp_path), include_untracked=False, ignore_crlf=False)

    assert "new_file.py" in files_with
    assert "tracked.py" in files_with
    assert "new_file.py" not in files_without


def test_merge_dirty_check_applies_crlf_filter(tmp_path):
    """_check_merge_policy must NOT block when source has only CRLF-only changes."""
    state = _make_merge_state(tmp_path)

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        if "status" in args and "--porcelain" in args:
            r.stdout = " M agents/README.md\n"  # appears dirty
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            r.stdout = ""  # CRLF-only — no real diff
        elif "rev-parse" in args:
            r.stdout = state.base_ref
        else:
            r.stdout = ""
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        ok, reason = _check_merge_policy(state, MergePolicy(), changed_files=[])

    assert ok is True, f"CRLF-only source should not block merge, got: {reason}"


def test_finalize_untracked_file_not_filtered_as_crlf(tmp_path):
    """Newly created (untracked) files must NOT be dropped by CRLF filter.

    git diff --ignore-cr-at-eol on an untracked file returns empty stdout
    (no index version), which would make _is_crlf_only_diff return True.
    The fix: skip CRLF check for untracked files.
    """
    import json
    state = _make_state(tmp_path, phase=DogfoodPhase.FINALIZE, isolation_status="ready")
    state.worktree_workspace = str(tmp_path / "worktree")
    Path(state.worktree_workspace).mkdir(parents=True, exist_ok=True)
    state.base_ref = "base001"
    state.plan_path = ""  # no plan — stage all

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
        elif "status" in args and "--porcelain" in args:
            if "--untracked-files=no" in args:
                r.stdout = " M core/utils.py\n"  # only tracked
            else:
                r.stdout = " M core/utils.py\n?? new_module.py\n"  # tracked + untracked
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            filepath = args[-1]
            # new_module.py is untracked: git diff returns empty (no index baseline)
            r.stdout = "" if "new_module" in filepath else "real diff"
        elif "diff" in args and "--name-only" in args and ".." in " ".join(args):
            r.stdout = "core/utils.py\nnew_module.py"
        elif args[0] == "add":
            staged.append(list(args))
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        report = finalize_dogfood_result(state)

    # new_module.py (untracked) must NOT be dropped despite empty CRLF diff
    assert any("new_module.py" in " ".join(a) for a in staged)
    assert report["scope_violations"] == []


def test_merge_branch_default_policy_applies_denied_paths(tmp_path):
    """merge_dogfood_branch must apply DEFAULT_DENIED_PATHS when no policy given."""
    state = _make_merge_state(tmp_path)
    state.source_workspace = str(tmp_path)

    # Provide a merge report with a denied path in changed_files
    report_path = _artifact_path(state, ARTIFACT_MERGE_REPORT)
    atomic_write_json(report_path, {
        "changed_files": [".af_runtime/dogfood/state.json"],
        "scope_violations": [],
    })

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        if "merge-base" in args and "--is-ancestor" in args:
            r.returncode = 1  # not already merged
        elif "status" in args and "--porcelain" in args:
            r.stdout = ""  # clean
        elif "rev-parse" in args:
            r.stdout = state.base_ref
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        merge_dogfood_branch(state)  # no policy arg → default applied

    assert state.merge_status == "policy_rejected"
    assert "denied" in state.last_failure


# ---------------------------------------------------------------------------
# Finding 1 — build_merge_policy: auto + manual paths share scope enforcement
# ---------------------------------------------------------------------------

def _write_plan(state, steps):
    import json
    plan_path = Path(state.runtime_workspace) / "plan.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps({"steps": steps}), encoding="utf-8")
    state.plan_path = str(plan_path)
    return plan_path


def test_build_merge_policy_derives_allowed_paths_from_plan(tmp_path):
    """allowed_paths must come from the plan's artifacts + tests_required."""
    state = _make_merge_state(tmp_path)
    _write_plan(state, [
        {"artifacts": ["core/utils.py"], "tests_required": ["tests/test_utils.py"]},
    ])
    policy = build_merge_policy(state)
    assert "core/utils.py" in policy.allowed_paths
    assert "tests/test_utils.py" in policy.allowed_paths
    assert policy.mode == state.merge_mode
    assert ".af_runtime/" in policy.denied_paths


def test_build_merge_policy_no_plan_empty_allowed(tmp_path):
    """No plan_path → allowed_paths empty (denied gate still applied)."""
    state = _make_merge_state(tmp_path)
    state.plan_path = ""
    policy = build_merge_policy(state)
    assert policy.allowed_paths == []


def test_run_merge_phase_auto_enforces_plan_allowed_paths(tmp_path):
    """REGRESSION (Finding 1, High): the auto_policy path must enforce the
    plan-derived allowed_paths. Before build_merge_policy() it constructed a bare
    MergePolicy with empty allowed_paths, silently disabling the scope gate."""
    state = _make_merge_state(tmp_path)
    state.source_workspace = str(tmp_path)
    _write_plan(state, [{"artifacts": ["core/utils.py"], "tests_required": []}])

    # An out-of-scope file made it into the commit — must be rejected on merge.
    report_path = _artifact_path(state, ARTIFACT_MERGE_REPORT)
    atomic_write_json(report_path, {
        "changed_files": ["core/utils.py", "core/sneaky.py"],
        "scope_violations": [],
    })

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        if "merge-base" in args and "--is-ancestor" in args:
            r.returncode = 1  # not already merged
        elif "status" in args and "--porcelain" in args:
            r.stdout = ""  # clean
        elif "rev-parse" in args:
            r.stdout = state.base_ref
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        _run_merge_phase(state, merge_mode="auto_policy")

    assert state.merge_status == "policy_rejected"
    assert "allowed_paths" in state.last_failure
    assert "core/sneaky.py" in state.last_failure


# ---------------------------------------------------------------------------
# Finding 2 — merge_mode enum validation (fail-closed, no auto fallthrough)
# ---------------------------------------------------------------------------

def test_create_run_rejects_invalid_merge_mode(tmp_path):
    with pytest.raises(ValueError):
        create_run("t", str(tmp_path), merge_mode="foo")


def test_merge_policy_rejects_invalid_mode():
    with pytest.raises(ValueError):
        MergePolicy(mode="foo")  # type: ignore[arg-type]


def test_merge_policy_rejects_whitespace_mode():
    """'manual ' (trailing space) must not fall through to auto_policy."""
    with pytest.raises(ValueError):
        MergePolicy(mode="manual ")  # type: ignore[arg-type]


def test_valid_merge_modes_membership():
    assert VALID_MERGE_MODES == frozenset({"auto_policy", "manual", "never"})


# ---------------------------------------------------------------------------
# CRLF fixture 확장 — untracked + all-CRLF edge cases
# ---------------------------------------------------------------------------

def test_dirty_files_untracked_not_crlf_filtered(tmp_path):
    """Untracked files must appear even when ignore_crlf=True.

    git diff --ignore-cr-at-eol on an untracked path returns empty stdout
    (no index version), which would wrongly classify it as CRLF-only.
    _dirty_files must skip the CRLF check for '??' entries.
    """
    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        if "status" in args and "--porcelain" in args:
            # One tracked CRLF-only file + one untracked new file
            r.stdout = " M crlf_only.py\n?? new_file.py\n"
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            # Real git behaviour: untracked file → empty output (no index version)
            r.stdout = ""
        else:
            r.stdout = ""
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        files = _dirty_files(str(tmp_path), include_untracked=True, ignore_crlf=True)

    assert "crlf_only.py" not in files  # filtered out (tracked, CRLF-only)
    assert "new_file.py" in files       # untracked — exempt from CRLF check


def test_dirty_files_all_crlf_returns_empty(tmp_path):
    """When all dirty files are CRLF-only, _dirty_files returns an empty list."""
    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        if "status" in args and "--porcelain" in args:
            r.stdout = " M a.py\n M b.py\n"
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            r.stdout = ""  # both are CRLF-only
        else:
            r.stdout = ""
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        files = _dirty_files(str(tmp_path), include_untracked=False, ignore_crlf=True)

    assert files == []


def test_dirty_files_git_status_failure_raises(tmp_path):
    """git status non-zero exit must raise GitWorktreeError (fail-closed)."""
    from core.dogfood import GitWorktreeError
    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 128  # git: not a repository / fatal error
        r.stdout = ""
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        with pytest.raises(GitWorktreeError):
            _dirty_files(str(tmp_path), include_untracked=False, ignore_crlf=False)


def test_remove_worktree_only_dirty_refuses(tmp_path):
    """_remove_worktree_only must refuse to remove a dirty worktree."""
    from core.dogfood import _remove_worktree_only, DogfoodPhase, DogfoodState

    state = DogfoodState(
        run_id="rw-test",
        task="t",
        phase=DogfoodPhase.BLOCKED,
        source_workspace=str(tmp_path),
        runtime_workspace=str(tmp_path / "rt"),
    )
    wt = tmp_path / "wt"
    wt.mkdir()
    state.worktree_workspace = str(wt)

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        if "status" in args and "--porcelain" in args:
            r.stdout = " M core/utils.py\n"  # dirty: real change
        elif "diff" in args and "--ignore-cr-at-eol" in args:
            r.stdout = "real diff content"  # not CRLF-only
        else:
            r.stdout = ""
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        removed = _remove_worktree_only(state)

    assert removed is False  # must refuse (uncommitted work present)
    assert wt.exists()       # worktree still exists


# ---------------------------------------------------------------------------
# Track 2: autocrlf=false + update-index --refresh after worktree add
# ---------------------------------------------------------------------------

def test_prepare_isolated_worktree_sets_autocrlf_false(tmp_path):
    """After git worktree add, prepare_isolated_worktree must run
    update-index --refresh with -c core.autocrlf=false in the new worktree.

    On Windows with core.autocrlf=true, files with bare \\r characters in their
    committed blobs produce a stale stat cache entry after checkout, making
    git-status report them as ' M' even though blob == working copy.
    Using -c core.autocrlf=false as a one-shot override (not a permanent config
    write) clears the phantom dirty state without polluting the shared source
    repo config (linked worktrees share .git/config).
    """
    state = _make_state(tmp_path)
    git_calls: list[tuple[list, str]] = []

    def _git_stub(args, cwd, **kwargs):
        git_calls.append((list(args), cwd))
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        if "status" in args and "--porcelain" in args:
            r.stdout = ""  # clean
        elif "branch" in args and "--show-current" in args:
            r.stdout = "main"
        elif "rev-parse" in args:
            r.stdout = "abc1234def5678"
        elif "worktree" in args and "add" in args:
            wt = args[-2] if len(args) >= 3 else cwd
            Path(wt).mkdir(parents=True, exist_ok=True)
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        prepare_isolated_worktree(state)

    # update-index --refresh must be called with -c core.autocrlf=false, in the worktree
    refresh_calls = [
        (a, c) for a, c in git_calls
        if "update-index" in a and "--refresh" in a
    ]
    assert refresh_calls, "Expected git update-index --refresh to be called"
    refresh_args, refresh_cwd = refresh_calls[0]
    assert refresh_cwd == state.worktree_workspace, (
        "update-index --refresh must run in the worktree"
    )
    # -c core.autocrlf=false must be the inline override (not a separate config write)
    assert "-c" in refresh_args and "core.autocrlf=false" in refresh_args, (
        "update-index must use -c core.autocrlf=false inline override"
    )

    # There must be NO permanent 'git config core.autocrlf' call at all
    config_writes = [
        (a, c) for a, c in git_calls
        if "config" in a and "core.autocrlf" in a
    ]
    assert config_writes == [], (
        "git config core.autocrlf must NOT be called (use -c inline override instead)"
    )

    assert state.isolation_status == "ready"


def test_prepare_isolated_worktree_source_repo_autocrlf_unchanged(tmp_path):
    """autocrlf fix must NOT permanently write to any git config (source or worktree).

    Linked worktrees share the parent repo's .git/config, so a bare
    'git config core.autocrlf false' run from the worktree directory would
    silently overwrite the source repo's setting.  The fix uses -c inline
    override on update-index only — no permanent config write anywhere.
    """
    state = _make_state(tmp_path)
    all_config_autocrlf_writes: list[tuple[list, str]] = []

    def _git_stub(args, cwd, **kwargs):
        # Catch any permanent 'git config core.autocrlf ...' call regardless of cwd
        if "config" in args and "core.autocrlf" in args:
            all_config_autocrlf_writes.append((list(args), cwd))
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        if "status" in args and "--porcelain" in args:
            r.stdout = ""
        elif "branch" in args and "--show-current" in args:
            r.stdout = "main"
        elif "rev-parse" in args:
            r.stdout = "abc1234def5678"
        elif "worktree" in args and "add" in args:
            wt = args[-2] if len(args) >= 3 else cwd
            Path(wt).mkdir(parents=True, exist_ok=True)
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        prepare_isolated_worktree(state)

    assert all_config_autocrlf_writes == [], (
        "git config core.autocrlf must NOT be called anywhere — "
        "use -c inline override on update-index instead"
    )


def test_is_crlf_only_diff_doubled_cr_treated_as_noise(tmp_path):
    """Secondary check: a file that differs from HEAD only in bare \\r chars
    (doubled-CR: \\r\\r\\n) must be classified as CRLF-only noise.

    --ignore-cr-at-eol misses doubled-CR because git only strips the final \\r
    before \\n; extra bare \\r's appear as content changes.  The secondary
    byte-level comparison (strip all \\r, compare) must catch these.

    The blob is read via _git_bytes (text=False) so Python's universal-newline
    conversion does not silently turn \\r\\r\\n into \\n\\n before the \\r-strip,
    which was the original bug causing a false mismatch.
    """
    from core.dogfood import _is_crlf_only_diff

    # Working copy has normal CRLF (\r\n)
    wc_file = tmp_path / "doubled_cr.md"
    wc_file.write_bytes(b"# Title\r\nLine two\r\n")

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        if "diff" in args and "--ignore-cr-at-eol" in args:
            # --ignore-cr-at-eol still shows diff for doubled-CR
            r.stdout = "-# Title\n\n+# Title\n"
        return r

    def _git_bytes_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        if "show" in args:
            # Blob has doubled-CR: \r\r\n  — raw bytes, no newline conversion
            r.stdout = b"# Title\r\r\nLine two\r\r\n"
        else:
            r.stdout = b""
        return r

    with patch("core.dogfood._git", side_effect=_git_stub), \
         patch("core.dogfood._git_bytes", side_effect=_git_bytes_stub):
        result = _is_crlf_only_diff("doubled_cr.md", str(tmp_path))

    assert result is True, "doubled-CR file should be classified as CRLF-only noise"


def test_is_crlf_only_diff_real_content_change_not_noise(tmp_path):
    """Secondary check must NOT classify a real content change as CRLF-only."""
    from core.dogfood import _is_crlf_only_diff

    wc_file = tmp_path / "changed.md"
    wc_file.write_bytes(b"# New Title\r\nLine two\r\n")

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        if "diff" in args and "--ignore-cr-at-eol" in args:
            r.stdout = "-# Old Title\n+# New Title\n"  # real content change
        return r

    def _git_bytes_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        if "show" in args:
            r.stdout = b"# Old Title\r\nLine two\r\n"  # different content — raw bytes
        else:
            r.stdout = b""
        return r

    with patch("core.dogfood._git", side_effect=_git_stub), \
         patch("core.dogfood._git_bytes", side_effect=_git_bytes_stub):
        result = _is_crlf_only_diff("changed.md", str(tmp_path))

    assert result is False, "real content change must NOT be classified as CRLF-only"


def test_is_crlf_only_diff_standard_crlf_still_works(tmp_path):
    """Primary path (--ignore-cr-at-eol returns empty) must still work unchanged."""
    from core.dogfood import _is_crlf_only_diff

    wc_file = tmp_path / "normal_crlf.md"
    wc_file.write_bytes(b"Line one\r\nLine two\r\n")

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        if "diff" in args and "--ignore-cr-at-eol" in args:
            r.stdout = ""  # standard CRLF → ignored by --ignore-cr-at-eol
        return r

    with patch("core.dogfood._git", side_effect=_git_stub):
        result = _is_crlf_only_diff("normal_crlf.md", str(tmp_path))

    assert result is True, "standard CRLF diff should still be classified as noise"


# ---------------------------------------------------------------------------
# Fix ① regression: _is_crlf_only_diff secondary check uses raw bytes
# (no universal-newline conversion that would hide doubled-CR)
# ---------------------------------------------------------------------------

def test_is_crlf_only_diff_doubled_cr_raw_bytes_comparison(tmp_path):
    """_git_bytes is called for the blob read (not _git with text=True).

    Regression guard: if _git (text=True) were used instead of _git_bytes,
    Python's universal-newline mode would convert \\r\\r\\n → \\n\\n before
    the .replace(b"\\r",...) strip, making the stripped blob look like \\n\\n
    while the working-copy strip gives \\n — a false mismatch → False (real
    change).  The fix reads via _git_bytes so \\r\\r\\n stays \\r\\r\\n until
    we explicitly strip all \\r, leaving \\n on both sides → True (CRLF-only).
    """
    from core.dogfood import _is_crlf_only_diff

    # Working copy: standard \r\n (after CRLF normalisation)
    wc_file = tmp_path / "doubled_cr_raw.md"
    wc_file.write_bytes(b"hello\r\nworld\r\n")

    git_bytes_called = {"show": False}

    def _git_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        # Primary check: non-empty diff → secondary check triggered
        r.stdout = "-old\n+new\n" if "diff" in args else ""
        return r

    def _git_bytes_stub(args, cwd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        if "show" in args:
            git_bytes_called["show"] = True
            # Blob has doubled-CR: \r\r\n — raw bytes as git would deliver them
            r.stdout = b"hello\r\r\nworld\r\r\n"
        else:
            r.stdout = b""
        return r

    with patch("core.dogfood._git", side_effect=_git_stub), \
         patch("core.dogfood._git_bytes", side_effect=_git_bytes_stub):
        result = _is_crlf_only_diff("doubled_cr_raw.md", str(tmp_path))

    assert git_bytes_called["show"], "_git_bytes must be called for blob read (not _git)"
    # blob b"hello\r\r\nworld\r\r\n".replace(b"\r",b"") == b"hello\nworld\n"
    # wc   b"hello\r\nworld\r\n"    .replace(b"\r",b"") == b"hello\nworld\n"
    assert result is True, (
        "doubled-CR blob vs CRLF working copy must be CRLF-only after \\r strip"
    )


# ---------------------------------------------------------------------------
# Fix ② regression: prepare_isolated_worktree does not permanently write
# to any .git/config (real git repo integration test)
# ---------------------------------------------------------------------------

def test_prepare_isolated_worktree_no_permanent_config_change_real_git(tmp_path):
    """Integration: prepare_isolated_worktree must not alter source repo's git config.

    Creates a real git repo + worktree, runs prepare_isolated_worktree, then
    asserts core.autocrlf in the source repo is unchanged.  This catches the
    linked-worktree config pollution bug: 'git config core.autocrlf false' run
    from a worktree directory writes to the shared .git/config, silently
    overwriting the source repo's setting.
    """
    import shutil

    # Skip if git is not available
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("git not available")

    # Create a minimal real git repo
    src = tmp_path / "src_repo"
    src.mkdir()
    subprocess.run(["git", "init", str(src)], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(src), "config", "user.email", "test@test.com"],
                   capture_output=True, check=True)
    subprocess.run(["git", "-C", str(src), "config", "user.name", "Test"],
                   capture_output=True, check=True)
    # Set a known autocrlf value we can check afterward
    subprocess.run(["git", "-C", str(src), "config", "core.autocrlf", "input"],
                   capture_output=True, check=True)
    # Create an initial commit so HEAD exists
    readme = src / "README.md"
    readme.write_text("hello\n")
    subprocess.run(["git", "-C", str(src), "add", "README.md"],
                   capture_output=True, check=True)
    subprocess.run(["git", "-C", str(src), "commit", "-m", "init"],
                   capture_output=True, check=True)

    # Build a DogfoodState pointing at the real repo
    from core.dogfood import create_run, prepare_isolated_worktree
    wt_path = tmp_path / "dogfood_wt"
    state = create_run(
        "test no-config-pollution",
        str(src),
        run_id="cfg-test-001",
        runtime_workspace=str(tmp_path / ".runtime"),
    )
    state.worktree_workspace = str(wt_path)
    state.dogfood_branch = "dogfood/cfg-test-001"

    try:
        prepare_isolated_worktree(state)
    finally:
        # Always clean up the worktree and branch
        subprocess.run(
            ["git", "-C", str(src), "worktree", "remove", "--force", str(wt_path)],
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(src), "branch", "-D", "dogfood/cfg-test-001"],
            capture_output=True,
        )

    # Verify source repo's core.autocrlf was not changed
    result = subprocess.run(
        ["git", "-C", str(src), "config", "core.autocrlf"],
        capture_output=True, text=True,
    )
    assert result.stdout.strip() == "input", (
        f"source repo core.autocrlf was altered by prepare_isolated_worktree: "
        f"got {result.stdout.strip()!r}, expected 'input'"
    )
