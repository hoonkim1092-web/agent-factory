"""Completion contract: goal-reached verification via an evidence ledger.

이 모듈은 "생성 = 완료" 패턴 A를 차단하기 위한 *데이터 기반*이다.
파이프라인의 acceptance criteria를 검증 가능한 골(GoalEntry)로 모델링하고,
각 골을 실행 증거(GoalEvidence)로 판정(GoalVerdict)한다.

설계: docs/2026-06-17-af-completion-contract-goal-verification-design.md §4·§5·§6·§8
"""
from __future__ import annotations

import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Literal

# VERIFIED      — 실행 증거로 골 충족 확인
# FAILED        — 실행했으나 골 미충족 (BLOCKED(goal_failed) terminal 유발)
# CANNOT_VERIFY — 환경 한계로 검증 불가 (실패 아님, is_done() done 허용)
# UNVERIFIED    — 아직 검증 안 됨 / harness_type 미해결 (file-exists 자동통과 금지)
GoalVerdict = Literal["VERIFIED", "FAILED", "CANNOT_VERIFY", "UNVERIFIED"]


@dataclass
class GoalEvidence:
    evidence_type: str          # "exit_code" | "stdout_contains" | "file_exists" | "manual" | "cannot_verify" | "unverified"
    evidence_value: str         # 실제 캡처된 값 또는 설명
    command_run: str = ""       # 실행한 명령 (있을 경우)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_type": self.evidence_type,
            "evidence_value": self.evidence_value,
            "command_run": self.command_run,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoalEvidence":
        return cls(
            evidence_type=data.get("evidence_type", ""),
            evidence_value=data.get("evidence_value", ""),
            command_run=data.get("command_run", ""),
        )


@dataclass
class GoalEntry:
    goal_id: str                # 예: "G-1"
    description: str            # 사람이 읽는 골 설명
    harness_type: str           # "cli" | "server" | "gui" | "library" | "none"
    evidence: GoalEvidence | None = None
    verdict: GoalVerdict = "UNVERIFIED"
    cannot_verify_reason: str = ""   # CANNOT_VERIFY일 때 이유
    command: str = ""           # 하니스 실행 명령 (cli: 셸 명령, library: python -c 코드, server: 기동 명령)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "description": self.description,
            "harness_type": self.harness_type,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "verdict": self.verdict,
            "cannot_verify_reason": self.cannot_verify_reason,
            "command": self.command,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoalEntry":
        ev = data.get("evidence")
        return cls(
            goal_id=data.get("goal_id", ""),
            description=data.get("description", ""),
            harness_type=data.get("harness_type", "none"),
            evidence=GoalEvidence.from_dict(ev) if ev else None,
            verdict=data.get("verdict", "UNVERIFIED"),
            cannot_verify_reason=data.get("cannot_verify_reason", ""),
            command=data.get("command", ""),
        )


@dataclass
class GoalContract:
    task_id: str
    goals: list[GoalEntry] = field(default_factory=list)

    def is_done(self) -> bool:
        """INV-A: 모든 골이 VERIFIED 또는 CANNOT_VERIFY여야 done.

        골이 하나도 없으면 done이 아니다(빈 계약으로 통과 금지).
        """
        for g in self.goals:
            if g.verdict in ("UNVERIFIED", "FAILED"):
                return False
        return bool(self.goals)

    def has_failures(self) -> bool:
        return any(g.verdict == "FAILED" for g in self.goals)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goals": [g.to_dict() for g in self.goals],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoalContract":
        return cls(
            task_id=data.get("task_id", ""),
            goals=[GoalEntry.from_dict(g) for g in (data.get("goals") or [])],
        )


_SERVER_STARTUP_WAIT_SEC = 2  # 서버 기동 확인 대기 시간 (§5.1 server harness)


@dataclass
class HarnessResult:
    ok: bool
    evidence_type: str
    evidence_value: str
    command_run: str


class ExecutionHarness:
    """산출물 유형별 실행 하니스. §5.1/§5.2 설계."""

    def run(
        self,
        goal: "GoalEntry",
        workspace: str,
        timeout: int = 30,
    ) -> HarnessResult:
        if goal.harness_type == "cli":
            return self._run_cli(goal, workspace, timeout)
        if goal.harness_type == "server":
            return self._run_server(goal, workspace, timeout)
        if goal.harness_type == "gui":
            # AcceptanceGate가 먼저 처리하지만, 직접 호출 경로를 위한 방어
            return HarnessResult(
                ok=False,
                evidence_type="cannot_verify",
                evidence_value="GUI harness requires display — mark CANNOT_VERIFY",
                command_run="",
            )
        if goal.harness_type == "library":
            return self._run_library(goal, workspace, timeout)
        # "none" or unknown — 자동 통과(file-exists) 금지(§5.1 정정)
        return HarnessResult(
            ok=False,
            evidence_type="unverified",
            evidence_value="harness_type unresolved — cannot auto-verify",
            command_run="",
        )

    def _run_cli(self, goal: "GoalEntry", workspace: str, timeout: int) -> HarnessResult:
        if not goal.command:
            return HarnessResult(
                ok=False,
                evidence_type="unverified",
                evidence_value="cli command not specified",
                command_run="",
            )
        try:
            cmd_parts = shlex.split(goal.command, posix=(sys.platform != "win32"))
        except ValueError as exc:
            return HarnessResult(
                ok=False,
                evidence_type="unverified",  # 실행 안 됨 — FAILED 아님, harness 설정 오류
                evidence_value=f"command parse error: {exc}",
                command_run=goal.command,
            )
        try:
            proc = subprocess.run(
                cmd_parts,
                cwd=workspace,
                timeout=timeout,
                capture_output=True,
                text=True,
                errors="replace",
            )
            return HarnessResult(
                ok=proc.returncode == 0,
                evidence_type="exit_code",
                evidence_value=str(proc.returncode),
                command_run=goal.command,
            )
        except subprocess.TimeoutExpired:
            return HarnessResult(
                ok=False,
                evidence_type="exit_code",
                evidence_value="timeout",
                command_run=goal.command,
            )
        except FileNotFoundError:
            return HarnessResult(
                ok=False,
                evidence_type="exit_code",
                evidence_value="command not found",
                command_run=goal.command,
            )
        except Exception as exc:
            return HarnessResult(
                ok=False,
                evidence_type="exit_code",
                evidence_value=f"error: {exc}",
                command_run=goal.command,
            )

    def _run_server(self, goal: "GoalEntry", workspace: str, timeout: int) -> HarnessResult:
        """서버 기동 후 _SERVER_STARTUP_WAIT_SEC 대기 — 프로세스 생존 체크. §5.1.

        S2 단순화: 프로세스 생존 여부만 확인(ok=True). HTTP probe(requests.get)는 S3에서 추가.
        """
        if not goal.command:
            return HarnessResult(
                ok=False,
                evidence_type="unverified",
                evidence_value="server command not specified",
                command_run="",
            )
        try:
            cmd_parts = shlex.split(goal.command, posix=(sys.platform != "win32"))
        except ValueError as exc:
            return HarnessResult(
                ok=False,
                evidence_type="unverified",  # 실행 안 됨 — FAILED 아님, harness 설정 오류
                evidence_value=f"command parse error: {exc}",
                command_run=goal.command,
            )
        proc = None
        try:
            proc = subprocess.Popen(
                cmd_parts,
                cwd=workspace,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(_SERVER_STARTUP_WAIT_SEC)
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                return HarnessResult(
                    ok=True,
                    evidence_type="exit_code",
                    evidence_value="process_alive",
                    command_run=goal.command,
                )
            return HarnessResult(
                ok=False,
                evidence_type="exit_code",
                evidence_value=str(proc.returncode),
                command_run=goal.command,
            )
        except FileNotFoundError:
            return HarnessResult(
                ok=False,
                evidence_type="exit_code",
                evidence_value="command not found",
                command_run=goal.command,
            )
        except Exception as exc:
            if proc is not None and proc.poll() is None:
                proc.kill()
            return HarnessResult(
                ok=False,
                evidence_type="exit_code",
                evidence_value=f"error: {exc}",
                command_run=goal.command,
            )

    def _run_library(self, goal: "GoalEntry", workspace: str, timeout: int) -> HarnessResult:
        """python -c "<code>" 로 임포트·어서션 검증. §5.1.

        한계: PyInstaller frozen 빌드에서 sys.executable이 Python 인터프리터를
        가리키지 않으면 실패한다. frozen 환경에서는 harness_type="library" 미사용 권장.
        """
        if not goal.command:
            return HarnessResult(
                ok=False,
                evidence_type="unverified",
                evidence_value="library command not specified",
                command_run="",
            )
        cmd = [sys.executable, "-c", goal.command]
        try:
            proc = subprocess.run(
                cmd,
                cwd=workspace,
                timeout=timeout,
                capture_output=True,
                text=True,
                errors="replace",
            )
            return HarnessResult(
                ok=proc.returncode == 0,
                evidence_type="exit_code",
                evidence_value=str(proc.returncode),
                command_run=goal.command,
            )
        except subprocess.TimeoutExpired:
            return HarnessResult(
                ok=False,
                evidence_type="exit_code",
                evidence_value="timeout",
                command_run=goal.command,
            )
        except Exception as exc:
            return HarnessResult(
                ok=False,
                evidence_type="exit_code",
                evidence_value=f"error: {exc}",
                command_run=goal.command,
            )


# ---------------------------------------------------------------------------
# S3 helpers: parser + evidence ledger
# ---------------------------------------------------------------------------

def _infer_harness_type(text: str) -> str:
    """키워드 기반 harness_type 추론 — §4.2 파서 폴백."""
    t = text.lower()
    # GUI 우선 체크 (가장 구체적)
    if any(k in t for k in ("gui", "화면", "window", "창", "display", " ui ", "tkinter", "qt")):
        return "gui"
    # server 체크
    if any(k in t for k in ("server", "서버", " http ", "api ", " port", "포트", "flask", "fastapi", "django")):
        return "server"
    # library 체크
    if any(k in t for k in ("import ", "library", "라이브러리", "python -c", "import\t")):
        return "library"
    # cli 체크
    if any(k in t for k in ("cli", "명령줄", "명령어", "exit code", "exit_code", "bash ", " sh ", "실행 시", "실행하면")):
        return "cli"
    return "none"


def _extract_command(text: str) -> str:
    """텍스트에서 실행 명령 추출 — 백틱 인용 또는 python/pytest 패턴."""
    # 백틱 인용 우선
    m = re.search(r"`([^`]+)`", text)
    if m:
        return m.group(1).strip()
    # python script.py 패턴
    m = re.search(r"(python\s+\S+\.py(?:\s+\S+)*)", text)
    if m:
        return m.group(1).strip()
    # pytest 패턴
    m = re.search(r"(pytest\s+\S+)", text)
    if m:
        return m.group(1).strip()
    # curl 패턴
    m = re.search(r"(curl\s+\S+)", text)
    if m:
        return m.group(1).strip()
    return ""


def parse_acceptance_criteria(criteria: list[str], task_id: str) -> "GoalContract":
    """acceptance_criteria 문자열 목록 → GoalContract (§8 S3 파서).

    각 항목에서 harness_type 추론 + 명령 추출. 추론 불가 → harness_type="none" → UNVERIFIED.
    """
    goals = []
    for i, criterion in enumerate(criteria):
        stripped = criterion.strip()
        if not stripped:
            continue
        goals.append(GoalEntry(
            goal_id=f"G-{i + 1}",
            description=stripped,
            harness_type=_infer_harness_type(stripped),
            command=_extract_command(stripped),
        ))
    return GoalContract(task_id=task_id, goals=goals)


def build_evidence_ledger(contract: "GoalContract") -> dict[str, Any]:
    """GoalContract → evidence_ledger dict (§7 포맷)."""
    goal_entries = []
    cannot_verify: list[str] = []
    unverified: list[str] = []
    for g in contract.goals:
        entry: dict[str, Any] = {
            "goal_id": g.goal_id,
            "description": g.description,
            "verdict": g.verdict,
        }
        if g.evidence:
            entry["evidence_type"] = g.evidence.evidence_type
            entry["evidence_value"] = g.evidence.evidence_value
            if g.evidence.command_run:
                entry["command_run"] = g.evidence.command_run
        if g.cannot_verify_reason:
            entry["cannot_verify_reason"] = g.cannot_verify_reason
        goal_entries.append(entry)
        if g.verdict == "CANNOT_VERIFY":
            cannot_verify.append(g.goal_id)
        elif g.verdict == "UNVERIFIED":
            unverified.append(g.goal_id)

    verified = sum(1 for g in contract.goals if g.verdict == "VERIFIED")
    failed = sum(1 for g in contract.goals if g.verdict == "FAILED")
    total = len(contract.goals)
    summary = (
        f"{total} goals: {verified} VERIFIED, {failed} FAILED, "
        f"{len(cannot_verify)} CANNOT_VERIFY, {len(unverified)} UNVERIFIED"
    )
    return {
        "task_id": contract.task_id,
        "summary": summary,
        "goals": goal_entries,
        "unverified": unverified,
        "cannot_verify": cannot_verify,
    }


# wiring: deferred — S3에서 dogfood.py / project_pipeline.py 연결 예정
class AcceptanceGate:
    """GoalContract 각 GoalEntry에 하니스를 실행해 verdict를 채운다. §6.2."""

    def run(self, contract: "GoalContract", workspace: str) -> "GoalContract":
        """idempotent: 이미 VERIFIED/FAILED/CANNOT_VERIFY인 골은 재실행 skip."""
        harness = ExecutionHarness()
        for goal in contract.goals:
            if goal.verdict in ("VERIFIED", "FAILED", "CANNOT_VERIFY"):
                continue

            if goal.harness_type == "gui":
                goal.verdict = "CANNOT_VERIFY"
                if not goal.cannot_verify_reason:
                    goal.cannot_verify_reason = "display required"
                continue

            result = harness.run(goal, workspace)

            if result.ok:
                goal.evidence = GoalEvidence(
                    evidence_type=result.evidence_type,
                    evidence_value=result.evidence_value,
                    command_run=result.command_run,
                )
                goal.verdict = "VERIFIED"
            elif result.evidence_type == "unverified":
                # harness_type 미해결 — 실행 안 함(UNVERIFIED), 실패(FAILED) 아님 §5.2
                goal.verdict = "UNVERIFIED"
                goal.evidence = GoalEvidence(
                    evidence_type="unverified",
                    evidence_value=result.evidence_value,
                    command_run="",
                )
            else:
                goal.verdict = "FAILED"
                goal.evidence = GoalEvidence(
                    evidence_type=result.evidence_type,
                    evidence_value=result.evidence_value,
                    command_run=result.command_run,
                )

        return contract
