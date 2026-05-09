"""
core/approval_gate.py
=====================
work-item approval-gate.md를 프로그램적으로 관리.

승인 흐름:
  1. prepare() → generate_work_items() 로 approval-gate.md 초기화 (execution_open: false)
  2. 사용자가 문서 검토/편집
  3. approve() 호출 → 현재 문서 해시를 스냅샷에 저장 + execution_open: true
  4. execute() 호출 시 is_execution_open() + check_validity() 통과 필요
  5. 승인 후 문서 변경 감지 시 invalidate() → 재승인 필요
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any

from core.file_io import write_text
from core.utils import now_iso


def _emit_approval_event(event_type: str, gate: "ApprovalGate", run_id: str, approver: str = "") -> None:
    """RunEvent 방출 — run_id 없으면 no-op. fire-and-forget."""
    if not run_id:
        return
    try:
        from core.events.run_event import RunEvent, RunEventType, get_default_store
        et = RunEventType(event_type) if isinstance(event_type, str) else event_type
        payload: dict = {"slug": gate.slug, "gate_path": gate.gate_path}
        if approver:
            payload["approver"] = approver
        get_default_store().append(RunEvent(
            run_id=run_id,
            event_type=et,
            payload=payload,
        ))
    except Exception:
        pass

GATE_FILENAME = "approval-gate.md"

# 섹션 헤더 상수 — _render와 _parse가 동일 문자열을 참조해 포맷 드리프트 방지
_SEC_METADATA = "## Metadata"
_SEC_SNAPSHOT = "## Approved Snapshot"
_SEC_GATE_STATUS = "## Gate Status"
_SEC_REVIEW_NOTES = "## Review Notes"
_SEC_INVALIDATION = "## Invalidation Rules"

_DOC_FILES = {
    "feature_plan": "feature-plan.md",
    "feature_spec": "feature-spec.md",
    "bug_fix_spec": "bug-fix-spec.md",
    "implementation_design": "implementation-design.md",
    "implementation_tasks": "implementation-tasks.md",
}


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()[:16]  # 앞 16자리만 저장 (가독성)


def _clean(value: Any) -> str:
    return str(value or "").strip()


class ApprovalGate:
    """work-item 폴더의 approval-gate.md를 읽고 씁니다."""

    def __init__(
        self,
        workspace: str,
        slug: str,
        *,
        runtime_workspace: str | None = None,
    ):
        self.workspace = os.path.abspath(workspace)
        self.slug = slug
        self.runtime_workspace = (
            os.path.abspath(runtime_workspace) if runtime_workspace else self.workspace
        )
        self.work_item_dir = os.path.join(
            self.workspace, "docs", "work-items", slug
        )
        self.gate_path = os.path.join(self.work_item_dir, GATE_FILENAME)

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    def initialize(self, work_item_id: str = "", run_id: str = "") -> None:
        """approval-gate.md 최초 생성 (execution_open: false)."""
        os.makedirs(self.work_item_dir, exist_ok=True)
        content = self._render(
            work_item=work_item_id or self.slug,
            approver="",
            status="review_pending",
            snapshots={},
            gate_statuses={},
            execution_open=False,
            review_notes="",
        )
        write_text(self.gate_path, content)
        _emit_approval_event("approval_requested", self, run_id)

    def approve(self, approver: str = "user", run_id: str = "") -> bool:
        """
        현재 문서 해시를 스냅샷에 저장하고 execution_open을 true로 설정.
        gate_path가 없으면 False 반환.
        """
        if not os.path.exists(self.gate_path):
            return False
        current = self._parse()
        snapshots = self.compute_snapshots()
        gate_statuses = {key: "approved" for key in _DOC_FILES}
        content = self._render(
            work_item=_clean(current.get("work_item") or self.slug),
            approver=approver,
            status="approved",
            snapshots=snapshots,
            gate_statuses=gate_statuses,
            execution_open=True,
            review_notes=_clean(current.get("review_notes")),
        )
        write_text(self.gate_path, content)
        _emit_approval_event("approval_granted", self, run_id, approver=approver)
        return True

    def invalidate(self, reason: str = "") -> None:
        """문서 변경 감지 시 호출 — 승인을 무효화한다."""
        if not os.path.exists(self.gate_path):
            return
        current = self._parse()
        note = _clean(current.get("review_notes"))
        if reason:
            note = f"{note}\n[무효화] {now_iso()}: {reason}".strip()
        gate_statuses = {key: "review_pending" for key in _DOC_FILES}
        content = self._render(
            work_item=_clean(current.get("work_item") or self.slug),
            approver="",
            status="review_pending",
            snapshots={},
            gate_statuses=gate_statuses,
            execution_open=False,
            review_notes=note,
        )
        write_text(self.gate_path, content)

    def is_execution_open(self) -> bool:
        """execution_open == true 이고 승인 상태인지 확인.

        W3 fix: gate가 열려 있어도 check_validity()를 항상 실행한다.
        문서가 변경된 경우 자동으로 invalidate하고 False를 반환한다.
        """
        if not os.path.exists(self.gate_path):
            return False
        data = self._parse()
        if not (bool(data.get("execution_open")) and _clean(data.get("status")) == "approved"):
            return False
        valid, changed = self.check_validity()
        if not valid:
            self.invalidate(reason=f"문서 변경 감지 (자동): {', '.join(changed)}")
            return False
        return True

    def read_block_decision(self) -> tuple[bool, dict | None]:
        """escalation _decision.json을 읽어 (blocked, decision_dict) 반환 (fail-closed).

        - _summary.json 부재 → (False, None) — P1 호환 fail-open
        - _summary.json 존재 + escalation_phase 마커 없음 → (False, None) — P1 산출
        - escalation_phase 마커 있음 + _decision.json 누락/stale/parse_error → fail-closed
        - AF_SKIP_ESCALATION=1 → 즉시 (False, None) — rollback 긴급 우회
        """
        if os.environ.get("AF_SKIP_ESCALATION") == "1":
            return False, None

        warnings_dir = os.path.join(
            self.runtime_workspace, "runtime", "warnings", self.slug
        )
        summary_path = os.path.join(warnings_dir, "_summary.json")
        decision_path = os.path.join(warnings_dir, "_decision.json")

        if not os.path.isfile(summary_path):
            return False, None
        try:
            with open(summary_path, encoding="utf-8") as fh:
                summary = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return False, None

        expected_phase = summary.get("escalation_phase")
        summary_last = summary.get("last_updated", "")

        if not expected_phase:
            return False, None

        # 여기부터 P2+ 환경 — fail-closed 분기
        if not os.path.isfile(decision_path):
            return True, {
                "block": True,
                "reason": "decision_missing",
                "blocking_rules": [],
                "expected_phase": expected_phase,
            }
        try:
            with open(decision_path, encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return True, {
                "block": True,
                "reason": "decision_parse_error",
                "blocking_rules": [],
                "expected_phase": expected_phase,
            }

        # phase 검증 — 순방향 호환 (old decision은 새 phase에서도 유효)
        _PHASE_ORDER_EC = {"P1": 1, "P2": 2, "P3": 3, "P4": 4, "P5": 5, "P6": 6}
        decision_phase = d.get("escalation_phase", "")
        decision_phase_num = _PHASE_ORDER_EC.get(decision_phase, 0)
        expected_phase_num = _PHASE_ORDER_EC.get(expected_phase, 0)
        # decision이 expected_phase보다 미래 phase로 평가됨 → 이상 상태 → fail-closed
        if decision_phase_num > expected_phase_num:
            return True, {
                "block": True,
                "reason": "decision_phase_mismatch",
                "blocking_rules": [],
                "expected_phase": expected_phase,
                "actual_phase": decision_phase,
            }
        # decision_phase_num <= expected_phase_num → 순방향 호환

        # stale (decision이 더 오래된 summary 기준)
        decision_summary_ts = d.get("generated_from_summary_last_updated", "")
        if decision_summary_ts and summary_last and decision_summary_ts < summary_last:
            return True, {
                "block": True,
                "reason": "decision_stale",
                "blocking_rules": [],
                "summary_last": summary_last,
                "decision_summary_ts": decision_summary_ts,
            }

        return bool(d.get("block")), d

    def check_validity(self) -> tuple[bool, list[str]]:
        """
        승인 스냅샷과 현재 문서 해시를 비교.

        Returns:
            (유효 여부, 변경된 문서 목록)
        """
        if not os.path.exists(self.gate_path):
            return False, ["approval-gate.md not found"]
        data = self._parse()
        snapshots = dict(data.get("snapshots") or {})
        if not snapshots:
            return False, ["no snapshot recorded"]

        # 스냅샷 값이 모두 빈 문자열: 승인 시 문서가 없었던 경우
        if not any(snapshots.values()):
            # 승인 이후 추가된 파일을 변경으로 분류
            added = [
                fname
                for fname in _DOC_FILES.values()
                if os.path.exists(os.path.join(self.work_item_dir, fname))
            ]
            if not added:
                return True, []
            return False, added

        changed: list[str] = []
        current = self.compute_snapshots()
        for key, filename in _DOC_FILES.items():
            saved = _clean(snapshots.get(key))
            now_hash = _clean(current.get(key))
            if not saved:
                # 승인 당시 없었지만 지금 존재하면 변경으로 분류
                if now_hash:
                    changed.append(filename)
                continue
            if saved != now_hash:
                changed.append(filename)
        return len(changed) == 0, changed

    def compute_snapshots(self) -> dict[str, str]:
        """각 work-item 문서의 현재 해시를 계산."""
        result: dict[str, str] = {}
        for key, filename in _DOC_FILES.items():
            path = os.path.join(self.work_item_dir, filename)
            result[key] = _sha256_file(path) if os.path.exists(path) else ""
        return result

    def apply_verification_verdict(self, verdict: str) -> None:
        """verification-report.md verdict를 게이트에 반영한다.

        verdict == "BLOCK" → execution_open=false, status="verification_blocked".
        다른 verdict(PASS, WARN 등)는 무시한다.
        """
        if not os.path.exists(self.gate_path):
            return
        if (verdict or "").strip().upper() != "BLOCK":
            return
        current = self._parse()
        # 멱등성: 이미 BLOCK 상태이고 review_notes에 차단 마커가 있으면 no-op.
        # _sweep_verify_handoffs가 매 tick 호출되어 timestamp 라인이 무한 누적되는 회귀 차단.
        existing_notes = _clean(current.get("review_notes"))
        if (
            _clean(current.get("status")) == "verification_blocked"
            and "verification verdict=BLOCK" in existing_notes
        ):
            return
        note = f"{existing_notes}\n[자동 차단] {now_iso()}: verification verdict=BLOCK".strip()
        gate_statuses = {key: "review_pending" for key in _DOC_FILES}
        content = self._render(
            work_item=_clean(current.get("work_item") or self.slug),
            approver="",
            status="verification_blocked",
            snapshots={},
            gate_statuses=gate_statuses,
            execution_open=False,
            review_notes=note,
        )
        write_text(self.gate_path, content)

    def get_status(self) -> dict[str, Any]:
        """현재 gate 상태를 딕셔너리로 반환."""
        if not os.path.exists(self.gate_path):
            return {"exists": False}
        data = self._parse()
        return {
            "exists": True,
            "status": _clean(data.get("status")),
            "approver": _clean(data.get("approver")),
            "execution_open": bool(data.get("execution_open")),
            "work_item": _clean(data.get("work_item") or self.slug),
            "gate_path": self.gate_path,
            "work_item_dir": self.work_item_dir,
        }

    # ------------------------------------------------------------------
    # 내부: 파싱
    # ------------------------------------------------------------------

    def _parse(self) -> dict[str, Any]:
        """approval-gate.md를 파싱하여 딕셔너리로 반환."""
        try:
            with open(self.gate_path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            return {}

        result: dict[str, Any] = {}
        snapshots: dict[str, str] = {}
        gate_statuses: dict[str, str] = {}

        # Metadata 섹션 (work_item, approver, status, last_updated)
        # execution_open 은 Gate Status 섹션에서만 파싱한다
        _h_meta = re.escape(_SEC_METADATA)
        _h_snap = re.escape(_SEC_SNAPSHOT)
        _h_gate = re.escape(_SEC_GATE_STATUS)
        _h_notes = re.escape(_SEC_REVIEW_NOTES)

        meta_block = re.search(rf"{_h_meta}\n(.*?)(?=\n##|\Z)", text, re.S)
        if meta_block:
            for line in meta_block.group(1).splitlines():
                m = re.match(r"-\s+(\w+):\s*(.*)", line.strip())
                if m:
                    key, val = m.group(1).strip(), m.group(2).strip()
                    result[key] = val

        # Approved Snapshot 섹션
        snap_block = re.search(rf"{_h_snap}\n(.*?)(?=\n##|\Z)", text, re.S)
        if snap_block:
            for line in snap_block.group(1).splitlines():
                m = re.match(r"-\s+(\w+)_version:\s*(.*)", line.strip())
                if m:
                    snapshots[m.group(1).strip()] = m.group(2).strip()
        result["snapshots"] = snapshots

        # Gate Status 섹션
        gate_block = re.search(rf"{_h_gate}\n(.*?)(?=\n##|\Z)", text, re.S)
        if gate_block:
            for line in gate_block.group(1).splitlines():
                m = re.match(r"-\s+(\w+)_status:\s*(.*)", line.strip())
                if m:
                    gate_statuses[m.group(1).strip()] = m.group(2).strip()
                ex = re.match(r"-\s+execution_open:\s*(.*)", line.strip())
                if ex:
                    result["execution_open"] = ex.group(1).strip().lower() in ("true", "yes", "1")
        result["gate_statuses"] = gate_statuses

        # Review Notes 섹션
        notes_block = re.search(rf"{_h_notes}\n(.*?)(?=\n##|\Z)", text, re.S)
        if notes_block:
            result["review_notes"] = notes_block.group(1).strip()

        return result

    # ------------------------------------------------------------------
    # 내부: 렌더링
    # ------------------------------------------------------------------

    def _render(
        self,
        work_item: str,
        approver: str,
        status: str,
        snapshots: dict[str, str],
        gate_statuses: dict[str, str],
        execution_open: bool,
        review_notes: str,
    ) -> str:
        snap_lines = "\n".join(
            f"- {key}_version: {snapshots.get(key, '')}"
            for key in _DOC_FILES
        )
        gate_lines = "\n".join(
            f"- {key}_status: {gate_statuses.get(key, 'review_pending')}"
            for key in _DOC_FILES
        )
        decision_report_path = os.path.join(
            self.runtime_workspace, "runtime", "warnings", self.slug, "_decision.md"
        )
        decision_report_line = f"- gate_decision_report: {decision_report_path}"
        notes_body = (
            f"{review_notes}\n{decision_report_line}"
            if review_notes.strip()
            else decision_report_line
        )
        return (
            "# Approval Gate\n"
            "\n"
            f"{_SEC_METADATA}\n"
            "\n"
            f"- work_item: {work_item}\n"
            f"- approver: {approver}\n"
            f"- status: {status}\n"
            f"- last_updated: {now_iso()}\n"
            "\n"
            f"{_SEC_SNAPSHOT}\n"
            "\n"
            f"{snap_lines}\n"
            "\n"
            f"{_SEC_GATE_STATUS}\n"
            "\n"
            f"{gate_lines}\n"
            f"- execution_open: {'true' if execution_open else 'false'}\n"
            "\n"
            f"{_SEC_REVIEW_NOTES}\n"
            "\n"
            f"{notes_body}\n"
            "\n"
            f"{_SEC_INVALIDATION}\n"
            "\n"
            "- 승인 후 문서가 바뀌면 기존 승인은 무효다.\n"
            "- 최신 문서 상태와 승인 스냅샷이 다르면 구현할 수 없다.\n"
        )
