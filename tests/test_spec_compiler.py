"""Tests for core.spec_compiler (§17 Step 4)."""
from __future__ import annotations

import pytest

from core.research_brief import ResearchBrief
from core.spec_compiler import CompiledSpec, compile_spec, _detect_gaps, _str_list


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _interview_artifact(extra_brief=None):
    brief = {
        "goal": "Add dogfood loop to AF",
        "scope": ["core/dogfood.py", "run_factory_cli.py"],
        "success_criteria": ["af dogfood complete works end-to-end"],
        "constraints": ["no hardcoded questions", "worktree isolation"],
        "approval_policy": "require_human_for_destructive",
        "research_questions": ["How does AF store state?", "Which components exist?"],
        "risk_hints": ["Blueprint sync required for core/*.py"],
        "assumptions": [{"id": "A1", "statement": "Q → A", "source": "deep_skip", "confidence": "medium"}],
    }
    if extra_brief:
        brief.update(extra_brief)
    return {"task_input": "Add dogfood loop", "project_brief": brief}


def _evidence_bundle():
    return {
        "local_refs": [
            {"title": "AF state storage docs", "content": "AF stores state in JSON files"},
            {"title": "UI flexbox guide", "content": "CSS flexbox for layout grids"},
        ],
        "web_refs": [
            {"title": "worktree tutorial", "content": "git worktree isolation for parallel dev"},
        ],
        "llm_prior": [],
    }


# ---------------------------------------------------------------------------
# compile_spec — basic
# ---------------------------------------------------------------------------

def test_compile_spec_extracts_interview_fields():
    artifact = _interview_artifact()
    spec = compile_spec(artifact, evidence_bundle=None)

    assert spec.intent == "Add dogfood loop to AF"
    assert "core/dogfood.py" in spec.scope
    assert "af dogfood complete works end-to-end" in spec.success_criteria
    assert "no hardcoded questions" in spec.constraints
    assert spec.approval_policy == "require_human_for_destructive"
    assert "Blueprint sync required for core/*.py" in spec.risk_hints
    assert len(spec.assumptions) == 1


def test_compile_spec_no_evidence():
    spec = compile_spec(_interview_artifact(), evidence_bundle=None)
    assert spec.research_findings == []
    assert spec.supplemental == []
    assert spec.gaps == []


def test_compile_spec_to_dict_has_all_keys():
    spec = compile_spec(_interview_artifact(), evidence_bundle=None)
    d = spec.to_dict()
    for key in ("intent", "scope", "success_criteria", "constraints",
                "approval_policy", "research_findings", "supplemental",
                "gaps", "risk_hints", "assumptions"):
        assert key in d


# ---------------------------------------------------------------------------
# compile_spec — with research brief (Step 3 integration)
# ---------------------------------------------------------------------------

def test_compile_spec_splits_evidence_by_brief():
    brief = ResearchBrief(questions=["AF state storage"], risk_hints=["worktree"])
    spec = compile_spec(_interview_artifact(), _evidence_bundle(), research_brief=brief)

    # "AF state storage docs" and "worktree tutorial" should be on-brief
    on_titles = {e["title"] for e in spec.research_findings}
    supp_titles = {e["title"] for e in spec.supplemental}

    assert "AF state storage docs" in on_titles
    assert "worktree tutorial" in on_titles
    assert "UI flexbox guide" in supp_titles


def test_compile_spec_gaps_for_unanswered_questions():
    brief = ResearchBrief(questions=["retry policy details"])
    # evidence has nothing about retry policy
    spec = compile_spec(_interview_artifact(), _evidence_bundle(), research_brief=brief)
    assert "retry policy details" in spec.gaps


def test_compile_spec_no_gap_when_question_answered():
    brief = ResearchBrief(questions=["AF state"])
    spec = compile_spec(_interview_artifact(), _evidence_bundle(), research_brief=brief)
    # "AF state storage docs" has "state" token — should match
    assert spec.gaps == []


def test_compile_spec_empty_brief_no_split():
    brief = ResearchBrief()
    spec = compile_spec(_interview_artifact(), _evidence_bundle(), research_brief=brief)
    assert len(spec.research_findings) == 3  # all evidence on-brief
    assert spec.supplemental == []


# ---------------------------------------------------------------------------
# compile_spec — bare project_brief (no outer wrapper)
# ---------------------------------------------------------------------------

def test_compile_spec_bare_brief_dict():
    bare = {
        "goal": "fix a bug",
        "research_questions": ["What causes the error?"],
        "risk_hints": [],
        "assumptions": [],
    }
    spec = compile_spec(bare, evidence_bundle=None)
    assert spec.intent == "fix a bug"


# ---------------------------------------------------------------------------
# _str_list helper
# ---------------------------------------------------------------------------

def test_str_list_from_list():
    assert _str_list(["a", "b", ""]) == ["a", "b"]


def test_str_list_from_none():
    assert _str_list(None) == []


def test_str_list_from_string():
    assert _str_list("single") == ["single"]


# ---------------------------------------------------------------------------
# _detect_gaps
# ---------------------------------------------------------------------------

def test_detect_gaps_all_answered():
    questions = ["state storage"]
    on_brief = [{"content": "AF state storage in JSON files"}]
    assert _detect_gaps(questions, on_brief) == []


def test_detect_gaps_unanswered():
    questions = ["retry policy limit"]
    on_brief = [{"content": "AF state storage in JSON files"}]
    gaps = _detect_gaps(questions, on_brief)
    assert "retry policy limit" in gaps


def test_detect_gaps_empty_questions():
    assert _detect_gaps([], [{"content": "anything"}]) == []
