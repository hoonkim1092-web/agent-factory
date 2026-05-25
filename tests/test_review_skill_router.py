"""Tests for core.review_skill_router — §17 Step 17."""
from __future__ import annotations

import pytest

from core.review_skill_router import (
    ReviewContext,
    ReviewSkillPlan,
    TierSkillProfile,
    _dedup,
    _has_blueprint_impact,
    _is_worktree_work,
    route_review_skills,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _ctx(
    files: list[str],
    tier: int = 2,
    work_kind: str = "feature",
    risk_tokens: list[str] | None = None,
    packaging: bool = False,
    self_mod: bool = False,
) -> ReviewContext:
    return ReviewContext(
        changed_files=files,
        blast_tier=tier,
        work_kind=work_kind,  # type: ignore[arg-type]
        risk_tokens=risk_tokens or [],
        has_packaging_impact=packaging,
        is_self_modifying=self_mod,
    )


# ---------------------------------------------------------------------------
# _has_blueprint_impact
# ---------------------------------------------------------------------------


def test_blueprint_impact_core_file():
    assert _has_blueprint_impact(["core/dogfood.py"])


def test_blueprint_impact_master_blueprint():
    assert _has_blueprint_impact(["Master_Blueprint.md"])


def test_blueprint_impact_af_spec():
    assert _has_blueprint_impact(["af.spec"])


def test_blueprint_impact_scripts_no():
    assert not _has_blueprint_impact(["scripts/blast_radius.py"])


def test_blueprint_impact_docs_no():
    assert not _has_blueprint_impact(["docs/2026-05-21-foo.md"])


def test_blueprint_impact_backslash_normalized():
    assert _has_blueprint_impact(["core\\review_skill_router.py"])


# ---------------------------------------------------------------------------
# _is_worktree_work
# ---------------------------------------------------------------------------


def test_worktree_work_dogfood_kind():
    assert _is_worktree_work(_ctx([], work_kind="dogfood"))


def test_worktree_work_self_modifying():
    assert _is_worktree_work(_ctx([], self_mod=True))


def test_worktree_work_risk_token():
    assert _is_worktree_work(_ctx([], risk_tokens=["worktree"]))


def test_worktree_work_filename_contains_dogfood():
    assert _is_worktree_work(_ctx(["core/dogfood.py"]))


def test_worktree_work_filename_contains_worktree():
    assert _is_worktree_work(_ctx(["tests/test_dogfood_isolation.py"]))


def test_worktree_work_plain_feature_no():
    assert not _is_worktree_work(_ctx(["core/triad.py"], work_kind="feature"))


# ---------------------------------------------------------------------------
# _dedup
# ---------------------------------------------------------------------------


def test_dedup_preserves_order():
    assert _dedup(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]


def test_dedup_empty():
    assert _dedup([]) == []


# ---------------------------------------------------------------------------
# Tier 1 routing
# ---------------------------------------------------------------------------


def test_tier1_only_test_runner():
    plan = route_review_skills(_ctx(["docs/foo.md"], tier=1))
    assert plan.required_tiers == ["af-test-runner"]
    assert set(plan.profiles.keys()) == {"af-test-runner"}


def test_tier1_base_skills_only():
    plan = route_review_skills(_ctx(["docs/foo.md"], tier=1))
    skills = plan.profiles["af-test-runner"].skills
    assert "af-test-runner" in skills
    assert "verification-before-completion" in skills
    assert "af-blueprint-sync" not in skills


def test_tier1_ignores_packaging_flag():
    """Packaging flag must not add tiers on Tier 1."""
    plan = route_review_skills(_ctx(["docs/changelog.md"], tier=1, packaging=True))
    assert plan.required_tiers == ["af-test-runner"]


# ---------------------------------------------------------------------------
# Tier 2 routing — core file (§11.4 reference scenario)
# ---------------------------------------------------------------------------


def test_tier2_core_dogfood_all_tiers():
    """§11.4 example: core/dogfood.py → all three tiers."""
    plan = route_review_skills(_ctx(["core/dogfood.py"], tier=2))
    assert plan.required_tiers == ["af-test-runner", "af-critic", "af-cross-review"]


def test_tier2_core_dogfood_blueprint_sync_on_runner():
    plan = route_review_skills(_ctx(["core/dogfood.py"], tier=2))
    assert "af-blueprint-sync" in plan.profiles["af-test-runner"].skills


def test_tier2_core_dogfood_blueprint_sync_on_critic():
    plan = route_review_skills(_ctx(["core/dogfood.py"], tier=2))
    assert "af-blueprint-sync" in plan.profiles["af-critic"].skills


def test_tier2_core_dogfood_worktree_skills_on_critic():
    plan = route_review_skills(_ctx(["core/dogfood.py"], tier=2))
    critic = plan.profiles["af-critic"].skills
    assert "using-git-worktrees" in critic
    assert "context-degradation" in critic


def test_tier2_core_dogfood_worktree_skills_on_cross():
    plan = route_review_skills(_ctx(["core/dogfood.py"], tier=2))
    cross = plan.profiles["af-cross-review"].skills
    assert "context-degradation" in cross
    assert "using-git-worktrees" in cross


def test_tier2_non_dogfood_no_worktree_skills():
    plan = route_review_skills(_ctx(["core/triad.py"], tier=2, work_kind="feature"))
    assert "using-git-worktrees" not in plan.profiles["af-critic"].skills
    assert "context-degradation" not in plan.profiles["af-cross-review"].skills


# ---------------------------------------------------------------------------
# Tier 2 routing — packaging impact
# ---------------------------------------------------------------------------


def test_tier2_packaging_adds_architecture_to_runner():
    plan = route_review_skills(_ctx(["core/triad.py"], tier=2, packaging=True))
    assert "af-architecture" in plan.profiles["af-test-runner"].skills


def test_tier2_no_packaging_no_architecture_on_runner():
    plan = route_review_skills(_ctx(["core/triad.py"], tier=2))
    # af-architecture already in _BASE_CRITIC but NOT _BASE_TEST_RUNNER
    assert "af-architecture" not in plan.profiles["af-test-runner"].skills


# ---------------------------------------------------------------------------
# Tier 3 routing — extra skills
# ---------------------------------------------------------------------------


def test_tier3_adds_verification_to_critic():
    plan = route_review_skills(_ctx(["scripts/run.py"], tier=3))
    assert "verification-before-completion" in plan.profiles["af-critic"].skills


def test_tier3_adds_context_optimization_to_cross():
    plan = route_review_skills(_ctx(["scripts/run.py"], tier=3))
    cross = plan.profiles["af-cross-review"].skills
    assert "context-optimization" in cross
    assert "multi-agent-patterns" in cross


def test_tier2_does_not_have_tier3_extras():
    plan = route_review_skills(_ctx(["core/triad.py"], tier=2))
    cross = plan.profiles["af-cross-review"].skills
    assert "context-optimization" not in cross
    assert "multi-agent-patterns" not in cross


# ---------------------------------------------------------------------------
# Self-modifying flag
# ---------------------------------------------------------------------------


def test_self_modifying_triggers_worktree_skills_even_without_dogfood_file():
    plan = route_review_skills(_ctx(["core/triad.py"], tier=2, self_mod=True))
    critic = plan.profiles["af-critic"].skills
    assert "using-git-worktrees" in critic
    assert "context-degradation" in critic


def test_self_modifying_cross_review_skills():
    plan = route_review_skills(_ctx(["core/triad.py"], tier=2, self_mod=True))
    cross = plan.profiles["af-cross-review"].skills
    assert "context-degradation" in cross
    assert "using-git-worktrees" in cross


# ---------------------------------------------------------------------------
# Risk tokens
# ---------------------------------------------------------------------------


def test_risk_token_worktree_triggers_worktree_skills():
    plan = route_review_skills(
        _ctx(["scripts/review_gate.py"], tier=3, risk_tokens=["worktree"])
    )
    assert "using-git-worktrees" in plan.profiles["af-critic"].skills


# ---------------------------------------------------------------------------
# Dedup — no duplicate skills in profiles
# ---------------------------------------------------------------------------


def test_no_duplicate_skills_in_tier2_dogfood():
    plan = route_review_skills(
        _ctx(["core/dogfood.py"], tier=2, work_kind="dogfood", self_mod=True)
    )
    for profile in plan.profiles.values():
        assert len(profile.skills) == len(set(profile.skills)), (
            f"Duplicates in {profile.tier}: {profile.skills}"
        )


def test_no_duplicate_skills_in_tier3():
    plan = route_review_skills(
        _ctx(["scripts/run.py"], tier=3, packaging=True, self_mod=True)
    )
    for profile in plan.profiles.values():
        assert len(profile.skills) == len(set(profile.skills))


# ---------------------------------------------------------------------------
# to_dict roundtrip
# ---------------------------------------------------------------------------


def test_to_dict_structure():
    plan = route_review_skills(_ctx(["core/dogfood.py"], tier=2))
    d = plan.to_dict()
    assert "required_tiers" in d
    assert "profiles" in d
    for tier in d["required_tiers"]:
        assert tier in d["profiles"]
        p = d["profiles"][tier]
        assert "tier" in p
        assert "skills" in p
        assert isinstance(p["skills"], list)


def test_tier_profile_to_dict():
    p = TierSkillProfile("af-critic", ["af-code-review", "af-architecture"])
    d = p.to_dict()
    assert d == {"tier": "af-critic", "skills": ["af-code-review", "af-architecture"]}
