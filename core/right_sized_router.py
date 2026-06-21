"""
core/right_sized_router.py — AF Right-Sized Execution 라우터 (슬라이스 1).

classify(task, workspace, *, changed_files) → RouteDecision

LLM 분류 → 결정적 안전 floor 강제 → 보수적 fallback.
설계: docs/2026-06-03-af-right-sized-execution-detailed-design.md §3
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

# ---------------------------------------------------------------------------
# 어휘 상수 (SSOT — 소비처는 import해서만 쓴다)
# ---------------------------------------------------------------------------

ISOLATION_LEVELS: tuple[str, ...] = ("none", "source", "worktree", "dogfood")

STAGE_RESEARCH:     str = "research"
STAGE_DESIGN:       str = "design"
STAGE_PLAN:         str = "plan"
STAGE_IMPLEMENT:    str = "implement"
STAGE_TEST:         str = "test"
STAGE_REVIEW:       str = "review"
STAGE_CROSS_REVIEW: str = "cross_review"

STAGE_VOCAB: tuple[str, ...] = (
    STAGE_RESEARCH, STAGE_DESIGN, STAGE_PLAN, STAGE_IMPLEMENT,
    STAGE_TEST, STAGE_REVIEW, STAGE_CROSS_REVIEW,
)

LIGHT_STAGES: frozenset[str] = frozenset({STAGE_PLAN, STAGE_IMPLEMENT, STAGE_TEST})

_LIGHT_CONFIDENCE_THRESHOLD: float = 0.7
_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD: float = 0.82
ROUTE_MARKER_SCOPE_UNCERTAIN: Final[str] = "scope_uncertain"


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
    markers: list[str] = field(default_factory=list)
    source: str = "llm"         # "llm" | "fallback"

    def is_light(self) -> bool:
        """floor 적용 후 호출 — 네이티브 light 경로 적격 여부.

        SCOPE_UNCERTAIN marker가 있으면 0.82 임계 적용(empty-scope 추론은 불확실).
        marker 없는 결정은 0.7 그대로 → scope 있는 경로 완전 무변(INV-1).
        """
        threshold = (
            _EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD
            if ROUTE_MARKER_SCOPE_UNCERTAIN in self.markers
            else _LIGHT_CONFIDENCE_THRESHOLD
        )
        return (
            self.source == "llm"
            and self.confidence >= threshold
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
            "markers": list(self.markers),
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

    classify_with_content 사용 — 내용 기반 Tier3 상향 포함.
    신규(nonexistent) 파일은 classify_with_content가 Tier2로 fallback.
    """
    if not changed_files:
        return 0
    from scripts.blast_radius import classify_with_content
    return max(classify_with_content(f, workspace) for f in changed_files)


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
        forced = (STAGE_DESIGN, STAGE_REVIEW, STAGE_CROSS_REVIEW)
        added = [s for s in forced if s not in decision.required_stages]
        if added:
            decision.required_stages = _stage_ordered_union(decision.required_stages, forced)
            applied.append("blast_radius_tier3:" + ",".join(added))

    decision.floors_applied = applied
    return decision


# ---------------------------------------------------------------------------
# 프롬프트 빌더
# ---------------------------------------------------------------------------

def _build_empty_scope_prompt(task: str) -> str:
    """scope 미확정 task용 분류 프롬프트. 파일 목록 없이 task 의미만으로 추론. CoT 구조."""
    stage_list = ", ".join(STAGE_VOCAB)
    light_list = ", ".join(sorted(LIGHT_STAGES))
    return f"""You are a task-complexity classifier for the Agent Factory codebase.

## Task
{task}

## Intended scope files
(미확정) — the task did not specify explicit file paths. Infer complexity from the task description alone.

## Step-by-step reasoning (follow these steps before outputting JSON)

Step 1 — Leaf check:
  Is this a PURE LEAF implementation? Criteria: adds/changes a single function with NO API
  or contract changes, affects at most 1–2 files, no design decisions needed.
  Answer: YES or NO

Step 2 — Stage necessity:
  Which stages are GENUINELY needed?
  - research: only if external knowledge or API discovery is needed
  - design: only if architecture or interface decisions must be made first
  - plan: almost always needed before implementation
  - implement: needed if any code changes
  - test: needed if any code changes
  - review: needed if non-trivial logic or potential regressions
  - cross_review: needed if cross-cutting concerns or system boundaries

Step 3 — Scope uncertainty:
  Without explicit file paths, how certain are you?
  If the task is vague or covers multiple systems, confidence MUST be < 0.5.

Step 4 — Decision:
  Pure-leaf (YES in Step 1) + clear description → confidence ≥ 0.82.
  Ambiguous or multi-system → confidence < 0.60.

## Output (JSON block only — no text before or after)
```json
{{
  "isolation": "<one of {list(ISOLATION_LEVELS)}>",
  "required_stages": ["<subset of [{stage_list}] in execution order>"],
  "review_depth": "<none | standard | deep>",
  "confidence": <float 0.0-1.0>,
  "reason": "<1-2 sentences summarizing your conclusion>"
}}
```

## Additional rules
- Pure leaf (YES in Step 1): required_stages = [{light_list}] only.
- Multi-system or design-heavy: include design/review/cross_review as needed.
- Tier hint is unavailable — rely on task semantics only.
"""


def _classify_empty_scope(task: str, workspace: str) -> RouteDecision:
    """scope 미확정 task를 LLM으로 분류. 보수적 — 높은 임계(0.82) + marker.

    Precondition: changed_files is empty — caller (classify()) guarantees this.

    INV-2: LLM 실패/무효 → full fallback.
    INV-3: 반환 결정에 ROUTE_MARKER_SCOPE_UNCERTAIN 부착.

    [안전성] 빈-scope는 changed_files=[]이므로 _apply_safety_floors의 Floor 1·2가
    둘 다 자연 생략된다. 이 생략의 안전성은 dispatch의 INV-5(δB)에 의존한다:
    빈-scope light는 merge∈{never,manual}일 때만 통과(_light_allowed). enforce flip
    전까지 이 결합이 유일 방어선.
    """
    prompt = _build_empty_scope_prompt(task)
    try:
        raw = _get_router_llm().generate_json(prompt)
    except Exception as exc:
        return _fallback_decision(f"empty-scope LLM error: {exc}")

    decision = _validate_raw(raw)
    if decision is None:
        return _fallback_decision(f"empty-scope invalid LLM response: {raw!r}")

    # marker만 부착하고 반환. light 자격(0.82 + light-stages)은 is_light()가 marker를
    # 보고 단일 판정(외부리뷰 #5). conf 낮은 결정도 marker 단 채 반환 → is_light()=False
    # → full. _fallback_decision으로 덮지 않아 LLM 실판단이 state.route_decision에 보존.
    decision.markers = [ROUTE_MARKER_SCOPE_UNCERTAIN]
    return decision


def _build_prompt(task: str, changed_files: list[str], tier_hint: dict[str, int]) -> str:
    files_section = "\n".join(f"  - {f} (Tier {tier_hint.get(f, '?')})" for f in changed_files) or "  (없음)"
    stage_list = ", ".join(STAGE_VOCAB)
    light_list = ", ".join(sorted(LIGHT_STAGES))

    return f"""You are a task-complexity classifier for the Agent Factory codebase.

## Task
{task}

## Intended scope files (derived from task, not guaranteed exhaustive)
{files_section}

## Step-by-step reasoning (follow these steps before outputting JSON)

Step 1 — Leaf check:
  Is this a PURE LEAF implementation? Criteria: adds/changes a single function with NO API
  or contract changes, no design decisions needed.
  Answer: YES or NO

Step 2 — Stage necessity:
  Which stages are GENUINELY needed?
  - research: only if external knowledge or API discovery is needed
  - design: only if architecture or interface decisions must be made first
  - plan: almost always needed before implementation
  - implement: needed if any code changes
  - test: needed if any code changes
  - review: needed if Tier-2+ files or non-trivial logic
  - cross_review: needed if Tier-3 files or cross-cutting concerns

Step 3 — Confidence:
  How certain are you given the scope files?
  If uncertain or multi-system, set confidence < 0.5.

Step 4 — Decision:
  Pure-leaf (YES in Step 1) + clear scope → confidence ≥ 0.70.
  Ambiguous or multi-system → confidence < 0.50.

## Output (JSON block only — no text before or after)
```json
{{
  "isolation": "<one of {list(ISOLATION_LEVELS)}>",
  "required_stages": ["<subset of [{stage_list}] in execution order>"],
  "review_depth": "<none | standard | deep>",
  "confidence": <float 0.0-1.0>,
  "reason": "<1-2 sentences summarizing your conclusion>"
}}
```

## Additional rules
- Pure leaf (YES in Step 1): required_stages = [{light_list}] only.
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
        return _classify_empty_scope(task, workspace)  # Phase 1: LLM path, 빈-scope early fallback 대체

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
