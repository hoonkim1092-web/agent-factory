"""
core/right_sized_router.py — AF Right-Sized Execution 라우터 (슬라이스 1).

classify(task, workspace, *, changed_files) → RouteDecision

LLM 분류 → 결정적 안전 floor 강제 → 보수적 fallback.
설계: docs/2026-06-03-af-right-sized-execution-detailed-design.md §3
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# 어휘 상수
# ---------------------------------------------------------------------------

ISOLATION_LEVELS: tuple[str, ...] = ("none", "source", "worktree", "dogfood")

STAGE_VOCAB: tuple[str, ...] = (
    "research", "design", "plan", "implement", "test", "review", "cross_review",
)

LIGHT_STAGES: frozenset[str] = frozenset({"plan", "implement", "test"})

_LIGHT_CONFIDENCE_THRESHOLD: float = 0.7


# ---------------------------------------------------------------------------
# RouteDecision
# ---------------------------------------------------------------------------

@dataclass
class RouteDecision:
    isolation: str
    required_stages: list[str]
    review_depth: str           # "none" | "standard" | "deep"  (슬라이스1: 기록용)
    confidence: float
    reason: str
    floors_applied: list[str] = field(default_factory=list)
    source: str = "llm"         # "llm" | "fallback"

    def is_light(self) -> bool:
        """floor 적용 후 호출 — 네이티브 light 경로 적격 여부."""
        return (
            self.source == "llm"
            and self.confidence >= _LIGHT_CONFIDENCE_THRESHOLD
            and set(self.required_stages) <= LIGHT_STAGES
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "isolation": self.isolation,
            "required_stages": list(self.required_stages),
            "review_depth": self.review_depth,
            "confidence": self.confidence,
            "reason": self.reason,
            "floors_applied": list(self.floors_applied),
            "source": self.source,
        }


# ---------------------------------------------------------------------------
# LLM 주입 (테스트: core.right_sized_router._router_llm 에 stub 대입)
# ---------------------------------------------------------------------------

_router_llm = None  # lazy ControlPlaneLLM


def _get_router_llm():
    global _router_llm
    if _router_llm is None:
        from core.control_plane_llm import ControlPlaneLLM
        _router_llm = ControlPlaneLLM()
    return _router_llm


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------

_FULL_STAGES: list[str] = list(STAGE_VOCAB)

def _fallback_decision(reason: str) -> RouteDecision:
    return RouteDecision(
        isolation="worktree",
        required_stages=list(_FULL_STAGES),
        review_depth="deep",
        confidence=0.0,
        reason=reason,
        floors_applied=[],
        source="fallback",
    )


# ---------------------------------------------------------------------------
# 검증 (_validate_raw)
# ---------------------------------------------------------------------------

def _validate_raw(raw: dict[str, Any]) -> RouteDecision | None:
    """LLM 반환 dict를 RouteDecision으로 강건 파싱. 실패 시 None."""
    if not raw:
        return None

    isolation = raw.get("isolation", "")
    if isolation not in ISOLATION_LEVELS:
        return None

    raw_stages = raw.get("required_stages") or []
    stages = [s for s in raw_stages if s in STAGE_VOCAB]
    if not stages:
        return None

    try:
        confidence = float(raw.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    if not (0.0 <= confidence <= 1.0):
        return None  # 설계 §3.5 트리거 3: confidence 범위 밖 → fallback

    review_depth = raw.get("review_depth", "deep")
    if review_depth not in ("none", "standard", "deep"):
        review_depth = "deep"

    reason = str(raw.get("reason") or "")

    return RouteDecision(
        isolation=isolation,
        required_stages=stages,
        review_depth=review_depth,
        confidence=confidence,
        reason=reason,
        source="llm",
    )


# ---------------------------------------------------------------------------
# 보조 함수
# ---------------------------------------------------------------------------

def _isolation_rank(level: str) -> int:
    try:
        return ISOLATION_LEVELS.index(level)
    except ValueError:
        return 0


def _stage_ordered_union(base: list[str], extra: tuple[str, ...]) -> list[str]:
    """STAGE_VOCAB 순서 보존 union."""
    combined = set(base) | set(extra)
    return [s for s in STAGE_VOCAB if s in combined]


def _is_self_modification(workspace: str, changed_files: list[str]) -> bool:
    """scope에 AF 자기-수정 경로가 포함되면 True.

    workspace 경로명에 의존하지 않는다 — dogfood worktree 경로처럼
    'agent-factory'가 없는 경우에도 정확히 감지하기 위함.
    """
    from core.express_router import _SELF_MOD
    return any(
        any(token in f.replace("\\", "/") for token in _SELF_MOD)
        for f in changed_files
    )


def _max_tier(changed_files: list[str], workspace: str) -> int:
    """scope 파일들의 blast_radius Tier 최댓값.

    classify_path (path-only, 결정적) 사용 — 신규 파일도 분류 가능.
    설계 §1.2: classify_with_content는 파일 읽음, 신규 파일엔 부적합.
    workspace 파라미터는 시그니처 호환성을 위해 유지.
    """
    if not changed_files:
        return 0
    from scripts.blast_radius import classify_path
    return max(classify_path(f) for f in changed_files)


# ---------------------------------------------------------------------------
# 안전 floor
# ---------------------------------------------------------------------------

def _apply_safety_floors(
    decision: RouteDecision,
    workspace: str,
    changed_files: list[str],
) -> RouteDecision:
    applied: list[str] = []

    # Floor 1: self-mod → isolation 최소 worktree
    if _is_self_modification(workspace, changed_files):
        if _isolation_rank(decision.isolation) < _isolation_rank("worktree"):
            decision.isolation = "worktree"
            applied.append("self_mod_isolation>=worktree")

    # Floor 2: blast_radius Tier3 → design+review+cross_review 강제
    if changed_files and _max_tier(changed_files, workspace) >= 3:
        forced = ("design", "review", "cross_review")
        added = [s for s in forced if s not in decision.required_stages]
        if added:
            decision.required_stages = _stage_ordered_union(decision.required_stages, forced)
            applied.append("blast_radius_tier3:" + ",".join(added))

    decision.floors_applied = applied
    return decision


# ---------------------------------------------------------------------------
# 프롬프트 빌더
# ---------------------------------------------------------------------------

def _build_prompt(task: str, changed_files: list[str], tier_hint: dict[str, int]) -> str:
    files_section = "\n".join(f"  - {f} (Tier {tier_hint.get(f, '?')})" for f in changed_files) or "  (없음)"
    stage_list = ", ".join(STAGE_VOCAB)
    light_list = ", ".join(sorted(LIGHT_STAGES))

    return f"""You are a task-complexity classifier for the Agent Factory codebase.

## Task
{task}

## Intended scope files (derived from task, not guaranteed exhaustive)
{files_section}

## Output (JSON only, no explanation outside JSON)
Return a JSON object with exactly these keys:
  isolation       : one of {list(ISOLATION_LEVELS)}
  required_stages : subset of [{stage_list}] in execution order
  review_depth    : one of ["none", "standard", "deep"]
  confidence      : float 0.0–1.0 (your certainty)
  reason          : brief explanation (1–2 sentences)

## Rules
- Pure leaf implementation (add a single function, no API/contract changes):
    required_stages should be [{light_list}] only.
- If design, review, or cross-review is genuinely needed, include them.
- If uncertain, set confidence < 0.5 (forces full pipeline).
- Tier hint is advisory only — safety floors enforce hard limits independently.
"""


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------

def classify(
    task: str,
    workspace: str,
    *,
    changed_files: list[str] | None = None,
) -> RouteDecision:
    """task를 실행 경로로 분류한다.

    1. _get_router_llm().generate_json(_build_prompt(...)) 로 후보 결정 생성
    2. 파싱·검증 실패 / 예외 → _fallback_decision()
    3. _apply_safety_floors() 로 결정적 하한 강제
    """
    files: list[str] = list(changed_files or [])
    if not files:
        return _fallback_decision("no changed_files: scope required for routing")

    # Tier hint 계산 (프롬프트용 참고 — floor와 별도)
    tier_hint: dict[str, int] = {}
    if files:
        try:
            from scripts.blast_radius import classify_path
            tier_hint = {f: classify_path(f) for f in files}
        except Exception:
            pass

    prompt = _build_prompt(task, files, tier_hint)

    try:
        llm = _get_router_llm()
        raw = llm.generate_json(prompt)
    except Exception as exc:
        return _fallback_decision(f"LLM error: {exc}")

    decision = _validate_raw(raw)
    if decision is None:
        return _fallback_decision(f"invalid LLM response: {raw!r}")

    decision = _apply_safety_floors(decision, workspace, files)
    return decision
