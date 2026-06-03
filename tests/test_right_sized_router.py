"""Tests for core.right_sized_router — §5.1 (9 cases, test-first RED→GREEN)."""
from __future__ import annotations

import pytest
import core.right_sized_router as rsr
from core.right_sized_router import (
    RouteDecision,
    LIGHT_STAGES,
    STAGE_VOCAB,
    classify,
    _fallback_decision,
    _apply_safety_floors,
    _LIGHT_CONFIDENCE_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Stub helper
# ---------------------------------------------------------------------------

class _StubLLM:
    """Injects a fixed response or exception into _router_llm."""

    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc

    def generate_json(self, prompt, output_schema=None):
        if self._exc is not None:
            raise self._exc
        return self._response


def _stub(response=None, exc=None):
    return _StubLLM(response=response, exc=exc)


# ---------------------------------------------------------------------------
# R-LIGHT  — high-confidence light subset → is_light() True
# ---------------------------------------------------------------------------

def test_r_light(monkeypatch, tmp_path):
    monkeypatch.setattr(rsr, "_router_llm", _stub({
        "isolation": "source",
        "required_stages": ["plan", "implement", "test"],
        "review_depth": "none",
        "confidence": 0.9,
        "reason": "leaf function, Tier2 only",
    }))
    # scripts/utils.py is Tier2 → floor should not fire
    decision = classify("add helper to scripts/utils.py", str(tmp_path),
                        changed_files=["scripts/utils.py"])
    assert decision.is_light() is True
    assert decision.floors_applied == []
    assert decision.source == "llm"


# ---------------------------------------------------------------------------
# R-FULL-STAGE — design in required_stages → not light
# ---------------------------------------------------------------------------

def test_r_full_stage(monkeypatch, tmp_path):
    monkeypatch.setattr(rsr, "_router_llm", _stub({
        "isolation": "worktree",
        "required_stages": ["design", "plan", "implement", "test"],
        "review_depth": "standard",
        "confidence": 0.9,
        "reason": "design needed",
    }))
    decision = classify("refactor core architecture", str(tmp_path),
                        changed_files=["scripts/utils.py"])
    assert decision.is_light() is False


# ---------------------------------------------------------------------------
# R-LOWCONF — confidence 0.5, light subset → not light (full)
# ---------------------------------------------------------------------------

def test_r_lowconf(monkeypatch, tmp_path):
    monkeypatch.setattr(rsr, "_router_llm", _stub({
        "isolation": "source",
        "required_stages": ["plan", "implement", "test"],
        "review_depth": "none",
        "confidence": 0.5,
        "reason": "not sure",
    }))
    decision = classify("add func to scripts/utils.py", str(tmp_path),
                        changed_files=["scripts/utils.py"])
    assert decision.confidence < _LIGHT_CONFIDENCE_THRESHOLD
    assert decision.is_light() is False


# ---------------------------------------------------------------------------
# R-FLOOR-TIER3 — Tier3 scope → design/review/cross_review forced, not light
# ---------------------------------------------------------------------------

def test_r_floor_tier3(monkeypatch, tmp_path):
    # blast_radius.classify_path("scripts/review_gate.py") == Tier3
    monkeypatch.setattr(rsr, "_router_llm", _stub({
        "isolation": "source",
        "required_stages": ["plan", "implement", "test"],
        "review_depth": "none",
        "confidence": 0.9,
        "reason": "looks simple",
    }))
    decision = classify("update scripts/review_gate.py", str(tmp_path),
                        changed_files=["scripts/review_gate.py"])
    assert decision.is_light() is False
    assert any(s in decision.required_stages for s in ("design", "review", "cross_review"))
    assert len(decision.floors_applied) > 0
    assert "blast_radius_tier3" in decision.floors_applied[0]


# ---------------------------------------------------------------------------
# R-FLOOR-SELFMOD — self-mod workspace + core/ scope → isolation→worktree
# ---------------------------------------------------------------------------

def test_r_floor_selfmod(monkeypatch, tmp_path):
    # core/ prefix in changed_files triggers self-mod detection (workspace path ignored)
    import os
    ws = str(tmp_path / "agent-factory")
    os.makedirs(ws, exist_ok=True)
    monkeypatch.setattr(rsr, "_router_llm", _stub({
        "isolation": "source",
        "required_stages": ["plan", "implement", "test"],
        "review_depth": "none",
        "confidence": 0.9,
        "reason": "simple",
    }))
    decision = classify("add func to core/foo.py", ws,
                        changed_files=["core/foo.py"])
    assert decision.isolation == "worktree"
    assert any("self_mod" in f for f in decision.floors_applied)


# ---------------------------------------------------------------------------
# R-FB-EMPTY — stub returns {} → fallback
# ---------------------------------------------------------------------------

def test_r_fb_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(rsr, "_router_llm", _stub({}))
    decision = classify("add func to scripts/utils.py", str(tmp_path),
                        changed_files=["scripts/utils.py"])
    assert decision.source == "fallback"
    assert set(STAGE_VOCAB) == set(decision.required_stages)
    assert decision.isolation == "worktree"


# ---------------------------------------------------------------------------
# R-FB-EXC — stub raises exception → fallback with reason
# ---------------------------------------------------------------------------

def test_r_fb_exc(monkeypatch, tmp_path):
    monkeypatch.setattr(rsr, "_router_llm", _stub(exc=RuntimeError("boom")))
    decision = classify("add func to scripts/utils.py", str(tmp_path),
                        changed_files=["scripts/utils.py"])
    assert decision.source == "fallback"
    assert "boom" in decision.reason


# ---------------------------------------------------------------------------
# R-FB-BADSCHEMA — unknown isolation value → fallback
# ---------------------------------------------------------------------------

def test_r_fb_badschema(monkeypatch, tmp_path):
    monkeypatch.setattr(rsr, "_router_llm", _stub({
        "isolation": "banana",
        "required_stages": ["plan"],
        "review_depth": "none",
        "confidence": 0.9,
        "reason": "bad",
    }))
    decision = classify("add func to scripts/utils.py", str(tmp_path),
                        changed_files=["scripts/utils.py"])
    assert decision.source == "fallback"


# ---------------------------------------------------------------------------
# R-FB-NOSCOPE — scope=[] → conservative fallback (LLM not called)
# ---------------------------------------------------------------------------

def test_r_fb_noscope(monkeypatch, tmp_path):
    # LLM stub is installed but must NOT be called when scope is empty
    monkeypatch.setattr(rsr, "_router_llm", _stub({
        "isolation": "source",
        "required_stages": ["plan", "implement", "test"],
        "review_depth": "none",
        "confidence": 0.9,
        "reason": "no scope",
    }))
    decision = classify("add geometric_mean", str(tmp_path), changed_files=[])
    # Empty scope must always fall back conservatively
    assert decision.source == "fallback"
    assert decision.is_light() is False
    assert not any("blast_radius_tier3" in f for f in decision.floors_applied)
