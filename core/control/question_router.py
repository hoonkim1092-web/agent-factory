"""Stage 0 QuestionRouter — 순수 분류기 (파일 쓰기·side effect 없음).

설계 §6, §5 참조. LLM 호출은 QuestionRouterLLMCaller adapter를 통해서만 수행.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

import yaml

from core.control.verdicts import BlockCause, QuestionRoute


# ---------------------------------------------------------------------------
# 데이터 클래스
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Question:
    id: str
    text: str
    output_field: str
    required: bool = False
    fallback: Any = None
    default_route: QuestionRoute = QuestionRoute.LLM_DELEGATE
    block_category_if_missing: BlockCause | None = None


@dataclass
class QuestionResult:
    question_id: str
    output_field: str
    question_route: QuestionRoute
    value: Any = None
    block_cause: BlockCause | None = None
    used_fallback: bool = False
    source: str = ""
    warning: str = ""
    provenance: str = "default"  # user | research | default (INV-Q2)


@dataclass
class QuestionBatchResult:
    question_set_id: str
    schema_version: int
    schema_hash: str
    results: list[QuestionResult] = field(default_factory=list)
    paused_hitl_ids: list[str] = field(default_factory=list)
    block_results: list[QuestionResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# YAML 로더 및 검증
# ---------------------------------------------------------------------------

_ALLOWED_ROUTING_METADATA = {"required", "fallback", "default_route", "block_category_if_missing"}
_FORBIDDEN_ROUTING_METADATA = {
    "risk", "failure_policy", "escalation_policy", "fallback_allowed", "require_hitl_when"
}


def load_question_schema(yaml_path: str) -> tuple[dict, str]:
    """YAML 파일 로드 + 검증. (parsed_schema, sha256_hex) 반환.

    검증 실패 시 ValueError 발생.
    """
    with open(yaml_path, "rb") as f:
        raw_bytes = f.read()
    schema_hash = hashlib.sha256(raw_bytes).hexdigest()
    schema = yaml.safe_load(raw_bytes)
    _validate_schema(schema, yaml_path)
    return schema, schema_hash


def _validate_schema(schema: dict, source: str) -> None:
    if not schema.get("schema_version"):
        raise ValueError(f"[{source}] schema_version 누락")
    if not schema.get("question_set_id"):
        raise ValueError(f"[{source}] question_set_id 누락")

    questions = schema.get("questions", [])
    seen_ids: set[str] = set()
    for q in questions:
        if not q.get("id"):
            raise ValueError(f"[{source}] question에 id 누락")
        if not q.get("output_field"):
            raise ValueError(f"[{source}] question '{q['id']}' output_field 누락")
        if q["id"] in seen_ids:
            raise ValueError(f"[{source}] question.id 중복: '{q['id']}'")
        seen_ids.add(q["id"])

        dr = q.get("default_route", "llm_delegate")
        try:
            QuestionRoute(dr)
        except ValueError:
            raise ValueError(
                f"[{source}] question '{q['id']}' default_route='{dr}' 은 QuestionRoute 외 값"
            )

        bcm = q.get("block_category_if_missing")
        if bcm is not None:
            try:
                BlockCause(bcm)
            except ValueError:
                raise ValueError(
                    f"[{source}] question '{q['id']}' block_category_if_missing='{bcm}' 은 BlockCause 외 값"
                )

        if q.get("required") and bcm is None:
            raise ValueError(
                f"[{source}] question '{q['id']}': required=true 이면 block_category_if_missing 필수"
            )

        forbidden_used = _FORBIDDEN_ROUTING_METADATA & set(q.keys())
        if forbidden_used:
            raise ValueError(
                f"[{source}] question '{q['id']}' 허용되지 않은 routing metadata: {forbidden_used}"
            )


def parse_questions(schema: dict) -> list[Question]:
    result = []
    for q in schema.get("questions", []):
        result.append(
            Question(
                id=q["id"],
                text=q.get("text", ""),
                output_field=q["output_field"],
                required=bool(q.get("required", False)),
                fallback=q.get("fallback"),
                default_route=QuestionRoute(q.get("default_route", "llm_delegate")),
                block_category_if_missing=(
                    BlockCause(q["block_category_if_missing"])
                    if q.get("block_category_if_missing")
                    else None
                ),
            )
        )
    return result


# ---------------------------------------------------------------------------
# LLM Caller adapter 인터페이스
# ---------------------------------------------------------------------------

class QuestionRouterLLMCaller:
    """LLM 호출 adapter — 실제 구현은 하위 클래스에서 제공."""

    def batch_route(
        self,
        questions: list[Question],
        context: dict[str, Any],
        timeout_sec: float,
    ) -> dict[str, Any]:
        raise NotImplementedError


class BriefBackedQuestionCaller(QuestionRouterLLMCaller):
    """project_brief 필드를 이용해 llm_delegate 질문에 응답하는 concrete caller.

    실 LLM 호출 0 → HITL cascade 없음(INV-Q6).
    필수 2개(goal_summary/deployment_target)는 항상 응답 — 키 누락 금지(§6.3.3).
    """

    def __init__(self, project_brief: dict[str, Any]) -> None:
        self._brief = project_brief

    def batch_route(
        self,
        questions: list[Question],
        context: dict[str, Any],
        timeout_sec: float,
    ) -> dict[str, Any]:
        try:
            brief = self._brief
            goal = str(brief.get("goal") or brief.get("task_input") or "")

            # deployment_target: constraints에서 "배포:" 항목 우선, fallback="development"
            deploy = "development"
            for c in brief.get("constraints") or []:
                cs = str(c)
                if cs.startswith("배포:"):
                    deploy = cs[3:].strip()
                    break

            answers: dict[str, Any] = {
                "goal_summary": goal or "project goal",
                "deployment_target": deploy,
            }

            deliverables = brief.get("deliverables")
            if deliverables:
                answers["success_criteria"] = (
                    deliverables if isinstance(deliverables, list) else [str(deliverables)]
                )

            non_goals = brief.get("non_goals")
            if non_goals:
                answers["out_of_scope"] = (
                    non_goals if isinstance(non_goals, list) else [str(non_goals)]
                )

            return answers
        except Exception:
            # 예외를 전파하지 않음 — route_batch catch 블록이 받으면 HITL 유발(§6.3.3)
            return {
                "goal_summary": "project goal",
                "deployment_target": "development",
            }


# ---------------------------------------------------------------------------
# QuestionRouter
# ---------------------------------------------------------------------------

class QuestionRouter:
    """질문별 route를 결정하는 순수 분류기.

    파일 쓰기, pause/abort, ADR 생성 등 side effect 없음.
    """

    def __init__(
        self,
        llm_caller: QuestionRouterLLMCaller | None = None,
        timeout_sec: float = 300.0,
        synthesizer: Any = None,
    ):
        self._llm = llm_caller
        self._timeout_sec = timeout_sec
        self._synthesizer = synthesizer  # Callable[[list[Question]], dict[str, str]] | None

    def route_batch(
        self,
        questions: list[Question],
        schema: dict,
        schema_hash: str,
        blast_radius: str,
        context: dict[str, Any] | None = None,
    ) -> QuestionBatchResult:
        """질문 목록을 일괄 처리하고 QuestionBatchResult 반환."""
        context = context or {}
        results: list[QuestionResult] = []
        paused_hitl_ids: list[str] = []
        block_results: list[QuestionResult] = []

        llm_answers: dict[str, Any] = {}
        llm_questions = [q for q in questions if q.default_route == QuestionRoute.LLM_DELEGATE]
        if llm_questions and self._llm is not None:
            try:
                llm_answers = self._llm.batch_route(llm_questions, context, self._timeout_sec)
            except Exception as exc:
                for q in llm_questions:
                    r = self._handle_llm_failure(q, blast_radius, exc)
                    results.append(r)
                    if r.question_route == QuestionRoute.HITL:
                        paused_hitl_ids.append(q.id)
                    elif r.question_route == QuestionRoute.BLOCK:
                        block_results.append(r)
                llm_questions = []

        for q in questions:
            if q.default_route == QuestionRoute.HITL:
                r = QuestionResult(
                    question_id=q.id,
                    output_field=q.output_field,
                    question_route=QuestionRoute.HITL,
                    source="hitl",
                )
                paused_hitl_ids.append(q.id)
                results.append(r)

            elif q.default_route == QuestionRoute.BLOCK:
                r = QuestionResult(
                    question_id=q.id,
                    output_field=q.output_field,
                    question_route=QuestionRoute.BLOCK,
                    block_cause=q.block_category_if_missing,
                    source="policy",
                )
                block_results.append(r)
                results.append(r)

            elif q.default_route == QuestionRoute.LLM_DELEGATE and q in llm_questions:
                raw = llm_answers.get(q.id)
                r = self._process_llm_answer(q, raw, blast_radius)
                results.append(r)
                if r.question_route == QuestionRoute.HITL:
                    paused_hitl_ids.append(q.id)
                elif r.question_route == QuestionRoute.BLOCK:
                    block_results.append(r)

            elif q.default_route == QuestionRoute.PASS:
                results.append(
                    QuestionResult(
                        question_id=q.id,
                        output_field=q.output_field,
                        question_route=QuestionRoute.PASS,
                        source="pass",
                    )
                )

            elif q.default_route == QuestionRoute.RESEARCH_SYNTHESIZE:
                pass  # 아래 synthesizer 일괄 처리로 대체됨

        # RESEARCH_SYNTHESIZE 일괄 처리 — synthesizer 있으면 1회 호출, 없으면 pending
        rs_questions = [q for q in questions if q.default_route == QuestionRoute.RESEARCH_SYNTHESIZE]
        if rs_questions:
            synthesized: dict[str, str] = {}
            if self._synthesizer is not None:
                try:
                    synthesized = self._synthesizer(rs_questions) or {}
                except Exception:
                    synthesized = {}
            for q in rs_questions:
                value = synthesized.get(q.output_field)
                prov = "research" if value else "default"
                results.append(
                    QuestionResult(
                        question_id=q.id,
                        output_field=q.output_field,
                        question_route=QuestionRoute.RESEARCH_SYNTHESIZE,
                        value=value,
                        source="research_synthesize" if value else "research_synthesize_pending",
                        provenance=prov,
                    )
                )

        return QuestionBatchResult(
            question_set_id=schema.get("question_set_id", ""),
            schema_version=schema.get("schema_version", 1),
            schema_hash=schema_hash,
            results=results,
            paused_hitl_ids=paused_hitl_ids,
            block_results=block_results,
        )

    def _process_llm_answer(
        self, q: Question, raw: Any, blast_radius: str
    ) -> QuestionResult:
        if raw is None:
            return self._handle_llm_failure(q, blast_radius, exc=RuntimeError("no_answer"))

        # LLM이 block_cause를 반환한 경우 BlockCause enum으로 검증
        if isinstance(raw, dict) and "block_cause" in raw:
            bc_str = raw.get("block_cause")
            try:
                bc = BlockCause(bc_str)
            except ValueError:
                return QuestionResult(
                    question_id=q.id,
                    output_field=q.output_field,
                    question_route=QuestionRoute.HITL,
                    source="llm",
                    warning=f"llm_schema_violation: invalid block_cause='{bc_str}'",
                )
            return QuestionResult(
                question_id=q.id,
                output_field=q.output_field,
                question_route=QuestionRoute.BLOCK,
                block_cause=bc,
                source="llm",
            )

        value = raw if not isinstance(raw, dict) else raw.get("value", raw)
        return QuestionResult(
            question_id=q.id,
            output_field=q.output_field,
            question_route=QuestionRoute.LLM_DELEGATE,
            value=value,
            source="llm_delegate",
        )

    def _handle_llm_failure(
        self, q: Question, blast_radius: str, exc: Exception
    ) -> QuestionResult:
        reason = f"llm_failed:{type(exc).__name__}"

        if q.required and q.fallback is None:
            return QuestionResult(
                question_id=q.id,
                output_field=q.output_field,
                question_route=QuestionRoute.HITL,
                source="hitl",
                warning=reason,
            )

        if not q.required and q.fallback is not None:
            return QuestionResult(
                question_id=q.id,
                output_field=q.output_field,
                question_route=QuestionRoute.LLM_DELEGATE,
                value=q.fallback,
                used_fallback=True,
                source="fallback",
                warning=reason,
            )

        if not q.required and q.fallback is None:
            return QuestionResult(
                question_id=q.id,
                output_field=q.output_field,
                question_route=QuestionRoute.PASS,
                source="skip",
                warning=reason,
            )

        # required=True and fallback exists
        if blast_radius in ("cross_module", "system_wide"):
            return QuestionResult(
                question_id=q.id,
                output_field=q.output_field,
                question_route=QuestionRoute.HITL,
                source="hitl",
                warning="required_with_fallback_high_blast",
            )

        return QuestionResult(
            question_id=q.id,
            output_field=q.output_field,
            question_route=QuestionRoute.LLM_DELEGATE,
            value=q.fallback,
            used_fallback=True,
            source="fallback",
            warning=reason,
        )
