"""Tests for core.express_router — §17 Step 18."""
from __future__ import annotations

import pytest

from core.express_router import (
    RouteDecision,
    _PHASES,
    _classify,
    _tokens_found,
    route_task,
)


# ---------------------------------------------------------------------------
# _tokens_found
# ---------------------------------------------------------------------------


def test_tokens_found_case_insensitive():
    assert "status" in _tokens_found("Check STATUS now", ("status",))


def test_tokens_found_substring_match():
    assert "core/" in _tokens_found("update core/dogfood.py", ("core/",))


def test_tokens_found_none_present():
    assert _tokens_found("add a unit test", ("security", "migrate")) == []


def test_tokens_found_multiple_matches():
    found = _tokens_found("investigate and analyze the pipeline", ("research", "investigate", "analyze"))
    assert "investigate" in found
    assert "analyze" in found


# ---------------------------------------------------------------------------
# Self-modifying → dogfood
# ---------------------------------------------------------------------------


def test_core_path_triggers_dogfood():
    d = route_task("update core/triad.py to handle edge cases")
    assert d.mode == "dogfood"


def test_af_spec_triggers_dogfood():
    d = route_task("add core.express_router to af.spec hiddenimports")
    assert d.mode == "dogfood"


def test_master_blueprint_triggers_dogfood():
    d = route_task("sync master_blueprint §3 after the change")
    assert d.mode == "dogfood"


def test_dogfood_keyword_triggers_dogfood():
    d = route_task("run dogfood complete on this task")
    assert d.mode == "dogfood"


def test_self_modifying_keyword_triggers_dogfood():
    d = route_task("this is a self-modifying workflow")
    assert d.mode == "dogfood"


def test_windows_backslash_path_triggers_dogfood():
    """Windows-style path core\\ must normalise to core/ and trigger dogfood."""
    d = route_task(r"modify core\triad.py to handle edge cases")
    assert d.mode == "dogfood"


def test_windows_backslash_path_rationale():
    d = route_task(r"update core\express_router.py")
    assert any("self-mod" in r for r in d.rationale)


def test_dogfood_rationale_contains_signal():
    d = route_task("modify core/planner.py")
    assert any("self-mod" in r for r in d.rationale)


# ---------------------------------------------------------------------------
# Risk / research → full
# ---------------------------------------------------------------------------


def test_risk_token_delete_triggers_full():
    d = route_task("delete all legacy endpoints in the API")
    assert d.mode == "full"


def test_risk_token_security_triggers_full():
    d = route_task("review security of the auth flow")
    assert d.mode == "full"


def test_research_token_investigate_triggers_full():
    d = route_task("investigate why the research router fails on deep mode")
    assert d.mode == "full"


def test_research_token_architecture_triggers_full():
    d = route_task("architecture review for the new pipeline design")
    assert d.mode == "full"


def test_complexity_short_stays_light():
    """Complexity token alone without enough words stays light."""
    d = route_task("build integration")
    assert d.mode == "light"


def test_complexity_long_triggers_full():
    """Complexity token + >= 15 words triggers full."""
    task = (
        "implement a complete end-to-end integration between the research "
        "router and the spec compiler across all pipeline stages"
    )
    d = route_task(task)
    assert d.mode == "full"


def test_full_rationale_contains_signal():
    d = route_task("investigate the failing research pipeline")
    assert any("research" in r for r in d.rationale)


# ---------------------------------------------------------------------------
# Trivial → direct
# ---------------------------------------------------------------------------


def test_status_query_triggers_direct():
    d = route_task("show status")
    assert d.mode == "direct"


def test_version_query_triggers_direct():
    d = route_task("print version")
    assert d.mode == "direct"


def test_trivial_too_long_stays_light():
    """Trivial token with more than 10 words should not be direct."""
    task = "show the current status of all pipeline stages and summarize them all"
    d = route_task(task)
    assert d.mode != "direct"


def test_direct_rationale_contains_trivial():
    d = route_task("help")
    assert any("trivial" in r for r in d.rationale)


def test_helper_word_does_not_trigger_trivial():
    """'helper' must not match 'help' token — word-boundary guard."""
    d = route_task("remove the old helper function")
    assert d.mode != "direct"


def test_blacklist_does_not_trigger_list_token():
    """'blacklist' must not match 'list' token — word-boundary guard."""
    d = route_task("update the blacklist rules")
    assert d.mode != "direct"


def test_complexity_plus_trivial_short_is_not_direct():
    """Complexity token present → trivial branch skipped, even for short text."""
    d = route_task("show pipeline")
    assert d.mode != "direct"


def test_complexity_trivial_combo_does_not_escalate_to_full_if_short():
    """Short complexity+trivial combo (< 15 words) → light, not direct, not full."""
    d = route_task("show pipeline")
    assert d.mode == "light"


# ---------------------------------------------------------------------------
# Default → light
# ---------------------------------------------------------------------------


def test_simple_bug_fix_is_light():
    d = route_task("fix a null pointer bug in utils.py")
    assert d.mode == "light"


def test_empty_task_is_light():
    d = route_task("")
    assert d.mode == "light"


def test_plain_feature_is_light():
    d = route_task("add a unit test for the planner module")
    assert d.mode == "light"


# ---------------------------------------------------------------------------
# force_route override
# ---------------------------------------------------------------------------


def test_force_route_dogfood():
    d = route_task("add a unit test", force_route="dogfood")
    assert d.mode == "dogfood"


def test_force_route_direct():
    d = route_task("investigate the security architecture", force_route="direct")
    assert d.mode == "direct"


def test_force_route_rationale():
    d = route_task("anything", force_route="full")
    assert d.rationale == ["forced:full"]


def test_force_route_invalid_raises():
    with pytest.raises(ValueError, match="force_route must be one of"):
        route_task("task", force_route="unknown")


# ---------------------------------------------------------------------------
# hints parameter
# ---------------------------------------------------------------------------


def test_hints_can_trigger_dogfood():
    d = route_task("update the planner", hints=["core/"])
    assert d.mode == "dogfood"


def test_hints_can_trigger_full():
    d = route_task("update a helper method", hints=["security"])
    assert d.mode == "full"


# ---------------------------------------------------------------------------
# RouteDecision flags per mode
# ---------------------------------------------------------------------------


def test_direct_flags():
    d = route_task("show status")
    assert d.requires_interview is False
    assert d.requires_research is False
    assert d.requires_premortem is False
    assert d.requires_triad is False
    assert d.requires_worktree is False
    assert d.requires_merge is False


def test_light_flags():
    d = route_task("fix a bug in scripts/review_gate.py")
    assert d.requires_interview is True
    assert d.requires_research is False
    assert d.requires_premortem is False
    assert d.requires_triad is False
    assert d.requires_worktree is False
    assert d.requires_merge is False


def test_full_flags():
    d = route_task("investigate why the review pipeline drops metrics")
    assert d.requires_interview is True
    assert d.requires_research is True
    assert d.requires_premortem is True
    assert d.requires_triad is False
    assert d.requires_worktree is False
    assert d.requires_merge is False


def test_dogfood_flags():
    d = route_task("add a feature to core/triad.py")
    assert d.requires_interview is True
    assert d.requires_research is True
    assert d.requires_premortem is True
    assert d.requires_triad is True
    assert d.requires_worktree is True
    assert d.requires_merge is True


# ---------------------------------------------------------------------------
# phases()
# ---------------------------------------------------------------------------


def test_direct_phases():
    d = route_task("show status")
    assert d.phases() == ["implement", "verify"]


def test_light_phases_contains_interview():
    d = route_task("fix a minor bug")
    assert "interview" in d.phases()
    assert "research_brief" not in d.phases()
    assert "isolate" not in d.phases()


def test_full_phases_contains_research():
    d = route_task("analyze the failing test suite coverage gap")
    assert "research_brief" in d.phases()
    assert "premortem" in d.phases()
    assert "isolate" not in d.phases()
    assert "merge" not in d.phases()


def test_dogfood_phases_contains_isolate_and_merge():
    d = route_task("update core/dogfood.py with the new merge policy")
    assert "isolate" in d.phases()
    assert "merge" in d.phases()


def test_phases_returns_copy():
    """Mutating the returned list must not alter the canonical table."""
    d = route_task("show status")
    p = d.phases()
    p.append("injected")
    assert d.phases() == ["implement", "verify"]


# ---------------------------------------------------------------------------
# to_dict()
# ---------------------------------------------------------------------------


def test_to_dict_structure():
    d = route_task("fix a bug in utils.py")
    result = d.to_dict()
    assert "mode" in result
    assert "requires_interview" in result
    assert "requires_research" in result
    assert "requires_premortem" in result
    assert "requires_triad" in result
    assert "requires_worktree" in result
    assert "requires_merge" in result
    assert "rationale" in result
    assert "phases" in result
    assert isinstance(result["phases"], list)
    assert isinstance(result["rationale"], list)
