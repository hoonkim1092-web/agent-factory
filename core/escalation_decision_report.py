"""Escalation Decision Report — _decision.md + _decision.json writer.

leaf writer: core.warning_registry module-level import 금지.
core.escalation_evaluator 의 RunDecision/EscalationDecision만 import.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict

from core.escalation_evaluator import RunDecision
from core.utils import now_iso


def write_decision_report(
    decision: RunDecision,
    slug_dir: str,
    *,
    summary_last_updated: str,
) -> None:
    """_decision.md + _decision.json을 slug_dir에 원자적으로 작성."""
    _write_decision_json(decision, slug_dir, summary_last_updated=summary_last_updated)
    _write_decision_md(decision, slug_dir, summary_last_updated=summary_last_updated)


def write_error_decision(
    slug_dir: str,
    *,
    project_slug: str,
    summary_last_updated: str,
    error_repr: str,
) -> None:
    """evaluator 오류 시 fail-closed: block=True, reason="evaluator_error" 강제 작성."""
    payload = {
        "decision_schema_version": 1,
        "project_slug": project_slug,
        "last_updated": now_iso(),
        "generated_from_summary_last_updated": summary_last_updated,
        "escalation_phase": "P2",
        "block": True,
        "activate_phase": "P2",
        "blocking_rules": [],
        "reason": "evaluator_error",
        "rule_decisions": [],
        "summary_snapshot": {},
        "error": error_repr,
    }
    _atomic_write_json(os.path.join(slug_dir, "_decision.json"), payload)

    # _decision.md도 오류 상태로 작성
    md_lines = [
        f"# Escalation Decision — {project_slug}",
        "",
        f"- last_updated: {payload['last_updated']}",
        "- activate_phase: P2",
        "- block: true",
        "- blocking_rules: (evaluator error)",
        "- reason: evaluator_error",
        "",
        "## 오류",
        "",
        f"escalation evaluator 실행 중 오류 발생: {error_repr}",
        "",
        "**해소 방법**: `AF_SKIP_ESCALATION=1` 환경변수로 임시 우회하거나 오류를 수정하세요.",
    ]
    _atomic_write_text(os.path.join(slug_dir, "_decision.md"), "\n".join(md_lines) + "\n")


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _write_decision_json(
    decision: RunDecision,
    slug_dir: str,
    *,
    summary_last_updated: str,
) -> None:
    rule_decisions_list = []
    for d in decision.rule_decisions:
        entry = {
            "rule_id": d.rule_id,
            "block": d.block,
            "severity": d.severity,
            "reason": d.reason,
            "activate_at": d.activate_at,
        }
        rule_decisions_list.append(entry)

    payload = {
        "decision_schema_version": 1,
        "project_slug": decision.summary_snapshot.get("project_slug", ""),
        "last_updated": now_iso(),
        "generated_from_summary_last_updated": summary_last_updated,
        "escalation_phase": decision.activate_phase,
        "block": decision.block,
        "activate_phase": decision.activate_phase,
        "blocking_rules": decision.blocking_rules,
        "reason": decision.reason,
        "rule_decisions": rule_decisions_list,
        "summary_snapshot": decision.summary_snapshot,
    }
    _atomic_write_json(os.path.join(slug_dir, "_decision.json"), payload)


def _write_decision_md(
    decision: RunDecision,
    slug_dir: str,
    *,
    summary_last_updated: str,
) -> None:
    slug = decision.summary_snapshot.get("project_slug", os.path.basename(slug_dir))
    ts = now_iso()
    blocking_str = ", ".join(decision.blocking_rules) if decision.blocking_rules else "(없음)"

    lines = [
        f"# Escalation Decision — {slug}",
        "",
        f"- last_updated: {ts}",
        f"- activate_phase: {decision.activate_phase}",
        f"- block: {'true' if decision.block else 'false'}",
        f"- blocking_rules: {blocking_str}",
        f"- reason: {decision.reason}",
        "",
    ]

    if decision.block and decision.blocking_rules:
        lines.append("## 차단 근거")
        lines.append("")
        # by_rule from summary_snapshot 으로 phase별 집계 출력
        by_rule = (decision.summary_snapshot.get("by_rule") or {})
        for rule_id in decision.blocking_rules:
            lines.append(f"### {rule_id}")
            info = by_rule.get(rule_id) or {}
            by_phase = info.get("by_phase") or {}
            # block_when 정보는 rule_decisions에서 추출
            blocking_phases = [
                d for d in decision.rule_decisions
                if d.rule_id == rule_id and d.block
            ]
            exempt_phases = [
                d for d in decision.rule_decisions
                if d.rule_id == rule_id and not d.block and "exempt" in d.reason
            ]
            if blocking_phases:
                ph_counts = ", ".join(
                    f"{ph} ({by_phase.get(ph, '?')}건)"
                    for d in blocking_phases
                    for ph in [_extract_phase_from_decision_reason(d, by_phase)]
                    if ph
                )
                if ph_counts:
                    lines.append(f"- 매칭 phase: {ph_counts}")
            if exempt_phases:
                ex_ph = ", ".join(
                    d.reason.split("exempt_phase:")[-1]
                    for d in exempt_phases
                    if "exempt_phase:" in d.reason
                )
                if ex_ph:
                    lines.append(f"- exempt phase: {ex_ph}")
            lines.append("")
            lines.append(f"**해소 방법** (택 1):")
            lines.append(f"1. 각 task의 `e2e_command` 필드를 채운 후 work-item 문서 재생성")
            lines.append(
                f"2. `af warning-override --workspace . --slug {slug} --rule {rule_id} "
                f"--reason \"<이유>\"` 로 false-positive 표시"
            )
            lines.append(
                "3. `config/escalation_policy.yaml` 에서 `activate_at` 을 `never` 로 변경 "
                "(전역 비활성, 권장하지 않음)"
            )
            lines.append("")

    lines.append("## 평가된 모든 규칙")
    lines.append("")
    lines.append("| rule_id | block | severity | reason |")
    lines.append("|---------|-------|----------|--------|")
    seen_rules: set[str] = set()
    for d in decision.rule_decisions:
        key = f"{d.rule_id}:{d.reason}"
        if key in seen_rules:
            continue
        seen_rules.add(key)
        lines.append(f"| {d.rule_id} | {str(d.block).lower()} | {d.severity} | {d.reason} |")
    lines.append("")

    lines.append("## 부록: summary 스냅샷")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(decision.summary_snapshot, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")

    _atomic_write_text(os.path.join(slug_dir, "_decision.md"), "\n".join(lines))


def _extract_phase_from_decision_reason(d: "EscalationDecision", by_phase: dict) -> str:  # type: ignore[name-defined]
    """rule_decision의 phase를 by_phase 키 기준으로 추출 (best-effort)."""
    # virtual record의 phase는 summary_snapshot.by_rule.by_phase 키와 같음
    # — 이 함수는 그 매핑을 역산하기보다 by_phase 키를 순회해 block decision과 대응
    if d.block and by_phase:
        for ph in by_phase:
            return ph
    return ""


def _atomic_write_json(path: str, payload: dict) -> None:
    slug_dir = os.path.dirname(path)
    os.makedirs(slug_dir, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=slug_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _atomic_write_text(path: str, content: str) -> None:
    slug_dir = os.path.dirname(path)
    os.makedirs(slug_dir, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=slug_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
