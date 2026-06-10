"""Test-first invariants for the dogfood = self-modification safe container
realignment (Option 2).

Design: docs/2026-06-02-dogfood-pipeline-realignment.md §7 (inv1~inv5), §8 step 0.

These are written BEFORE implementation (test-first). Per the design, the
realignment is locked by executable invariants — not by an LLM re-review —
because the codex MCP bridge is unavailable (re-review = self-review), so the
fail-open / fail-closed contracts are *regression targets*, not debate points.

Expected state at authoring time (step 0): ALL of these FAIL (red).
  - inv1/inv2/inv3 fail because the current code is fail-OPEN / retries.
  - inv4/inv5 error because DogfoodPhase.DEVELOP + the pipeline-injection seam
    (step 1~2) do not exist yet.

inv1 = merge safety hole, inv5 = isolation safety hole — the two core axes.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import core.dogfood as df
from core.dogfood import (
    DogfoodPhase,
    DogfoodState,
    MergePolicy,
    _check_merge_policy,
    run_phase,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mk(
    tmp_path: Path,
    phase: DogfoodPhase = DogfoodPhase.PENDING,
    *,
    run_id: str = "realign-test-001",
) -> DogfoodState:
    return DogfoodState(
        run_id=run_id,
        task="add a small pure function to core/utils.py + tests",
        phase=phase,
        source_workspace=str(tmp_path),
        runtime_workspace=str(tmp_path / ".runtime"),
    )


class _FakePipeline:
    """Stand-in for ProjectPipeline injected into dogfood DEVELOP (step 1~2).

    Records the workspace it was told to develop in and a snapshot of the
    isolation env vars that were active *during* the call, so inv4/inv5 can
    assert the DEVELOP phase runs the real engine inside the worktree under
    the reused F12/self-run guards.
    """

    _ISO_ENV_KEYS = ("AF_DISABLE_REGISTRY_WRITE", "AF_SELF_RUN", "AGENT_PROJECT_ROOT", "AF_SKIP_REVIEW_GATE")

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.run_calls: list[dict] = []
        self.env_during: dict[str, str | None] = {}

    def run(
        self,
        task_input: str,
        workspace: str,
        runtime_workspace: str | None = None,
        **kwargs: object,
    ) -> dict:
        self.run_calls.append(
            {
                "task_input": task_input,
                "workspace": workspace,
                "runtime_workspace": runtime_workspace,
            }
        )
        self.env_during = {k: os.environ.get(k) for k in self._ISO_ENV_KEYS}
        # Simulate the engine's research/prepare having run.
        return {
            "ok": not self.fail,
            "reason": "blocked" if self.fail else "completed",
            "changed_files": [] if self.fail else ["core/utils.py"],
        }


# ---------------------------------------------------------------------------
# inv1 — merge fail-closed: empty allowlist + changed files => REJECT
# (current code is fail-OPEN at _check_merge_policy `if policy.allowed_paths:`)
# ---------------------------------------------------------------------------

def test_inv1_empty_allowlist_with_changes_fails_closed(tmp_path):
    state = _mk(tmp_path, phase=DogfoodPhase.MERGE)
    # Neutralise every gate *except* the allowed-path gate so it is the
    # deciding factor (no git calls: source-advanced + clean-source off).
    policy = MergePolicy(
        mode="manual",
        require_clean_source=False,
        allow_source_advanced=True,
        require_dogfood_commit=False,
        allowed_paths=[],          # <- no plan-derived allowlist
        denied_paths=[],
    )

    ok, reason = _check_merge_policy(state, policy, changed_files=["core/utils.py"])

    assert ok is False, (
        "inv1: an empty allowlist with changed files must FAIL CLOSED "
        "(deny-all), not fail open. Currently the allowed-path gate is "
        "skipped when allowed_paths is empty."
    )


# ---------------------------------------------------------------------------
# inv2 — VERIFY fail-closed: placeholder (# TODO / empty) commands are not
# effective verification. Must reuse _is_e2e_missing semantics, not len==0.
# ---------------------------------------------------------------------------

def test_inv2_placeholder_verify_commands_fail_closed(tmp_path, monkeypatch):
    state = _mk(tmp_path, phase=DogfoodPhase.VERIFY)
    runner = MagicMock(return_value=(True, "ok"))
    monkeypatch.setattr(df, "_command_runner", runner)

    plan_dict = {
        "steps": [{"id": "s1"}],
        # All "commands" are placeholders -> no effective verification exists.
        "verification_requirements": ["# TODO add a real test", "   "],
    }

    result = df._run_verify_phase(state, {"plan_dict": plan_dict})

    assert result["passed"] is False, (
        "inv2: a plan whose only verification commands are # TODO/empty has no "
        "completion proof -> VERIFY must fail closed (reuse _is_e2e_missing), "
        "not execute the placeholder as a real check."
    )
    runner.assert_not_called()  # placeholders must be filtered, never executed


# ---------------------------------------------------------------------------
# inv3 — no auto-retry in pipeline (DEVELOP) mode: a failed VERIFY maps to
# BLOCK, not retry. FSALoop (inside the pipeline) owns self-correction; a
# dogfood-level retry is duplicate and its reset destroys FSALoop learning.
# ---------------------------------------------------------------------------

def test_inv3_failed_verify_blocks_without_retry(tmp_path):
    state = _mk(tmp_path, phase=DogfoodPhase.REVIEW)
    state.attempts = 0  # current code would return "retry" while attempts < MAX

    decision = df._run_review_phase(
        state,
        {"verify_result": {"passed": False, "failures": ["pytest failed"]}},
    )

    assert decision["decision"] == "block", (
        "inv3: in the realigned (Option 2) machine the pipeline's FSALoop owns "
        "retry; a dogfood-level failed verify must BLOCK + report, never loop "
        "back to re-implement (blind re-run forbidden)."
    )


# ---------------------------------------------------------------------------
# inv4 — INTERVIEW removed, pipeline research still runs: the DEVELOP phase
# delegates to the injected ProjectPipeline inside the worktree, which runs
# prepare()/research (project_pipeline.py:725 path).
# ---------------------------------------------------------------------------

def test_inv4_develop_runs_pipeline_research_in_worktree(tmp_path, monkeypatch):
    from core.right_sized_router import RouteDecision, _FULL_STAGES

    monkeypatch.setattr(
        "core.right_sized_router.classify",
        lambda *a, **kw: RouteDecision(
            isolation="worktree",
            required_stages=list(_FULL_STAGES),
            review_depth="deep",
            confidence=0.0,
            reason="test-stub",
            source="fallback",
        ),
    )

    state = _mk(tmp_path, phase=DogfoodPhase.DEVELOP)
    state.worktree_workspace = str(tmp_path / "worktree")
    state.isolation_status = "ready"
    fake = _FakePipeline()

    run_phase(state, project_pipeline=fake)

    assert len(fake.run_calls) == 1, (
        "inv4: DEVELOP must invoke the injected pipeline exactly once "
        "(research/evidence runs there now that INTERVIEW/RESEARCH are removed)."
    )
    assert fake.run_calls[0]["workspace"] == state.worktree_workspace, (
        "inv4: the pipeline must develop inside the isolated worktree, not the "
        "source workspace."
    )


# ---------------------------------------------------------------------------
# inv5 — isolation env containment: DEVELOP sets the reused F12/self-run guards
# (AF_DISABLE_REGISTRY_WRITE=1, AF_SELF_RUN=1, AGENT_PROJECT_ROOT=worktree)
# around the pipeline call and restores them after (try/finally). No new env
# var is introduced; reads stay global, writes are confined.
# ---------------------------------------------------------------------------

def test_inv5_develop_confines_writes_via_reused_guards(tmp_path, monkeypatch):
    from core.right_sized_router import RouteDecision, _FULL_STAGES

    monkeypatch.setattr(
        "core.right_sized_router.classify",
        lambda *a, **kw: RouteDecision(
            isolation="worktree",
            required_stages=list(_FULL_STAGES),
            review_depth="deep",
            confidence=0.0,
            reason="test-stub",
            source="fallback",
        ),
    )

    state = _mk(tmp_path, phase=DogfoodPhase.DEVELOP)
    worktree = str(tmp_path / "worktree")
    state.worktree_workspace = worktree
    state.isolation_status = "ready"
    fake = _FakePipeline()

    before = {k: os.environ.get(k) for k in _FakePipeline._ISO_ENV_KEYS}

    run_phase(state, project_pipeline=fake)

    # Guards active DURING the pipeline call.
    assert fake.env_during["AF_DISABLE_REGISTRY_WRITE"] == "1", (
        "inv5: registry/workflow writes must be globally blocked during DEVELOP "
        "(reuse F12 AF_DISABLE_REGISTRY_WRITE)."
    )
    assert fake.env_during["AF_SELF_RUN"] == "1", (
        "inv5: skill reads must be scoped to the project root during DEVELOP "
        "(reuse AF_SELF_RUN)."
    )
    assert fake.env_during["AGENT_PROJECT_ROOT"] == worktree, (
        "inv5: file edits must be routed into the worktree (AGENT_PROJECT_ROOT"
        " = worktree) so the merge gate is the only escape path."
    )
    assert fake.env_during["AF_SKIP_REVIEW_GATE"] == "1", (
        "inv5: worktree commits must not trigger the source-repo review-gate "
        "pre-commit hook (AF_SKIP_REVIEW_GATE=1 during DEVELOP)."
    )

    # Guards RESTORED after DEVELOP (no env leak into the rest of the process).
    after = {k: os.environ.get(k) for k in _FakePipeline._ISO_ENV_KEYS}
    assert after == before, (
        "inv5: DEVELOP must restore the prior isolation env via try/finally; "
        "it must not leak AF_*/AGENT_PROJECT_ROOT into the surrounding process."
    )
