"""Tests for core.research_brief (§17 Step 3)."""
from __future__ import annotations

import pytest

from core.research_brief import (
    ResearchBrief,
    build_from_interview,
    split_evidence,
    tag_evidence,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _interview_artifact(research_questions=None, risk_hints=None):
    return {
        "task_input": "build a thing",
        "project_brief": {
            "goal": "build a thing",
            "research_questions": research_questions or [],
            "risk_hints": risk_hints or [],
        },
    }


def _bare_brief(research_questions=None, risk_hints=None):
    """Bare project_brief dict (no outer wrapper)."""
    return {
        "goal": "build a thing",
        "research_questions": research_questions or [],
        "risk_hints": risk_hints or [],
    }


# ---------------------------------------------------------------------------
# build_from_interview
# ---------------------------------------------------------------------------

def test_build_from_interview_full_artifact():
    artifact = _interview_artifact(
        research_questions=["How does AF store state?", "Which components exist?"],
        risk_hints=["core/*.py changes require Blueprint sync"],
    )
    brief = build_from_interview(artifact)
    assert brief.questions == ["How does AF store state?", "Which components exist?"]
    assert brief.risk_hints == ["core/*.py changes require Blueprint sync"]


def test_build_from_interview_bare_dict():
    bare = _bare_brief(research_questions=["What is the retry limit?"])
    brief = build_from_interview(bare)
    assert brief.questions == ["What is the retry limit?"]


def test_build_from_interview_empty_fields():
    artifact = _interview_artifact()
    brief = build_from_interview(artifact)
    assert brief.questions == []
    assert brief.risk_hints == []
    assert brief.is_empty()


def test_build_from_interview_strips_blanks():
    artifact = _interview_artifact(research_questions=["  ", "valid question", ""])
    brief = build_from_interview(artifact)
    assert brief.questions == ["valid question"]


# ---------------------------------------------------------------------------
# tag_evidence
# ---------------------------------------------------------------------------

def test_tag_evidence_matching():
    brief = ResearchBrief(questions=["How does AF store state?"])
    evidence = [
        {"title": "AF state storage docs", "content": "AF stores state in JSON files"},
        {"title": "UI rendering guide", "content": "React components for rendering"},
    ]
    tagged = tag_evidence(evidence, brief)
    assert tagged[0]["on_brief"] is True
    assert tagged[1]["on_brief"] is False


def test_tag_evidence_empty_brief_all_on_brief():
    brief = ResearchBrief()
    evidence = [{"title": "anything", "content": "completely unrelated topic"}]
    tagged = tag_evidence(evidence, brief)
    assert tagged[0]["on_brief"] is True


def test_tag_evidence_does_not_mutate_originals():
    brief = ResearchBrief(questions=["state storage"])
    original = {"title": "state", "content": "some state info"}
    tag_evidence([original], brief)
    assert "on_brief" not in original


# ---------------------------------------------------------------------------
# split_evidence
# ---------------------------------------------------------------------------

def test_split_evidence_separates_correctly():
    brief = ResearchBrief(questions=["worktree isolation"], risk_hints=["packaging impact"])
    evidence = [
        {"title": "worktree setup guide", "content": "git worktree isolation step"},
        {"title": "unrelated UI tip", "content": "CSS flexbox for layout"},
        {"title": "packaging note", "content": "packaging impact on frozen builds"},
    ]
    on_brief, supplemental = split_evidence(evidence, brief)
    assert len(on_brief) == 2
    assert len(supplemental) == 1
    assert supplemental[0]["title"] == "unrelated UI tip"


def test_split_evidence_all_on_brief_when_empty_brief():
    brief = ResearchBrief()
    evidence = [{"content": "x"}, {"content": "y"}]
    on_brief, supplemental = split_evidence(evidence, brief)
    assert len(on_brief) == 2
    assert supplemental == []


def test_split_evidence_preserves_on_brief_false_tag():
    brief = ResearchBrief(questions=["state"])
    evidence = [{"content": "unrelated content about CSS"}]
    _, supplemental = split_evidence(evidence, brief)
    assert supplemental[0]["on_brief"] is False
