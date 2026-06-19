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
    ):
        self._llm = llm_caller
        self._timeout_sec = timeout_sec

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
                # Q-S3에서 ResearchRouter로 합성 예정 (INV-Q1)
                # 지금은 pending 표시만 — 실제 합성은 synthesize_via_research()가 담당
                results.append(
                    QuestionResult(
                        question_id=q.id,
                        output_field=q.output_field,
                        question_route=QuestionRoute.RESEARCH_SYNTHESIZE,
                        source="research_synthesize_pending",
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
