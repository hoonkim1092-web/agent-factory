"""
Generate work-item markdown documents from planning artifacts.
"""
from __future__ import annotations

import concurrent.futures as cf
import inspect as _inspect
import json
import logging
import os
import re
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.approval_gate import ApprovalGate
from core.document_policy import parse_frontmatter_exempt, scan_forbidden_tokens
from core.file_io import write_text
from core.utils import now_iso
from core.work_item_telemetry import write_initial_record

_LOGGER = logging.getLogger(__name__)
_PLACEHOLDER_REFINE_MAX = 2

TOTAL_BUDGET = 600.0  # v1 300s → v2 600s
STAGE_BUDGET: dict[int, float] = {
    1: 90.0,   # plan: 실측 63s → 90s
    2: 400.0,  # spec+design 병렬: 실측 352s → 400s
    3: 110.0,  # tasks: 미측정, plan 수준 + α
}

_SECTION_HEADER_RE = re.compile(r"^\s*##\s+(.+?)\s*$")
_TOC_PATTERNS = ("toc", "table of contents", "목차")


def _build_full_run_id(base_run_id: str, doc_type: str) -> str:
    nonce = uuid.uuid4().hex[:8]
    return f"{base_run_id or 'claude_cli_run'}_{doc_type}_{os.getpid()}_{time.time_ns()}_{nonce}"


@dataclass
class DocGenerationResult:
    doc_type: str
    content: str
    provider_id: str = ""
    model: str = ""
    elapsed_sec: float = 0.0
    used_fallback: bool = False
    timeout_fallback: bool = False
    placeholder_refine_attempts: int = 0
    # t1_refine_attempts는 generator dump 이후 project_pipeline T1 retry 시 atomic update
    t1_refine_attempts: int = 0
    errors: list = field(default_factory=list)
    run_id: str = ""
    usage_tokens: dict = field(default_factory=dict)

TEMPLATE_DIR_REL = os.path.join("docs", "work-items", "_template")
WORK_ITEMS_DIR_REL = os.path.join("docs", "work-items")


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _clean_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [_clean(v) for v in values if _clean(v)]


def _trim_text(value: Any, limit: int = 220) -> str:
    text = _clean(value)
    if len(text) <= limit:
        return text
    return text[: max(limit - 3, 0)].rstrip() + "..."


def _research_bullets(project_brief: dict[str, Any], limit: int = 8) -> str:
    lines: list[str] = []
    for item in _clean_list(project_brief.get("evidence_summary"))[:limit]:
        lines.append(f"- {item}")
    if not lines:
        for item in _clean_list(project_brief.get("research_notes"))[:limit]:
            lines.append(f"- {item}")
    notebook_summary = _trim_text(project_brief.get("notebook_summary"), limit=280)
    if notebook_summary and not any("NotebookLM" in line for line in lines):
        lines.append(f"- NotebookLM: {notebook_summary}")
    return "\n".join(lines[:limit]) if lines else "- (additional research needed)"


def _reference_bullets(project_brief: dict[str, Any], limit: int = 8) -> str:
    lines: list[str] = []
    seen: set[str] = set()

    for item in project_brief.get("local_references") or []:
        if not isinstance(item, dict):
            continue
        label = _clean(item.get("path") or item.get("title"))
        detail = _trim_text(item.get("heading") or item.get("excerpt"), limit=180)
        if not label:
            continue
        line = f"- Local: {label}"
        if detail:
            line += f" | {detail}"
        if line not in seen:
            seen.add(line)
            lines.append(line)
        if len(lines) >= limit:
            return "\n".join(lines)

    for item in project_brief.get("web_references") or []:
        if not isinstance(item, dict):
            continue
        label = _clean(item.get("title") or item.get("url"))
        detail = _trim_text(item.get("excerpt"), limit=180)
        if not label:
            continue
        line = f"- Web: {label}"
        if detail:
            line += f" | {detail}"
        if line not in seen:
            seen.add(line)
            lines.append(line)
        if len(lines) >= limit:
            return "\n".join(lines)

    for item in project_brief.get("llm_prior_references") or []:
        if not isinstance(item, dict):
            continue
        # producer(researcher._collect_llm_prior_knowledge)가 title에 "[LLM prior] " prefix를
        # 이미 부착하므로(researcher.py:630), bullet 라인 prefix와 중복되지 않게 strip한다.
        raw_label = _clean(item.get("title") or item.get("url"))
        label = raw_label[len("[LLM prior] "):] if raw_label.startswith("[LLM prior] ") else raw_label
        detail = _trim_text(item.get("excerpt"), limit=180)
        if not label:
            continue
        line = f"- LLM prior: {label}"
        if detail:
            line += f" | {detail}"
        if line not in seen:
            seen.add(line)
            lines.append(line)
        if len(lines) >= limit:
            return "\n".join(lines)

    return "\n".join(lines) if lines else "- (no additional references)"


def _slug_from_goal(goal: str) -> str:
    text = goal.lower()[:60]
    text = re.sub("[^a-z0-9\\uac00-\\ud7a3\\s]", " ", text)
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "work-item"


def _make_checklist(tasks: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    from core.project_task_board import _PHASE_ORDER as phase_order  # 단일 진실원천
    sorted_tasks = sorted(
        tasks,
        key=lambda item: (
            phase_order.get(_clean(item.get("phase") or "build"), 99),
            _clean(item.get("task_id") or ""),
        ),
    )
    for task in sorted_tasks:
        title = _clean(task.get("title") or task.get("instruction") or "")
        if not title:
            continue
        task_id = _clean(task.get("task_id") or "")
        owner = _clean(task.get("owner_role") or "")
        phase = _clean(task.get("phase") or "build")
        acceptance = _clean_list(task.get("acceptance"))
        artifacts = _clean_list(task.get("artifacts"))
        depends = _clean_list(task.get("depends_on"))
        e2e_command = _clean(task.get("e2e_command") or "")

        lines.append(f"- [ ] {title}")
        if task_id:
            lines.append(f"  - task_id: {task_id}")
        if owner:
            lines.append(f"  - owner_role: {owner}")
        lines.append(f"  - phase: {phase}")
        if depends:
            lines.append(f"  - depends_on: {', '.join(depends)}")
        if acceptance:
            lines.append(f"  - acceptance: {'; '.join(acceptance)}")
        if artifacts:
            lines.append(f"  - artifacts: {', '.join(artifacts)}")
        lines.append(f"  - e2e_command: {e2e_command or '(needs_backfill)'}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _fallback_feature_plan(
    work_item: str,
    project_brief: dict[str, Any],
    role_plan: dict[str, Any],
) -> str:
    goal = _clean(project_brief.get("goal") or "")
    background_context = _clean(project_brief.get("background_context") or "")
    problem_statement = _clean(project_brief.get("problem_statement") or "")
    deliverables = _clean_list(project_brief.get("deliverables"))
    constraints = _clean_list(project_brief.get("constraints"))
    risks = _clean_list(project_brief.get("risks"))
    non_goals = _clean_list(project_brief.get("non_goals"))
    modules = [m for m in (role_plan.get("modules") or []) if isinstance(m, dict)]
    roles = [r for r in (role_plan.get("roles") or []) if isinstance(r, dict)]

    # Scope: module name + summary (1줄)
    scope_lines = "\n".join(
        f"- **{_clean(m.get('name'))}**: {_trim_text(m.get('summary'), 120)}"
        for m in modules if _clean(m.get("name"))
    )
    deliverables_lines = "\n".join(f"- {item}" for item in deliverables) if deliverables else "- (auto-generate needed)"

    # Non-Goals: brief에서 가져오고 없으면 placeholder
    non_goals_lines = "\n".join(f"- {item}" for item in non_goals) if non_goals else "- (edit required)"

    # Stakeholders: 역할 이름 + 목적
    stakeholder_lines = "\n".join(
        f"- {_clean(r.get('name') or r.get('id'))}: {_trim_text(r.get('objective'), 80)}"
        for r in roles if _clean(r.get("name") or r.get("id"))
    ) or "- (auto-generate needed)"

    # Success Metrics: deliverable별 측정 기준 (Goals와 다른 관점)
    metrics_lines = "\n".join(
        f"- {item} — 완성 및 동작 검증됨" for item in deliverables
    ) if deliverables else "- (edit required)"

    # Risks: brief.risks + constraints 합산
    risk_items = risks + [c for c in constraints if any(kw in c for kw in ["제약", "불가", "없이", "미연결", "캐시"])]
    risks_lines = "\n".join(f"- {item}" for item in risk_items) if risk_items else "\n".join(f"- {item}" for item in constraints) if constraints else "- none"

    research_lines = _research_bullets(project_brief)
    reference_lines = _reference_bullets(project_brief)

    return (
        "# Feature Plan\n\n"
        "## Metadata\n\n"
        f"- work_item: {work_item}\n"
        "- owner: (edit required)\n"
        "- status: draft\n"
        f"- last_updated: {now_iso()}\n\n"
        "## Background\n\n"
        f"{background_context or goal or '(additional summary needed)'}\n\n"
        "## Problem Statement\n\n"
        f"{problem_statement or '(edit required)'}\n\n"
        "## Goals\n\n"
        f"{deliverables_lines}\n\n"
        "## Non-Goals\n\n"
        f"{non_goals_lines}\n\n"
        "## Scope\n\n"
        f"{scope_lines or '- (auto-generate needed)'}\n\n"
        "## Stakeholders\n\n"
        f"{stakeholder_lines}\n\n"
        "## Success Metrics\n\n"
        f"{metrics_lines}\n\n"
        "## Risks and Assumptions\n\n"
        f"{risks_lines}\n\n"
        "## Evidence\n\n"
        f"{research_lines}\n\n"
        "## References\n\n"
        f"{reference_lines}\n\n"
        "## Approval Request\n\n"
        "- Review this scope and confirm approval-gate.md when ready.\n"
    )


def _fallback_feature_spec(
    work_item: str,
    project_brief: dict[str, Any],
    role_plan: dict[str, Any],
    task_board: dict[str, Any],
) -> str:
    goal = _clean(project_brief.get("goal") or "")
    modules = [m for m in (role_plan.get("modules") or []) if isinstance(m, dict)]
    all_tasks = [t for t in (task_board.get("tasks") or []) if isinstance(t, dict)]
    user_flows = _clean_list(project_brief.get("user_flows"))
    constraints = _clean_list(project_brief.get("constraints"))
    non_goals = _clean_list(project_brief.get("non_goals"))
    data_model = project_brief.get("data_model") or []
    research_lines = _research_bullets(project_brief)
    reference_lines = _reference_bullets(project_brief)

    # User Scenarios: brief.user_flows 우선, 없으면 module summary 활용
    if user_flows:
        scenario_lines = [f"- {flow}" for flow in user_flows]
    else:
        scenario_lines = []
        for module in modules:
            summary = _clean(module.get("summary") or "")
            if summary:
                scenario_lines.append(f"- {summary}")
    scenario_text = "\n".join(scenario_lines) or "- (edit required)"

    # Functional Requirements: feature_slices (구체적 구현 단위)
    req_lines: list[str] = []
    for module in modules:
        name = _clean(module.get("name") or "")
        slices = _clean_list(module.get("feature_slices"))
        if slices:
            for item in slices:
                req_lines.append(f"- [{name}] {item}")
        elif name:
            summary = _clean(module.get("summary") or "")
            req_lines.append(f"- [{name}] {summary or name}")
    req_text = "\n".join(req_lines) or "- (auto-generate needed)"

    # Non-Functional Requirements: constraints 중 비기능 항목 추출
    nfr_keywords = ["성능", "속도", "보안", "안정", "오프라인", "캐시", "용량", "호환", "인터넷 없이", "단독 실행"]
    nfr_lines = [f"- {c}" for c in constraints if any(kw in c for kw in nfr_keywords)]
    nfr_text = "\n".join(nfr_lines) if nfr_lines else "- (edit required)"

    # Inputs / Outputs: data_model에서 생성
    io_lines: list[str] = []
    for entity in (data_model if isinstance(data_model, list) else []):
        if not isinstance(entity, dict):
            continue
        ename = _clean(entity.get("entity") or "")
        fields = _clean_list(entity.get("fields"))
        storage = _clean(entity.get("storage") or "")
        if ename:
            field_str = ", ".join(fields[:6]) if fields else "—"
            io_lines.append(f"- **{ename}** [{storage}]: {field_str}")
    io_text = "\n".join(io_lines) if io_lines else "- (edit required)"

    # Acceptance Criteria: build/verify 태스크의 acceptance만 (scope 제외)
    acceptance_lines: list[str] = []
    for task in all_tasks:
        if _clean(task.get("phase") or "") == "scope":
            continue
        for acc in _clean_list(task.get("acceptance")):
            bullet = f"- {acc}"
            if bullet not in acceptance_lines:
                acceptance_lines.append(bullet)
    acceptance_text = "\n".join(acceptance_lines) or "- (auto-generate needed)"

    # Out Of Scope
    out_of_scope_text = "\n".join(f"- {item}" for item in non_goals) if non_goals else "- (edit required)"

    return (
        "# Feature Spec\n\n"
        "## Metadata\n\n"
        f"- work_item: {work_item}\n"
        "- source_plan: feature-plan.md\n"
        "- status: draft\n"
        f"- last_updated: {now_iso()}\n\n"
        "## Feature Overview\n\n"
        f"{goal or '(edit required)'}\n\n"
        "## User Scenarios\n\n"
        f"{scenario_text}\n\n"
        "## Functional Requirements\n\n"
        f"{req_text}\n\n"
        "## Non-Functional Requirements\n\n"
        f"{nfr_text}\n\n"
        "## Inputs and Outputs\n\n"
        f"{io_text}\n\n"
        "## Exceptions and Failure Scenarios\n\n"
        "- (edit required)\n\n"
        "## Existing Behavior To Preserve\n\n"
        "- (edit required)\n\n"
        "## Acceptance Criteria\n\n"
        f"{acceptance_text}\n\n"
        "## Evidence\n\n"
        f"{research_lines}\n\n"
        "## References\n\n"
        f"{reference_lines}\n\n"
        "## Out Of Scope\n\n"
        f"{out_of_scope_text}\n"
    )


def _fallback_impl_design(
    work_item: str,
    project_brief: dict[str, Any],
    role_plan: dict[str, Any],
) -> str:
    goal = _clean(project_brief.get("goal") or "")
    modules = [m for m in (role_plan.get("modules") or []) if isinstance(m, dict)]
    execution_strategy = _clean(role_plan.get("execution_strategy") or "parallel")
    tech_stack = _clean_list(project_brief.get("tech_stack"))
    architecture_style = _clean(project_brief.get("architecture_style") or "")
    data_model = project_brief.get("data_model") or []
    risks = _clean_list(project_brief.get("risks"))
    constraints = _clean_list(project_brief.get("constraints"))
    research_lines = _research_bullets(project_brief)
    reference_lines = _reference_bullets(project_brief)

    # Design Summary: goal + architecture + tech stack
    tech_str = ", ".join(tech_stack) if tech_stack else ""
    design_summary_parts = [goal or "(edit required)"]
    if architecture_style:
        design_summary_parts.append(f"아키텍처: {architecture_style}")
    if tech_str:
        design_summary_parts.append(f"기술 스택: {tech_str}")
    design_summary_parts.append(f"실행 전략: {execution_strategy}")
    design_summary = "\n\n".join(design_summary_parts)

    # Planned Modules
    module_lines: list[str] = []
    for module in modules:
        name = _clean(module.get("name") or "")
        owner = _clean(module.get("owner_role") or "")
        summary = _clean(module.get("summary") or "")
        depends = _clean_list(module.get("depends_on"))
        delivs = _clean_list(module.get("deliverables"))
        slices = _clean_list(module.get("feature_slices"))
        if name:
            module_lines.append(f"### {name}")
            module_lines.append(f"- owner: {owner}")
            module_lines.append(f"- objective: {summary}")
            if depends:
                module_lines.append(f"- depends_on: {', '.join(depends)}")
            if delivs:
                module_lines.append(f"- deliverables: {', '.join(delivs)}")
            if slices:
                module_lines.append(f"- feature_slices: {', '.join(slices)}")
            module_lines.append("")
    module_text = "\n".join(module_lines) or "- (auto-generate needed)"

    # Data Flow: 실제 depends_on 기반 화살표
    # 먼저 id→name 맵 생성
    id_to_name = {_clean(m.get("id") or ""): _clean(m.get("name") or "") for m in modules if _clean(m.get("id") or "")}
    flow_lines: list[str] = []
    for module in modules:
        name = _clean(module.get("name") or "")
        depends = _clean_list(module.get("depends_on"))
        dep_names = [id_to_name.get(d, d) for d in depends if d]
        if dep_names:
            flow_lines.append(f"- {' + '.join(dep_names)} → **{name}**")
        else:
            flow_lines.append(f"- (시작) → **{name}**")
    flow_text = "\n".join(flow_lines) or "- (auto-generate needed)"

    # State / Data Model
    data_model_lines: list[str] = []
    for entity in (data_model if isinstance(data_model, list) else []):
        if not isinstance(entity, dict):
            continue
        ename = _clean(entity.get("entity") or "")
        fields = _clean_list(entity.get("fields"))
        storage = _clean(entity.get("storage") or "")
        if ename:
            field_str = ", ".join(fields) if fields else "—"
            data_model_lines.append(f"- **{ename}** ({storage}): {field_str}")
    data_model_text = "\n".join(data_model_lines) if data_model_lines else "- (edit required)"

    # Risks: brief.risks + 기술적 constraints
    risk_items = list(risks)
    for c in constraints:
        if any(kw in c for kw in ["불가", "없이", "캐시", "실패", "오류", "제약"]):
            risk_items.append(c)
    risks_text = "\n".join(f"- {r}" for r in risk_items) if risk_items else "- (edit required)"

    # Event Sequence / Phase Flow: domain_specs_summary.state_machine 우선 사용
    _specs_sum = project_brief.get("domain_specs_summary") or {}
    _state_machine = _clean(_specs_sum.get("state_machine") or "")
    if _state_machine:
        _phase_text = _state_machine[:800]  # 프롬프트 크기 제한
    else:
        _phase_text = (
            "- **Phase 1 — 초기화**: 시스템 준비 및 의존성 설정\n"
            "- **Phase 2 — 입력 수신**: 사용자/외부 이벤트 수신 및 유효성 검사\n"
            "- **Phase 3 — 핵심 처리**: 비즈니스 로직 실행 및 상태 전환\n"
            "- **Phase 4 — 결과 반환**: 처리 결과 직렬화 및 응답 전송"
        )

    return (
        "# Implementation Design\n\n"
        "## Metadata\n\n"
        f"- work_item: {work_item}\n"
        "- spec_type: feature\n"
        "- source_spec: feature-spec.md\n"
        "- status: draft\n"
        f"- last_updated: {now_iso()}\n\n"
        "## Design Summary\n\n"
        f"{design_summary}\n\n"
        "## Planned Modules\n\n"
        f"{module_text}\n\n"
        "## Data Flow\n\n"
        f"{flow_text}\n\n"
        "## Event Sequence / Phase Flow\n\n"
        f"{_phase_text}\n\n"
        "## Interface Impact\n\n"
        "- (edit required)\n\n"
        "## State And Data Model\n\n"
        f"{data_model_text}\n\n"
        "## Compatibility Considerations\n\n"
        "- (edit required)\n\n"
        "## Migration Requirement\n\n"
        "- none\n\n"
        "## Risks\n\n"
        f"{risks_text}\n\n"
        "## Alternatives Considered\n\n"
        "- (edit required)\n\n"
        "## Design Evidence\n\n"
        f"{research_lines}\n\n"
        "## References\n\n"
        f"{reference_lines}\n\n"
        "## Test Strategy\n\n"
        "- Unit tests per module\n"
        "- Integration tests for cross-module flows\n"
    )


def _fallback_impl_tasks(
    work_item: str,
    project_brief: dict[str, Any] | None,
    role_plan: dict[str, Any],
    task_board: dict[str, Any],
) -> str:
    tasks = [t for t in (task_board.get("tasks") or []) if isinstance(t, dict)]
    modules = [m for m in (role_plan.get("modules") or []) if isinstance(m, dict)]
    preconditions = [
        _clean(step.get("name") or "")
        for step in (role_plan.get("planning_steps") or [])
        if isinstance(step, dict) and _clean(step.get("name"))
    ]
    brief = project_brief if isinstance(project_brief, dict) else {}
    research_lines = _research_bullets(brief)

    pre_lines = "\n".join(f"- {item}" for item in preconditions) if preconditions else "- none"
    blocked = [
        _clean(module.get("name") or "")
        for module in modules
        if isinstance(module, dict) and _clean_list(module.get("depends_on"))
    ]
    blocker_lines = "\n".join(f"- {item}" for item in blocked) if blocked else "- none"
    checklist = _make_checklist(tasks) or "- [ ] (edit required)"

    return (
        "# Implementation Tasks\n\n"
        "## Metadata\n\n"
        f"- work_item: {work_item}\n"
        "- source_design: implementation-design.md\n"
        "- status: draft\n"
        f"- last_updated: {now_iso()}\n\n"
        "## Preconditions\n\n"
        f"{pre_lines}\n\n"
        "## Task Evidence\n\n"
        f"{research_lines}\n\n"
        "## Task List\n\n"
        f"{checklist}\n\n"
        "## Blockers\n\n"
        f"{blocker_lines}\n\n"
        "## Rollback Sign-Off\n\n"
        "- Commit after each module-level implementation milestone\n\n"
        "## Definition Of Done\n\n"
        "- All task checkboxes are complete\n"
        "- verification-report.md 작성 완료 (`templates/verify-handoff.md.tpl` 참고)\n"
        "  - `e2e_command:` 필드에 실행 명령어 기재\n"
        "  - `- verdict:` 필드에 PASS/WARN/BLOCK 기재\n"
    )


def _generate_doc_with_llm(
    prompt: str,
    fallback_fn,
    doc_type: str = "",
    run_id: str = "",
    timeout_sec: int = 120,
    workspace: str = "",
) -> DocGenerationResult:
    """LLM 문서 생성 시도. 실패/빈 응답 시 fallback_fn()으로 폴백."""
    try:
        from core.requirement_llm import execute_document_prompt
        result = execute_document_prompt(
            prompt,
            workspace=workspace or None,
            run_id=run_id,
            timeout_sec=timeout_sec,
        )
        if result.get("ok") and result.get("text"):
            return DocGenerationResult(
                doc_type=doc_type,
                content=result["text"],
                provider_id=result.get("provider_id", ""),
                model=result.get("model", ""),
                elapsed_sec=result.get("elapsed_sec", 0.0),
                used_fallback=False,
                errors=result.get("errors") or [],
                run_id=run_id,
                usage_tokens=result.get("usage_tokens") or {},
            )
        errors = result.get("errors") or []
        _LOGGER.warning("LLM 문서 생성 실패 — 폴백 사용. errors=%s", errors)
        return DocGenerationResult(
            doc_type=doc_type,
            content=fallback_fn(),
            used_fallback=True,
            errors=errors,
            run_id=run_id,
        )
    except Exception as exc:
        _LOGGER.warning("LLM 문서 생성 예외 — 폴백 사용: %s", exc)
        return DocGenerationResult(
            doc_type=doc_type,
            content=fallback_fn(),
            provider_id="fallback",
            model="static",
            used_fallback=True,
            errors=[f"{type(exc).__name__}:{exc}"],
            run_id=run_id,
        )


def _generate_feature_plan(
    work_item: str,
    project_brief: dict[str, Any],
    role_plan: dict[str, Any],
    *,
    prev_plan: str = "",
    run_id: str = "",
    timeout_sec: int = 120,
    workspace: str = "",
) -> DocGenerationResult:
    goal = _clean(project_brief.get("goal") or "")
    deliverables = _clean_list(project_brief.get("deliverables"))
    constraints = _clean_list(project_brief.get("constraints"))

    prompt = (
        "Create a feature-plan.md document for this work item.\n\n"
        f"## Input\n"
        f"- Brief:\n{json.dumps(project_brief, ensure_ascii=False)}\n"
        f"- Role Plan:\n{json.dumps(role_plan, ensure_ascii=False)}\n"
        + (f"- Previous Draft:\n{prev_plan}\n" if prev_plan else "")
        + "\n## Output Format\nReturn a complete markdown document:\n\n"
        "# Feature Plan\n\n"
        "## Metadata\n(work_item, owner, status, last_updated)\n\n"
        "## Background\n\n## Problem Statement\n\n## Goals\n\n"
        "## Non-Goals\n\n## Scope\n\n## Stakeholders\n\n"
        "## Success Metrics\n\n## Risks and Assumptions\n\n"
        "## Evidence\n\n## References\n\n## Approval Request\n\n"
        "Rules:\n"
        "- 한국어로 작성\n"
        "- \"(edit required)\" 사용 금지\n"
        f"- work_item: {work_item}\n"
        f"- Goal: {goal}\n"
        f"- Deliverables: {', '.join(deliverables)}\n"
        f"- Constraints: {', '.join(constraints)}"
    )

    def _fb() -> str:
        return _fallback_feature_plan(work_item, project_brief, role_plan)

    return _generate_doc_with_llm(prompt, _fb, doc_type="plan",
                                   run_id=run_id, timeout_sec=timeout_sec, workspace=workspace)


def _generate_feature_spec(
    work_item: str,
    project_brief: dict[str, Any],
    role_plan: dict[str, Any],
    task_board: dict[str, Any],
    *,
    prev_plan: str = "",
    run_id: str = "",
    timeout_sec: int = 120,
    workspace: str = "",
) -> DocGenerationResult:
    goal = _clean(project_brief.get("goal") or "")

    prompt = (
        "Create a feature-spec.md document for this work item.\n\n"
        f"## Input\n"
        f"- Brief:\n{json.dumps(project_brief, ensure_ascii=False)}\n"
        f"- Role Plan:\n{json.dumps(role_plan, ensure_ascii=False)}\n"
        f"- Task Board:\n{json.dumps(task_board, ensure_ascii=False)}\n"
        + (f"- Feature Plan:\n{prev_plan}\n" if prev_plan else "")
        + "\n## Output Format\nReturn a complete markdown document:\n\n"
        "# Feature Spec\n\n"
        "## Metadata\n(work_item, source_plan, status, last_updated)\n\n"
        "## Feature Overview\n\n## User Scenarios\n\n"
        "## Functional Requirements\n\n## Non-Functional Requirements\n\n"
        "## Inputs and Outputs\n\n## Exceptions and Failure Scenarios\n\n"
        "## Existing Behavior To Preserve\n\n## Acceptance Criteria\n\n"
        "## Evidence\n\n## References\n\n## Out Of Scope\n\n"
        "Rules:\n"
        "- 한국어로 작성\n"
        "- \"(edit required)\" 사용 금지\n"
        "- Acceptance Criteria는 검증 가능한 문장으로\n"
        f"- work_item: {work_item}, goal: {goal}"
    )

    def _fb() -> str:
        return _fallback_feature_spec(work_item, project_brief, role_plan, task_board)

    return _generate_doc_with_llm(prompt, _fb, doc_type="spec",
                                   run_id=run_id, timeout_sec=timeout_sec, workspace=workspace)


def _generate_implementation_design(
    work_item: str,
    project_brief: dict[str, Any],
    role_plan: dict[str, Any],
    *,
    prev_plan: str = "",
    prev_spec: str = "",
    run_id: str = "",
    timeout_sec: int = 120,
    workspace: str = "",
) -> DocGenerationResult:
    goal = _clean(project_brief.get("goal") or "")

    # finding #5: prev_spec 우선, 없으면 prev_plan 블록 (Stage 2 병렬용)
    if prev_spec:
        prev_block = f"- Feature Spec:\n{prev_spec}\n"
    elif prev_plan:
        prev_block = (
            f"- Feature Plan:\n{prev_plan}\n"
            f"  (Note: Feature Spec is being generated in parallel; "
            f"derive design from Feature Plan goals/scope only.)\n"
        )
    else:
        prev_block = ""

    prompt = (
        "Create an implementation-design.md document for this work item.\n\n"
        f"## Input\n"
        f"- Brief:\n{json.dumps(project_brief, ensure_ascii=False)}\n"
        f"- Role Plan:\n{json.dumps(role_plan, ensure_ascii=False)}\n"
        + prev_block
        + "\n## Output Format\nReturn a complete markdown document:\n\n"
        "# Implementation Design\n\n"
        "## Metadata\n(work_item, spec_type, source_spec, status, last_updated)\n\n"
        "## Design Summary\n\n## Planned Modules\n\n## Data Flow\n\n"
        "## Event Sequence / Phase Flow\n"
        "(시스템 전체 실행 흐름을 단계별로 기술. 각 Phase: 이름 / 진입 조건 / 핵심 이벤트 / 다음 Phase 전환 트리거. "
        "domain_specs_summary의 state_machine이 있으면 반드시 반영할 것. 최소 4개 Phase 이상.)\n\n"
        "## Interface Impact\n\n## State And Data Model\n\n"
        "## Compatibility Considerations\n\n## Migration Requirement\n\n"
        "## Risks\n\n## Alternatives Considered\n\n"
        "## Design Evidence\n\n## References\n\n## Test Strategy\n\n"
        "Rules:\n"
        "- 한국어로 작성\n"
        "- \"(edit required)\" 사용 금지\n"
        "- 기술 선택 근거 포함\n"
        "- Event Sequence / Phase Flow는 반드시 작성 (생략 불가)\n"
        f"- work_item: {work_item}, goal: {goal}"
    )

    def _fb() -> str:
        return _fallback_impl_design(work_item, project_brief, role_plan)

    return _generate_doc_with_llm(prompt, _fb, doc_type="design",
                                   run_id=run_id, timeout_sec=timeout_sec, workspace=workspace)


def _generate_implementation_tasks(
    work_item: str,
    project_brief: dict[str, Any] | None,
    role_plan: dict[str, Any],
    task_board: dict[str, Any],
    *,
    prev_design: str = "",
    prev_spec_outline: str = "",
    run_id: str = "",
    timeout_sec: int = 120,
    workspace: str = "",
) -> DocGenerationResult:
    brief = project_brief if isinstance(project_brief, dict) else {}

    spec_outline_block = (
        f"- Feature Spec Outline (refer with §N for traceability):\n{prev_spec_outline}\n"
        if prev_spec_outline else ""
    )

    prompt = (
        "You are a technical project manager creating an implementation task breakdown.\n\n"
        f"## Input\n"
        f"- Role Plan:\n{json.dumps(role_plan, ensure_ascii=False)}\n"
        f"- Task Board:\n{json.dumps(task_board, ensure_ascii=False)}\n"
        + (f"- Implementation Design:\n{prev_design}\n" if prev_design else "")
        + spec_outline_block
        + f"- Brief:\n{json.dumps(brief, ensure_ascii=False)}\n\n"
        "## Output Format\nReturn a complete markdown document:\n\n"
        "# Implementation Tasks\n\n"
        "## Metadata\n(work_item, source_design, status, last_updated)\n\n"
        "## Preconditions\n\n"
        "## Task Evidence\n\n"
        "## Task List\n"
        "(각 태스크: - [ ] 태스크 제목 / task_id: T-001 / owner_role / phase / depends_on / "
        "acceptance / artifacts / estimated_complexity / implementation_hint)\n\n"
        "## Blockers\n\n"
        "## Rollback Sign-Off\n\n"
        "## Definition Of Done\n\n"
        "Rules:\n"
        "- 한국어로 작성\n"
        "- \"(edit required)\" 사용 금지\n"
        "- 모든 태스크에 depends_on 포함 (없으면 빈 리스트)\n"
        "- acceptance는 검증 가능한 문장\n"
        "- Acceptance Criteria entries should reference spec §N when relevant\n"
        "- 태스크 순서: scope → build → integrate → verify\n"
        "- 태스크 ID는 T-001부터 순차 부여"
    )

    def _fb() -> str:
        return _fallback_impl_tasks(work_item, project_brief, role_plan, task_board)

    return _generate_doc_with_llm(prompt, _fb, doc_type="tasks",
                                   run_id=run_id, timeout_sec=timeout_sec, workspace=workspace)


def _extract_section_outline(markdown: str, expected_count: int = 12) -> str:
    """## 헤더만 뽑아 §N 형식 목차 반환. finding #12 해소."""
    lines = []
    section_idx = 0
    for raw in markdown.splitlines():
        m = _SECTION_HEADER_RE.match(raw)
        if not m:
            continue
        title = m.group(1)
        title = re.sub(r"[*_`]+", "", title).strip()
        title = re.sub(r"\s+", " ", title)
        if not title or title.lower() in _TOC_PATTERNS:
            continue
        section_idx += 1
        lines.append(f"§{section_idx} {title}")
    if section_idx != expected_count:
        _LOGGER.warning(
            "spec_outline section count mismatch: got=%d expected=%d", section_idx, expected_count,
        )
    return "\n".join(lines)


def _resolve_future_or_fallback(
    future: cf.Future,
    done_set: set,
    doc_type: str,
    fallback_factory,
) -> DocGenerationResult:
    if future in done_set:
        try:
            return future.result(timeout=0)
        except Exception as exc:
            return DocGenerationResult(
                doc_type=doc_type,
                content=fallback_factory(),
                used_fallback=True,
                errors=[f"{type(exc).__name__}:{exc}"],
            )
    return DocGenerationResult(
        doc_type=doc_type,
        content=fallback_factory(),
        used_fallback=True,
        timeout_fallback=True,
        errors=["stage2_deadline_exceeded"],
    )


def _exec_stage2(
    deadline: float,
    plan_content: str,
    work_item_id: str,
    project_brief: dict[str, Any],
    role_plan: dict[str, Any],
    task_board: dict[str, Any],
    base_run_id: str,
    workspace: str,
) -> tuple[DocGenerationResult, DocGenerationResult]:
    """spec / design 병렬 생성. 절대 deadline까지 기다리고, 미완료는 fallback으로 채움."""
    remaining = max(1.0, deadline - time.monotonic())
    llm_timeout = max(1, int(remaining) - 5)

    executor = cf.ThreadPoolExecutor(max_workers=2, thread_name_prefix="wi-stage2")
    try:
        fut_spec = executor.submit(
            _generate_and_refine, "spec", _generate_feature_spec,
            work_item_id, project_brief, role_plan, task_board,
            prev_plan=plan_content, run_id=base_run_id,
            timeout_sec=llm_timeout, workspace=workspace,
        )
        fut_design = executor.submit(
            _generate_and_refine, "design", _generate_implementation_design,
            work_item_id, project_brief, role_plan,
            prev_plan=plan_content, run_id=base_run_id,
            timeout_sec=llm_timeout, workspace=workspace,
        )

        done, _ = cf.wait(
            {fut_spec, fut_design},
            timeout=remaining,
            return_when=cf.ALL_COMPLETED,
        )

        spec_result = _resolve_future_or_fallback(
            fut_spec, done, "spec",
            lambda: _fallback_feature_spec(work_item_id, project_brief, role_plan, task_board),
        )
        design_result = _resolve_future_or_fallback(
            fut_design, done, "design",
            lambda: _fallback_impl_design(work_item_id, project_brief, role_plan),
        )
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    return spec_result, design_result


def _build_episode_hints_section(project_brief: dict[str, Any], workspace: str) -> str:
    """유사 과거 에피소드 힌트 섹션을 동기적으로 빌드한다 (Phase 4)."""
    if os.environ.get("AF_MEMORY_REPLAY", "1") == "0":
        return ""
    try:
        from core.memory_system.episode_matcher import EpisodeMatcher, _search_seed_episodes
        goal = _clean(project_brief.get("goal") or "")
        if not goal:
            return ""
        brief_text = f"{goal} {' '.join(_clean_list(project_brief.get('deliverables')))}"
        try:
            # P0-B fix: facade 주입 — 미주입 시 seed-only 모드로 폴백되어
            # 런타임 에피소드가 회상 경로에 들어오지 않음.
            try:
                from core.memory_system.facade import UnifiedMemoryFacade
                _facade = UnifiedMemoryFacade.get_instance()
                if not getattr(_facade, "_initialised", False):
                    _facade = None
            except Exception:
                _facade = None
            matcher = EpisodeMatcher(facade=_facade) if _facade else EpisodeMatcher()
            # _run_async_safe 사용 — 이미 running loop 안(orchestrator 컨텍스트)에서
            # 호출되어도 별도 스레드에서 실행되므로 RuntimeError로 떨어지지 않음.
            from core.agent_runner import _run_async_safe
            hits = _run_async_safe(matcher.query_similar(brief_text, top_k=5))
        except Exception:
            # 그래도 실패하면(초기화 오류 등) — 시드 전용 폴백
            hits = _search_seed_episodes(brief_text, top_k=5)
        if not hits:
            return ""
        lines = ["## Episode Hints\n"]
        lines.append("_과거 유사 프로젝트에서 학습된 주의사항:_\n")
        for hit in hits:
            for hint in hit.get("hints", []):
                lines.append(f"- {hint}")
        if len(lines) <= 2:
            return ""
        return "\n".join(lines) + "\n"
    except Exception as exc:
        _LOGGER.debug("episode hints 생성 실패 (무시): %s", exc)
        return ""


def generate_work_items(
    workspace: str,
    slug: str,
    project_brief: dict[str, Any],
    role_plan: dict[str, Any],
    task_board: dict[str, Any],
    run_id: str = "",
) -> dict[str, str]:
    # target_path가 있으면 프로젝트 디렉토리에 문서를 생성하고,
    # 없으면 기존처럼 workspace(agent-factory 내부)에 생성한다.
    target_path = _clean(project_brief.get("target_path") or "")
    if target_path and os.path.isabs(target_path):
        doc_root = os.path.abspath(target_path)
    else:
        doc_root = os.path.abspath(workspace)
    work_dir = os.path.join(doc_root, WORK_ITEMS_DIR_REL, slug)
    os.makedirs(work_dir, exist_ok=True)

    template_dir = os.path.join(os.path.abspath(workspace), TEMPLATE_DIR_REL)
    _copy_extra_templates(template_dir, work_dir)

    try:
        from core.cli_session_cleanup import cleanup_stale_sessions
        cleanup_stale_sessions(workspace, days=30)
    except Exception as _ce:
        _LOGGER.debug("cleanup_stale_sessions skip: %s", _ce)

    files: dict[str, str] = {}
    work_item_id = slug

    episode_hints_section = _build_episode_hints_section(project_brief, workspace)
    t_total_start = time.monotonic()

    # --- Stage 1: plan (sequential) ---
    llm_timeout_1 = max(1, int(STAGE_BUDGET[1]) - 5)
    plan_result = _generate_and_refine(
        "plan", _generate_feature_plan, work_item_id, project_brief, role_plan,
        run_id=run_id, timeout_sec=llm_timeout_1, workspace=workspace,
    )
    if episode_hints_section:
        plan_result.content = plan_result.content + "\n" + episode_hints_section
    plan_content = plan_result.content
    plan_path = os.path.join(work_dir, "feature-plan.md")
    write_text(plan_path, plan_content)
    files["feature-plan.md"] = plan_path

    elapsed_1 = time.monotonic() - t_total_start
    carry_over_1 = max(0.0, STAGE_BUDGET[1] - elapsed_1)
    if plan_result.used_fallback:
        _LOGGER.warning("Stage 1 fallback — Stage 2/3는 fallback plan을 prev로 사용")

    # --- Stage 2: spec + design (병렬) ---
    t_stage2_start = time.monotonic()
    budget_2 = STAGE_BUDGET[2] + carry_over_1
    deadline_2 = t_stage2_start + budget_2
    spec_result, design_result = _exec_stage2(
        deadline=deadline_2,
        plan_content=plan_content,
        work_item_id=work_item_id,
        project_brief=project_brief,
        role_plan=role_plan,
        task_board=task_board,
        base_run_id=run_id,
        workspace=workspace,
    )
    spec_content = spec_result.content
    spec_path = os.path.join(work_dir, "feature-spec.md")
    write_text(spec_path, spec_content)
    files["feature-spec.md"] = spec_path

    design_content = design_result.content
    design_path = os.path.join(work_dir, "implementation-design.md")
    write_text(design_path, design_content)
    files["implementation-design.md"] = design_path

    elapsed_2 = time.monotonic() - t_stage2_start
    carry_over_2 = max(0.0, budget_2 - elapsed_2)

    # --- Stage 3: tasks (sequential) ---
    budget_3 = STAGE_BUDGET[3] + carry_over_2
    llm_timeout_3 = max(1, int(budget_3) - 5)
    spec_outline = _extract_section_outline(spec_content)
    tasks_result = _generate_and_refine(
        "tasks", _generate_implementation_tasks, work_item_id, project_brief,
        role_plan, task_board,
        prev_design=design_content,
        prev_spec_outline=spec_outline,
        run_id=run_id, timeout_sec=llm_timeout_3, workspace=workspace,
    )
    tasks_content = tasks_result.content
    tasks_path = os.path.join(work_dir, "implementation-tasks.md")
    write_text(tasks_path, tasks_content)
    files["implementation-tasks.md"] = tasks_path

    # --- 텔레메트리 dump ---
    try:
        write_initial_record(workspace, slug, [plan_result, spec_result, design_result, tasks_result])
    except Exception as _te:
        _LOGGER.debug("telemetry dump skip: %s", _te)

    # e2e_command 누락 태스크 경고
    tasks_list = [t for t in (task_board.get("tasks") or []) if isinstance(t, dict)]
    missing_e2e = [
        _clean(t.get("task_id") or t.get("id") or "?")
        for t in tasks_list
        if not _clean(t.get("e2e_command") or "")
    ]
    if missing_e2e:
        _LOGGER.warning(
            "e2e_command 누락 task %d건 (needs_backfill 태그 부여): %s",
            len(missing_e2e), missing_e2e,
        )

    gate = ApprovalGate(doc_root, slug)
    gate.initialize(work_item_id, run_id=run_id)
    files["approval-gate.md"] = gate.gate_path

    return files


def _generate_and_refine(
    doc_type: str,
    generator_fn,
    work_item_id: str,
    project_brief: dict[str, Any],
    *extra_args,
    prev_plan: str = "",
    prev_spec: str = "",
    prev_design: str = "",
    prev_spec_outline: str = "",
    run_id: str = "",
    timeout_sec: int = 120,
    workspace: str = "",
) -> DocGenerationResult:
    """문서 생성 후 금지 토큰 스캔, 발견 시 LLM 보강 루프(최대 2회)를 수행한다."""
    placeholder_refine = os.environ.get("AF_PLACEHOLDER_REFINE", "1") != "0"

    # 설계 §3: 병렬 스레드 세션 파일 충돌 방지
    full_run_id = _build_full_run_id(run_id, doc_type)

    # explicit kwargs dispatch — introspection은 파라미터 존재 확인에만 사용 (마지막 인수 위치 가정 제거)
    sig_params = set(_inspect.signature(generator_fn).parameters)
    prev_kwargs: dict[str, str] = {}
    if "prev_plan" in sig_params and prev_plan:
        prev_kwargs["prev_plan"] = prev_plan
    if "prev_spec" in sig_params and prev_spec:
        prev_kwargs["prev_spec"] = prev_spec
    if "prev_design" in sig_params and prev_design:
        prev_kwargs["prev_design"] = prev_design
    if "prev_spec_outline" in sig_params and prev_spec_outline:
        prev_kwargs["prev_spec_outline"] = prev_spec_outline

    result: DocGenerationResult = generator_fn(
        work_item_id, project_brief, *extra_args,
        **prev_kwargs,
        run_id=full_run_id,
        timeout_sec=timeout_sec,
        workspace=workspace,
    )
    result.run_id = full_run_id
    result.doc_type = doc_type

    if not placeholder_refine:
        return result

    content = result.content
    exempt = parse_frontmatter_exempt(content)
    for attempt in range(_PLACEHOLDER_REFINE_MAX):
        found = scan_forbidden_tokens(content, exempt=exempt)
        if not found:
            break
        _LOGGER.info(
            "금지 토큰 발견 [%s] attempt=%d tokens=%s — LLM 보강 시도",
            doc_type, attempt, found,
        )
        feedback = (
            f"다음 금지 토큰을 제거하고 실제 내용으로 채워라: {found}. "
            f"project_brief의 {doc_type} 관련 필드를 참조해 구체적 내용을 생성하라. "
            "이미 채워진 섹션은 변경하지 마라."
        )
        refined = _refine_document(content, feedback, project_brief)
        if refined != content:
            content = refined
            result.placeholder_refine_attempts = attempt + 1
        else:
            break

    remaining = scan_forbidden_tokens(content, exempt=exempt)
    if remaining:
        _LOGGER.warning(
            "금지 토큰 %d회 보강 후에도 잔존 [%s]: %s — needs_human_review 태그 추가",
            _PLACEHOLDER_REFINE_MAX, doc_type, remaining,
        )
        content += "\n\n<!-- af:status=needs_human_review -->\n"

    result.content = content
    return result


def _refine_document(
    original: str,
    feedback: str,
    project_brief: dict[str, Any] | None = None,
) -> str:
    """
    교차검증 피드백을 반영하여 문서를 부분 수정한다.

    LLM에게 원본 문서 + 피드백 + 원천 데이터를 주고 수정본을 생성한다.
    원천 데이터(project_brief)도 함께 참조하여 문서↔원천 정합성을 유지한다.

    Args:
        original: 원본 마크다운 문서 내용
        feedback: Judge의 수정 지시 (ACCEPT 항목의 Action Required)
        project_brief: 원천 데이터 (정합성 검증용, 없으면 None)

    Returns:
        수정된 마크다운 문서 내용
    """
    try:
        from core.control_plane_llm import ControlPlaneLLM
    except ImportError:
        return original

    context_parts = [
        "[원본 문서]\n" + original,
        "\n\n[교차검증 수정 지시]\n" + feedback,
    ]
    if project_brief:
        import json
        brief_summary = json.dumps(project_brief, ensure_ascii=False, indent=2)[:2000]
        context_parts.append(
            "\n\n[원천 데이터 (project_brief) — 수정 후에도 이 데이터와 정합성을 유지하라]\n"
            + brief_summary
        )

    prompt = "\n".join(context_parts) + (
        "\n\n위 수정 지시를 반영하여 문서를 수정하라. "
        "수정 지시에 해당하지 않는 부분은 변경하지 마라. "
        "원천 데이터와의 정합성을 유지하라. "
        "마크다운 형식으로 전체 문서를 출력하라."
    )

    try:
        llm = ControlPlaneLLM()
        refined = llm.generate(prompt).strip()
        if refined and len(refined) > 100:
            return refined
    except Exception:
        pass

    return original


def _copy_extra_templates(template_dir: str, work_dir: str) -> None:
    if not os.path.isdir(template_dir):
        return
    extra = {"verification-report.md", "change-request.md", "bug-fix-spec.md"}
    for filename in extra:
        src = os.path.join(template_dir, filename)
        dst = os.path.join(work_dir, filename)
        if os.path.isfile(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)


def slug_from_brief(project_brief: dict[str, Any]) -> str:
    goal = _clean(project_brief.get("goal") or "")
    return _slug_from_goal(goal) if goal else "work-item"
