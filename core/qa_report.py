"""QA 리포트 렌더러 — evidence_ledger → 자기완결 HTML 파일.

설계: docs/2026-06-18-user-perspective-qa-pipeline-design.md §9 (Q-S5)
"""
from __future__ import annotations

import html
import os
from typing import Any

_BADGE = {
    "user":     '<span class="badge badge-user">user</span>',
    "research": '<span class="badge badge-research">research</span>',
    "default":  '<span class="badge badge-default">default</span>',
}

_CSS = """
body { font-family: monospace; max-width: 900px; margin: 2em auto; color: #222; }
h1 { font-size: 1.3em; border-bottom: 2px solid #ccc; padding-bottom: .4em; }
h2 { font-size: 1.05em; margin-top: 2em; padding: .3em .6em; border-radius: 3px; }
h2.v { background: #e6f4ea; color: #1a6e30; }
h2.f { background: #fce8e6; color: #9c1900; }
h2.c { background: #f0f0f0; color: #555; }
h2.u { background: #fff3cd; color: #7a4f00; }
h2.q { background: #fffde7; color: #5c4400; }
.goal { border: 1px solid #ddd; margin: .8em 0; padding: .8em; border-radius: 4px; }
.gid { font-weight: bold; margin-bottom: .3em; }
.desc { margin-bottom: .4em; }
.field { margin: .2em 0; }
.label { color: #666; }
pre { background: #f5f5f5; padding: .4em .6em; overflow: auto; margin: .3em 0; white-space: pre-wrap; }
.badge { display: inline-block; padding: 1px 5px; border-radius: 3px; font-size: .82em; }
.badge-user { background: #c8f0c8; }
.badge-research { background: #fff3b0; }
.badge-default { background: #e8e8e8; }
.warn { color: #8a4f00; font-style: italic; }
"""


def render_html(evidence_ledger: dict[str, Any], run_dir: str) -> str:
    """evidence_ledger를 입력받아 run_dir/qa_report.html 생성 후 경로 반환.

    INV-Q2: provenance=research 골은 verdict 섹션 외에 [확인 요망]에도 동시 표기.

    # wiring: deferred — Q-S4/Q-S6 또는 project_pipeline.py에서 연결 예정
    """
    goals: list[dict[str, Any]] = evidence_ledger.get("goals", [])
    task_id = html.escape(str(evidence_ledger.get("task_id", "")))
    summary = html.escape(str(evidence_ledger.get("summary", "")))

    by_verdict: dict[str, list[dict[str, Any]]] = {
        "VERIFIED": [],
        "FAILED": [],
        "CANNOT_VERIFY": [],
        "UNVERIFIED": [],
    }
    confirm_required: list[dict[str, Any]] = []

    _KNOWN_VERDICTS = {"VERIFIED", "FAILED", "CANNOT_VERIFY", "UNVERIFIED"}
    for g in goals:
        verdict = g.get("verdict", "UNVERIFIED")
        bucket = verdict if verdict in _KNOWN_VERDICTS else "UNVERIFIED"
        by_verdict[bucket].append(g)
        if g.get("provenance") == "research":
            confirm_required.append(g)

    sections = []
    sections.append(_section_verified(by_verdict["VERIFIED"]))
    sections.append(_section_failed(by_verdict["FAILED"]))
    sections.append(_section_cannot_verify(by_verdict["CANNOT_VERIFY"]))
    sections.append(_section_unverified(by_verdict["UNVERIFIED"]))
    sections.append(_section_confirm(confirm_required))

    page = (
        "<!DOCTYPE html>\n"
        '<html lang="ko">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"<title>QA Report — {task_id}</title>\n"
        f"<style>{_CSS}</style>\n"
        "</head>\n"
        "<body>\n"
        f"<h1>QA Report — {task_id}</h1>\n"
        f"<p>{summary}</p>\n"
        + "\n".join(sections)
        + "\n</body>\n</html>\n"
    )

    out_path = os.path.join(run_dir, "qa_report.html")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(page)
    return out_path


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _goal_header(g: dict[str, Any]) -> str:
    gid = html.escape(g.get("goal_id", ""))
    desc = html.escape(g.get("description", ""))
    prov = g.get("provenance", "default")
    badge = _BADGE.get(prov, _BADGE["default"])
    return f'<div class="gid">{gid} {badge}</div><div class="desc">{desc}</div>'


def _field(label: str, value: str) -> str:
    return f'<div class="field"><span class="label">{html.escape(label)}:</span> {html.escape(value)}</div>'


def _pre(value: str) -> str:
    return f"<pre>{html.escape(value)}</pre>"


def _section_verified(goals: list[dict[str, Any]]) -> str:
    if not goals:
        return ""
    items = []
    for g in goals:
        parts = [_goal_header(g)]
        cmd = g.get("command_run", "")
        if cmd:
            parts.append(_field("command", cmd))
        ev_type = g.get("evidence_type", "")
        ev_val = g.get("evidence_value", "")
        if ev_type:
            parts.append(_field("evidence", ev_type))
        if ev_val:
            parts.append(_pre(ev_val))
        expected = g.get("expected_output", "")
        if expected:
            parts.append(_field("expected", expected))
        items.append('<div class="goal">' + "".join(parts) + "</div>")
    return '<h2 class="v">[VERIFIED]</h2>' + "".join(items)


def _section_failed(goals: list[dict[str, Any]]) -> str:
    if not goals:
        return ""
    items = []
    for g in goals:
        parts = [_goal_header(g)]
        cmd = g.get("command_run", "")
        if cmd:
            parts.append(_field("command", cmd))
        ev_val = g.get("evidence_value", "")
        if ev_val:
            parts.append('<div class="label">actual output:</div>')
            parts.append(_pre(ev_val))
        expected = g.get("expected_output", "")
        if expected:
            parts.append(_field("expected", expected))
        items.append('<div class="goal">' + "".join(parts) + "</div>")
    return '<h2 class="f">[FAILED]</h2>' + "".join(items)


def _section_cannot_verify(goals: list[dict[str, Any]]) -> str:
    if not goals:
        return ""
    items = []
    for g in goals:
        parts = [_goal_header(g)]
        reason = g.get("cannot_verify_reason", "")
        if reason:
            parts.append(_field("reason", reason))
        items.append('<div class="goal">' + "".join(parts) + "</div>")
    return '<h2 class="c">[CANNOT_VERIFY]</h2>' + "".join(items)


def _section_unverified(goals: list[dict[str, Any]]) -> str:
    if not goals:
        return ""
    items = []
    for g in goals:
        items.append('<div class="goal">' + _goal_header(g) + "</div>")
    return '<h2 class="u">[UNVERIFIED]</h2>' + "".join(items)


def _section_confirm(goals: list[dict[str, Any]]) -> str:
    if not goals:
        return ""
    items = []
    for g in goals:
        parts = [_goal_header(g)]
        expected = g.get("expected_output", "")
        msg = "리서치로 정답이라 가정함. 맞나요?"
        if expected:
            msg = f"리서치로 &ldquo;{html.escape(expected)}&rdquo;를 정답이라 가정함. 맞나요?"
        parts.append(f'<div class="warn">{msg}</div>')
        items.append('<div class="goal">' + "".join(parts) + "</div>")
    return '<h2 class="q">[확인 요망]</h2>' + "".join(items)
