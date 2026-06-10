"""
tests/test_ise_provider_awareness.py
======================================
자가수정 brain Provider-Awareness 불변식 테스트 (INV-1~6).

INV-1: CLI provider 1개 이상 감지 시 ISEAnalyzer가 CLI 경로(execute_cli_chat)를 탄다.
INV-2: 우선 provider INFRA 실패 시 다음 provider로 fallback해 성공한다.
INV-3: CLI 0 + API key 0 → 예외 없이 휴리스틱 ISEAnalysis 반환.
INV-4: ControlPlaneLLM이 generate/generate_json 메서드를 갖는다(인터페이스 불변).
INV-5: 교체 대상 3 모듈에 LLMEngine( 직접 생성 0건.
INV-6: StrategyEvaluator 생성 시 .llm이 ControlPlaneLLM 타입.
"""
from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# ── 경로 상수 ──────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).parent.parent
_TARGET_MODULES = [
    _REPO_ROOT / "core" / "ise_analyzer.py",
    _REPO_ROOT / "core" / "ise_redesigner.py",
    _REPO_ROOT / "core" / "evaluator.py",
]

# CLI가 성공 응답으로 돌려주는 JSON 텍스트
_CLI_JSON = (
    '{"action": "retry", "reasoning": "test reason", "root_cause": "syntax issue",'
    ' "suggested_strategy": "fix the typo", "confidence": 0.8,'
    ' "error_category": "syntax", "new_instruction": "fix it"}'
)
_CLI_OK = {"ok": True, "text": _CLI_JSON, "reason": ""}
_CLI_INFRA = {"ok": False, "text": "", "reason": "connection refused"}


# ── INV-1: CLI 경로를 탄다 ──────────────────────────────────────
def test_inv1_ise_analyzer_uses_cli_when_available():
    """CLI provider 1개 이상 감지 시 ISEAnalyzer.analyze_failure가 execute_cli_chat을 호출한다."""
    from core.ise_analyzer import ISEAnalyzer

    with (
        patch(
            "core.providers.registry.detect_available_cli_providers",
            return_value=["claude_cli"],
        ),
        patch("core.llm_engine.get_current_gemini_key", return_value=""),
        patch(
            "core.providers.cli.execute_cli_chat",
            return_value=_CLI_OK,
        ) as mock_chat,
    ):
        analyzer = ISEAnalyzer()
        result = analyzer.analyze_failure(
            task="implement foo()",
            result={"ok": False, "reason": "SyntaxError on line 5"},
        )

    assert mock_chat.called, "execute_cli_chat이 호출되지 않았다 (LLMEngine 경로를 탔을 가능성)"
    assert result is not None


# ── INV-2: INFRA 실패 → 다음 provider fallback ───────────────
def test_inv2_infra_failure_triggers_fallback():
    """claude_cli가 INFRA 실패하면 codex_cli로 fallback해 결과를 반환한다."""
    from core.ise_analyzer import ISEAnalyzer
    from core.failure_classifier import FailureCategory

    call_provider_ids: list[str] = []

    def _fake_chat(req):
        call_provider_ids.append(req.provider_id)
        if req.provider_id == "claude_cli":
            return _CLI_INFRA
        return _CLI_OK

    with (
        patch(
            "core.providers.registry.detect_available_cli_providers",
            return_value=["claude_cli", "codex_cli"],
        ),
        patch("core.llm_engine.get_current_gemini_key", return_value=""),
        patch("core.providers.cli.execute_cli_chat", side_effect=_fake_chat),
        patch(
            "core.failure_classifier.classify_failure",
            return_value=FailureCategory.INFRA,
        ),
    ):
        analyzer = ISEAnalyzer()
        analyzer.analyze_failure(
            task="implement bar()",
            result={"ok": False, "reason": "err"},
        )

    assert "claude_cli" in call_provider_ids, "claude_cli가 시도되지 않았다"
    assert "codex_cli" in call_provider_ids, "codex_cli fallback이 발생하지 않았다"


# ── INV-3: graceful degrade ───────────────────────────────────
def test_inv3_graceful_degrade_no_provider():
    """CLI 0 + API key 0 → 예외 없이 ISEAnalysis 반환, 휴리스틱 분류 유지."""
    from core.ise_analyzer import ISEAnalyzer, ISEAnalysis

    with (
        patch(
            "core.providers.registry.detect_available_cli_providers",
            return_value=[],
        ),
        patch("core.llm_engine.get_current_gemini_key", return_value=""),
    ):
        analyzer = ISEAnalyzer()
        # LLM이 없으면 generate()가 "" 반환 → 휴리스틱 규칙만 동작
        result = analyzer.analyze_failure(
            task="implement baz()",
            result={"ok": False, "reason": "SyntaxError: invalid syntax"},
        )

    assert isinstance(result, ISEAnalysis), "ISEAnalysis가 반환되지 않았다"
    # "SyntaxError"는 규칙 기반으로 "syntax"로 분류됨
    assert result.error_category == "syntax", (
        f"규칙 기반 분류 실패: {result.error_category}"
    )


# ── INV-4: ControlPlaneLLM 인터페이스 불변 ──────────────────────
def test_inv4_control_plane_llm_has_required_interface():
    """ControlPlaneLLM이 generate(prompt) 및 generate_json(prompt) 메서드를 갖는다."""
    import inspect
    from core.control_plane_llm import ControlPlaneLLM

    # generate(prompt) → str
    sig_g = inspect.signature(ControlPlaneLLM.generate)
    params_g = list(sig_g.parameters.keys())
    assert "prompt" in params_g, "generate()에 prompt 파라미터 없음"

    # generate_json(prompt, output_schema=None) → dict
    sig_gj = inspect.signature(ControlPlaneLLM.generate_json)
    params_gj = list(sig_gj.parameters.keys())
    assert "prompt" in params_gj, "generate_json()에 prompt 파라미터 없음"
    assert "output_schema" in params_gj, "generate_json()에 output_schema 파라미터 없음"

    # 빈 provider 상태에서 반환 타입 확인
    with patch.object(ControlPlaneLLM, "_init_providers", lambda self: None):
        cp = ControlPlaneLLM()
        cp._cli_providers = []
        cp._api_engine = None

    assert cp.generate("x") == "", "generate()가 str을 반환해야 한다"
    assert cp.generate_json("x") == {}, "generate_json()이 dict를 반환해야 한다"


# ── INV-5: LLMEngine 직접 생성 0건 ────────────────────────────
def test_inv5_no_llmengine_direct_instantiation_in_targets():
    """교체 대상 3 모듈(ise_analyzer/ise_redesigner/evaluator)에 LLMEngine( 직접 생성 없다."""
    for module_path in _TARGET_MODULES:
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = ""
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            assert name != "LLMEngine", (
                f"{module_path.name}:{node.lineno} — LLMEngine( 직접 생성 발견 (INV-5 위반)"
            )


# ── INV-6: 생성처 3곳의 .llm이 ControlPlaneLLM 타입 ─────────────
def test_inv6_strategy_evaluator_llm_is_control_plane():
    """StrategyEvaluator() 인스턴스의 .llm이 ControlPlaneLLM 타입이다."""
    from core.evaluator import StrategyEvaluator
    from core.control_plane_llm import ControlPlaneLLM

    with (
        patch.object(ControlPlaneLLM, "_init_providers", lambda self: None),
        patch("core.llm_engine.get_current_gemini_key", return_value=""),
    ):
        ev1 = StrategyEvaluator()                                   # supervisor.py:399
        ev2 = StrategyEvaluator(model_name="some-model")            # dynamic_orchestrator.py:78
        ev3 = StrategyEvaluator(model_name="claude-sonnet-4-5")     # fsa_loop.py:95

    for label, ev in (("default", ev1), ("some-model", ev2), ("claude-sonnet-4-5", ev3)):
        assert isinstance(ev.llm, ControlPlaneLLM), (
            f"StrategyEvaluator(model_name={label!r}).llm 타입이 "
            f"{type(ev.llm).__name__}이지 ControlPlaneLLM이 아님 (INV-6 위반)"
        )
