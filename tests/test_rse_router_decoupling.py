"""Tests for Phase 1+2 router/research decoupling.

§5.3 (Phase 1 router decoupling) + §6.5 (Phase 2 observe-first Tier3 floor).
Design: docs/2026-06-07-router-scope-research-decoupling-design.md
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

import core.right_sized_router as rsr
from core.right_sized_router import (
    RouteDecision,
    LIGHT_STAGES,
    classify,
    _fallback_decision,
    ROUTE_MARKER_SCOPE_UNCERTAIN,
)


# ---------------------------------------------------------------------------
# Stub helper (reused from test_right_sized_router.py)
# ---------------------------------------------------------------------------

class _StubLLM:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc
        self.call_count = 0

    def generate_json(self, prompt, output_schema=None):
        self.call_count += 1
        if self._exc is not None:
            raise self._exc
        return self._response


def _stub(response=None, exc=None):
    return _StubLLM(response=response, exc=exc)


_LIGHT_RESPONSE = {
    "isolation": "source",
    "required_stages": ["plan", "implement", "test"],
    "review_depth": "none",
    "confidence": 0.9,
    "reason": "pure leaf function",
}

_LOW_CONF_RESPONSE = {
    "isolation": "source",
    "required_stages": ["plan", "implement", "test"],
    "review_depth": "none",
    "confidence": 0.7,  # < 0.82 threshold
    "reason": "uncertain",
}

_NON_LIGHT_RESPONSE = {
    "isolation": "worktree",
    "required_stages": ["design", "plan", "implement", "test"],
    "review_depth": "deep",
    "confidence": 0.95,
    "reason": "needs design",
}


# ===========================================================================
# §5.3 Phase 1 — Router decoupling (empty-scope LLM path)
# ===========================================================================

class TestEmptyScopeLLMPath:
    """scope=[] now calls LLM instead of immediate fallback (Phase 1 contract)."""

    def test_empty_scope_calls_llm(self, monkeypatch, tmp_path):
        """scope=[] → LLM IS called (Phase 1 contract change from R-FB-NOSCOPE)."""
        stub = _stub(_LIGHT_RESPONSE)
        monkeypatch.setattr(rsr, "_router_llm", stub)
        classify("add geometric_mean", str(tmp_path), changed_files=[])
        assert stub.call_count >= 1

    def test_empty_scope_high_conf_light(self, monkeypatch, tmp_path):
        """conf ≥ 0.82 + light stages → is_light()=True + marker attached."""
        monkeypatch.setattr(rsr, "_router_llm", _stub(_LIGHT_RESPONSE))
        decision = classify("add geometric_mean", str(tmp_path), changed_files=[])
        assert decision.source == "llm"
        assert decision.is_light() is True
        assert ROUTE_MARKER_SCOPE_UNCERTAIN in decision.markers

    def test_empty_scope_low_conf_not_light(self, monkeypatch, tmp_path):
        """conf < 0.82 → is_light()=False (full pipeline). LLM judgment preserved."""
        monkeypatch.setattr(rsr, "_router_llm", _stub(_LOW_CONF_RESPONSE))
        decision = classify("add something", str(tmp_path), changed_files=[])
        # LLM was called → source="llm", but below 0.82 threshold
        assert decision.source == "llm"
        assert decision.is_light() is False
        # marker still attached (audit trail preserved)
        assert ROUTE_MARKER_SCOPE_UNCERTAIN in decision.markers

    def test_empty_scope_llm_error_full(self, monkeypatch, tmp_path):
        """LLM exception → fallback (source='fallback')."""
        monkeypatch.setattr(rsr, "_router_llm", _stub(exc=RuntimeError("net down")))
        decision = classify("add helper", str(tmp_path), changed_files=[])
        assert decision.source == "fallback"
        assert decision.is_light() is False

    def test_empty_scope_invalid_full(self, monkeypatch, tmp_path):
        """bad schema → fallback (source='fallback')."""
        monkeypatch.setattr(rsr, "_router_llm", _stub({"bad": "schema"}))
        decision = classify("add helper", str(tmp_path), changed_files=[])
        assert decision.source == "fallback"
        assert decision.is_light() is False

    def test_empty_scope_non_light_stages_full(self, monkeypatch, tmp_path):
        """conf high but design/review stages → is_light()=False (marker still attached)."""
        monkeypatch.setattr(rsr, "_router_llm", _stub(_NON_LIGHT_RESPONSE))
        decision = classify("refactor auth system", str(tmp_path), changed_files=[])
        assert decision.source == "llm"
        assert decision.is_light() is False
        assert ROUTE_MARKER_SCOPE_UNCERTAIN in decision.markers

    def test_marker_serialized_in_to_dict(self, monkeypatch, tmp_path):
        """marker-bearing decision → to_dict()['markers'] contains scope_uncertain."""
        monkeypatch.setattr(rsr, "_router_llm", _stub(_LIGHT_RESPONSE))
        decision = classify("add func", str(tmp_path), changed_files=[])
        d = decision.to_dict()
        assert "markers" in d
        assert ROUTE_MARKER_SCOPE_UNCERTAIN in d["markers"]

    def test_scope_present_uses_existing_path(self, monkeypatch, tmp_path):
        """scope ≠ [] → existing LLM path used, NO marker (INV-1)."""
        monkeypatch.setattr(rsr, "_router_llm", _stub(_LIGHT_RESPONSE))
        decision = classify("add func", str(tmp_path),
                            changed_files=["scripts/utils.py"])
        assert decision.markers == []  # no uncertainty marker on scoped path

    def test_is_light_without_marker_uses_07_threshold(self, tmp_path):
        """Decisions without SCOPE_UNCERTAIN marker use original 0.7 threshold (INV-1)."""
        d = RouteDecision(
            isolation="source",
            required_stages=["plan", "implement", "test"],
            review_depth="none",
            confidence=0.75,
            reason="ok",
        )
        # 0.75 >= 0.7 → light (no marker)
        assert d.is_light() is True

    def test_is_light_with_marker_uses_082_threshold(self, tmp_path):
        """Decisions WITH SCOPE_UNCERTAIN marker use 0.82 threshold."""
        d = RouteDecision(
            isolation="source",
            required_stages=["plan", "implement", "test"],
            review_depth="none",
            confidence=0.75,
            reason="ok",
            markers=[ROUTE_MARKER_SCOPE_UNCERTAIN],
        )
        # 0.75 < 0.82 → NOT light (marker raises threshold)
        assert d.is_light() is False

    def test_is_light_with_marker_boundary_above(self, tmp_path):
        """SCOPE_UNCERTAIN marker + conf=0.83 (≥0.82) → is_light()=True (0.82 boundary)."""
        d = RouteDecision(
            isolation="source",
            required_stages=["plan", "implement", "test"],
            review_depth="none",
            confidence=0.83,
            reason="ok",
            markers=[ROUTE_MARKER_SCOPE_UNCERTAIN],
        )
        # 0.83 >= 0.82 → light
        assert d.is_light() is True

    def test_is_light_with_marker_boundary_below(self, tmp_path):
        """SCOPE_UNCERTAIN marker + conf=0.81 (<0.82) → is_light()=False (0.82 boundary)."""
        d = RouteDecision(
            isolation="source",
            required_stages=["plan", "implement", "test"],
            review_depth="none",
            confidence=0.81,
            reason="ok",
            markers=[ROUTE_MARKER_SCOPE_UNCERTAIN],
        )
        # 0.81 < 0.82 → NOT light
        assert d.is_light() is False

    def test_is_light_with_marker_high_conf(self, tmp_path):
        """SCOPE_UNCERTAIN marker + conf=0.9 → is_light()=True."""
        d = RouteDecision(
            isolation="source",
            required_stages=["plan", "implement", "test"],
            review_depth="none",
            confidence=0.9,
            reason="ok",
            markers=[ROUTE_MARKER_SCOPE_UNCERTAIN],
        )
        assert d.is_light() is True


# ===========================================================================
# §5.2 Phase 1 — dogfood dispatch guard (_light_allowed)
# ===========================================================================

class TestLightAllowed:
    """_light_allowed implements INV-1 + INV-5(δB)."""

    def _make_state(self, merge_mode: str = "auto_policy"):
        from core.dogfood import DogfoodState
        state = MagicMock(spec=DogfoodState)
        state.merge_mode = merge_mode
        return state

    def _make_route(self, has_marker: bool) -> RouteDecision:
        return RouteDecision(
            isolation="source",
            required_stages=["plan", "implement", "test"],
            review_depth="none",
            confidence=0.9,
            reason="ok",
            markers=[ROUTE_MARKER_SCOPE_UNCERTAIN] if has_marker else [],
        )

    def test_scope_present_always_allowed(self):
        """scope ≠ [] → True regardless of merge_mode (INV-1)."""
        from core.dogfood import _light_allowed
        route = self._make_route(has_marker=False)
        state = self._make_state("auto_policy")
        assert _light_allowed(route, ["scripts/utils.py"], state) is True

    def test_empty_scope_auto_policy_blocked(self):
        """empty scope + auto_policy → False (INV-5/δB)."""
        from core.dogfood import _light_allowed
        route = self._make_route(has_marker=True)
        state = self._make_state("auto_policy")
        assert _light_allowed(route, [], state) is False

    def test_empty_scope_never_allowed(self):
        """empty scope + merge_mode=never + marker → True."""
        from core.dogfood import _light_allowed
        route = self._make_route(has_marker=True)
        state = self._make_state("never")
        assert _light_allowed(route, [], state) is True

    def test_empty_scope_manual_allowed(self):
        """empty scope + merge_mode=manual + marker → True."""
        from core.dogfood import _light_allowed
        route = self._make_route(has_marker=True)
        state = self._make_state("manual")
        assert _light_allowed(route, [], state) is True

    def test_empty_scope_no_marker_blocked(self):
        """empty scope + no marker → False (marker required for empty-scope light)."""
        from core.dogfood import _light_allowed
        route = self._make_route(has_marker=False)
        state = self._make_state("never")
        assert _light_allowed(route, [], state) is False


# ===========================================================================
# §6.4 Phase 2 — MergePolicy.tier3_floor_mode validation
# ===========================================================================

class TestMergePolicyTier3Floor:

    def test_default_is_observe(self):
        from core.dogfood import MergePolicy
        p = MergePolicy()
        assert p.tier3_floor_mode == "observe"

    def test_enforce_valid(self):
        from core.dogfood import MergePolicy
        p = MergePolicy(tier3_floor_mode="enforce")
        assert p.tier3_floor_mode == "enforce"

    def test_invalid_mode_raises(self):
        from core.dogfood import MergePolicy
        with pytest.raises(ValueError, match="invalid tier3_floor_mode"):
            MergePolicy(tier3_floor_mode="bogus")


# ===========================================================================
# §6.5 Phase 2 — _run_develop_light tier3_floor observation
# ===========================================================================

class TestTier3FloorObservation:
    """Tier3 floor observation in _run_develop_light (observe mode)."""

    def _make_state(self, tmp_path, merge_mode="never"):
        from core.dogfood import DogfoodState, DogfoodPhase
        state = DogfoodState(
            run_id="test-obs-001",
            task="add helper to scripts/utils.py",
            phase=DogfoodPhase.DEVELOP,
            source_workspace=str(tmp_path),
            runtime_workspace=str(tmp_path / "runtime"),
        )
        state.merge_mode = merge_mode
        state.worktree_workspace = str(tmp_path)
        state.route_decision = {"markers": [ROUTE_MARKER_SCOPE_UNCERTAIN]}
        (tmp_path / "runtime").mkdir(parents=True, exist_ok=True)
        return state

    def _make_policy(self, mode="observe"):
        from core.dogfood import MergePolicy
        return MergePolicy(mode="never", tier3_floor_mode=mode)

    def _mock_impl_result(self, actual_changed: list[str]) -> dict:
        return {"ok": True, "actual_changed": actual_changed, "executed": [], "failures": []}

    def _mock_plan(self):
        from core.planner import ExecutablePlan, PlanStep
        return ExecutablePlan(
            intent="add helper",
            steps=[
                PlanStep(
                    id="s1",
                    action="implement",
                    target="scripts/utils.py",
                    artifacts=["scripts/utils.py"],
                    commands=["python -c 'pass'"],
                    tests_required=["tests/test_utils.py"],
                )
            ],
            verification_requirements=["pytest tests/test_utils.py"],
        )

    def test_tier3_floor_observe_emits_warning(self, tmp_path, monkeypatch):
        """Tier3 산출물 → tier3_floor.observability=='observed' + changed_tier3, phase complete."""
        from core.dogfood import _run_develop_light, DogfoodPhase
        state = self._make_state(tmp_path)
        policy = self._make_policy("observe")

        changed_files = ["core/dogfood.py"]  # stub → Tier3

        def _mock_compile(spec_input, *a, **kw):
            from core.spec_compiler import CompiledSpec
            return CompiledSpec(
                intent=spec_input.get("task_input", ""),
                scope=[],
                success_criteria=["tests pass"],
            )

        def _mock_premortem(spec):
            return {"risks": [], "notes": []}

        def _mock_build_plan(spec, premortem):
            return self._mock_plan()

        def _mock_run_implement(state_arg, context):
            return self._mock_impl_result(changed_files)

        def _mock_classify_with_content(path, workspace):
            # core/ files are Tier3 in production; replicate for test
            return 3 if path.startswith("core/") else 2

        # patch source modules so `from X import Y` inside _run_develop_light gets the mock
        monkeypatch.setattr("core.spec_compiler.compile_spec", _mock_compile)
        monkeypatch.setattr("core.premortem.run_premortem", _mock_premortem)
        monkeypatch.setattr("core.planner.build_plan", _mock_build_plan)
        monkeypatch.setattr("core.dogfood._run_implement_phase", _mock_run_implement)
        monkeypatch.setattr("core.dogfood.atomic_write_json", lambda *a, **kw: None)
        monkeypatch.setattr("scripts.blast_radius.classify_with_content",
                            _mock_classify_with_content)

        result = _run_develop_light(state, policy)

        assert "tier3_floor" in result
        tf = result["tier3_floor"]
        assert tf["observability"] == "observed"
        assert "core/dogfood.py" in tf.get("changed_tier3", [])
        # observe: complete 흐름 무변
        assert result.get("ok") is True

    def test_tier2_floor_no_warning(self, tmp_path, monkeypatch):
        """Tier2 산출물(wiki) → observability='observed', changed_tier3 없음."""
        from core.dogfood import _run_develop_light
        state = self._make_state(tmp_path)
        policy = self._make_policy("observe")

        # scripts/codebase_symbols.py is Tier2 → no tier3_changed
        changed_files = ["scripts/codebase_symbols.py"]

        def _mock_compile(spec_input, *a, **kw):
            from core.spec_compiler import CompiledSpec
            return CompiledSpec(
                intent=spec_input.get("task_input", ""),
                scope=[],
                success_criteria=[],
            )

        def _mock_premortem(spec):
            return {"risks": [], "notes": []}

        def _mock_build_plan(spec, premortem):
            return self._mock_plan()

        def _mock_run_implement(state_arg, context):
            return self._mock_impl_result(changed_files)

        monkeypatch.setattr("core.spec_compiler.compile_spec", _mock_compile)
        monkeypatch.setattr("core.premortem.run_premortem", _mock_premortem)
        monkeypatch.setattr("core.planner.build_plan", _mock_build_plan)
        monkeypatch.setattr("core.dogfood._run_implement_phase", _mock_run_implement)
        monkeypatch.setattr("core.dogfood.atomic_write_json", lambda *a, **kw: None)

        result = _run_develop_light(state, policy)

        assert "tier3_floor" in result
        tf = result["tier3_floor"]
        assert tf["observability"] == "observed"
        assert tf.get("changed_tier3") is None or tf.get("changed_tier3") == []

    def test_actual_changed_empty_records_no_changes(self, tmp_path, monkeypatch):
        """actual_changed=[] + fallback도 [] → tier3_floor.observability=='no_changes'."""
        from core.dogfood import _run_develop_light
        state = self._make_state(tmp_path)
        policy = self._make_policy("observe")

        def _mock_compile(spec_input, *a, **kw):
            from core.spec_compiler import CompiledSpec
            return CompiledSpec(
                intent=spec_input.get("task_input", ""),
                scope=[],
                success_criteria=[],
            )

        def _mock_premortem(spec):
            return {"risks": [], "notes": []}

        def _mock_build_plan(spec, premortem):
            return self._mock_plan()

        def _mock_run_implement(state_arg, context):
            return self._mock_impl_result([])  # empty changed files

        def _mock_fallback(state_arg, worktree):
            return []  # fallback also empty

        monkeypatch.setattr("core.spec_compiler.compile_spec", _mock_compile)
        monkeypatch.setattr("core.premortem.run_premortem", _mock_premortem)
        monkeypatch.setattr("core.planner.build_plan", _mock_build_plan)
        monkeypatch.setattr("core.dogfood._run_implement_phase", _mock_run_implement)
        monkeypatch.setattr("core.dogfood._changed_files_fallback", _mock_fallback)
        monkeypatch.setattr("core.dogfood.atomic_write_json", lambda *a, **kw: None)

        result = _run_develop_light(state, policy)

        assert "tier3_floor" in result
        assert result["tier3_floor"]["observability"] == "no_changes"

    def test_observe_does_not_block(self, tmp_path, monkeypatch):
        """observe 모드는 Tier3 산출물이 있어도 BLOCK하지 않음."""
        from core.dogfood import _run_develop_light
        state = self._make_state(tmp_path)
        policy = self._make_policy("observe")

        changed_files = ["core/dogfood.py"]  # stub → Tier3

        def _mock_compile(spec_input, *a, **kw):
            from core.spec_compiler import CompiledSpec
            return CompiledSpec(
                intent=spec_input.get("task_input", ""),
                scope=[],
                success_criteria=[],
            )

        def _mock_premortem(spec):
            return {"risks": [], "notes": []}

        def _mock_build_plan(spec, premortem):
            return self._mock_plan()

        def _mock_run_implement(state_arg, context):
            return self._mock_impl_result(changed_files)

        def _mock_classify_with_content(path, workspace):
            return 3 if path.startswith("core/") else 2

        monkeypatch.setattr("core.spec_compiler.compile_spec", _mock_compile)
        monkeypatch.setattr("core.premortem.run_premortem", _mock_premortem)
        monkeypatch.setattr("core.planner.build_plan", _mock_build_plan)
        monkeypatch.setattr("core.dogfood._run_implement_phase", _mock_run_implement)
        monkeypatch.setattr("core.dogfood.atomic_write_json", lambda *a, **kw: None)
        monkeypatch.setattr("scripts.blast_radius.classify_with_content",
                            _mock_classify_with_content)

        result = _run_develop_light(state, policy)

        # observe mode: ok unchanged, no block
        assert result.get("ok") is True
        # tier3_floor present but no forced block
        assert result["tier3_floor"]["observability"] == "observed"
