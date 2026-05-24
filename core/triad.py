"""Triad orchestration: 正反合 plan review pipeline.

§17 Step 15 — Triad (Planner / Fact-Based Critic / Architect-Mediator).

  正 (Planner)   = deterministic initial plan (core/planner.py build_plan)
  反 (Critic)    = adversarial LLM agent; attacks the plan with concrete evidence
  合 (Architect) = LLM mediator; resolves findings into a final executable plan

Critic and Architect executors are injectable so callers can swap in real agents
or lightweight stubs.  Default executors are PASS stubs — real agent wiring goes
into agent_invoker or the dogfood orchestrator when agent infra is ready.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any, Callable, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_EVIDENCE_TYPES = frozenset(
    {"file_line", "test_gap", "git_diff", "adr", "blueprint", "packaging"}
)
VALID_SEVERITIES = frozenset({"Critical", "High", "Medium", "Low"})
VALID_VERDICTS = frozenset({"PASS", "WARN", "BLOCK"})
VALID_DECISIONS = frozenset({"ACCEPT", "REJECT", "HOLD"})


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class TriadCriticFinding:
    severity: str           # Critical | High | Medium | Low
    title: str
    evidence_type: str      # file_line | test_gap | git_diff | adr | blueprint | packaging
    evidence: str           # concrete evidence — empty = invalid finding
    affected_plan_step: str
    why_it_breaks: str
    required_fix: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "title": self.title,
            "evidence_type": self.evidence_type,
            "evidence": self.evidence,
            "affected_plan_step": self.affected_plan_step,
            "why_it_breaks": self.why_it_breaks,
            "required_fix": self.required_fix,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TriadCriticFinding":
        return cls(
            severity=str(data.get("severity", "Low")),
            title=str(data.get("title", "")),
            evidence_type=str(data.get("evidence_type", "")),
            evidence=str(data.get("evidence", "")),
            affected_plan_step=str(data.get("affected_plan_step", "")),
            why_it_breaks=str(data.get("why_it_breaks", "")),
            required_fix=str(data.get("required_fix", "")),
        )


@dataclass
class TriadCriticReport:
    verdict: str                              # PASS | WARN | BLOCK
    findings: list[TriadCriticFinding] = field(default_factory=list)

    def has_critical(self) -> bool:
        return any(f.severity == "Critical" for f in self.findings)

    def critical_findings(self) -> list[TriadCriticFinding]:
        return [f for f in self.findings if f.severity == "Critical"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "findings": [f.to_dict() for f in self.findings],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TriadCriticReport":
        findings = [
            TriadCriticFinding.from_dict(f)
            for f in (data.get("findings") or [])
        ]
        return cls(verdict=str(data.get("verdict", "PASS")), findings=findings)


@dataclass
class TriadDecision:
    finding_title: str
    verdict: str            # ACCEPT | REJECT | HOLD
    reason: str
    blueprint_section: str = ""
    adr_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_title": self.finding_title,
            "verdict": self.verdict,
            "reason": self.reason,
            "blueprint_section": self.blueprint_section,
            "adr_ref": self.adr_ref,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TriadDecision":
        return cls(
            finding_title=str(data.get("finding_title", "")),
            verdict=str(data.get("verdict", "HOLD")),
            reason=str(data.get("reason", "")),
            blueprint_section=str(data.get("blueprint_section", "")),
            adr_ref=str(data.get("adr_ref", "")),
        )


@dataclass
class TriadResult:
    initial_plan: dict[str, Any]
    critic_report: TriadCriticReport
    decisions: list[TriadDecision]
    final_plan: dict[str, Any]
    approved: bool
    block_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "initial_plan": self.initial_plan,
            "critic_report": self.critic_report.to_dict(),
            "decisions": [d.to_dict() for d in self.decisions],
            "final_plan": self.final_plan,
            "approved": self.approved,
            "block_reason": self.block_reason,
        }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_findings(findings: list[TriadCriticFinding]) -> list[TriadCriticFinding]:
    """Drop findings without valid evidence; warn for each dropped finding.

    Contract: evidence_type must be one of VALID_EVIDENCE_TYPES and evidence
    must be non-empty.  근거 없는 비판은 finding 무효.
    """
    valid: list[TriadCriticFinding] = []
    for f in findings:
        if f.evidence_type not in VALID_EVIDENCE_TYPES:
            warnings.warn(
                f"TriadCritic: finding '{f.title}' dropped — "
                f"invalid evidence_type '{f.evidence_type}'. "
                f"Must be one of {sorted(VALID_EVIDENCE_TYPES)}.",
                RuntimeWarning,
                stacklevel=3,
            )
            continue
        if not f.evidence.strip():
            warnings.warn(
                f"TriadCritic: finding '{f.title}' dropped — evidence is empty.",
                RuntimeWarning,
                stacklevel=3,
            )
            continue
        if f.severity not in VALID_SEVERITIES:
            warnings.warn(
                f"TriadCritic: finding '{f.title}' has unknown severity "
                f"'{f.severity}'; treating as Low.",
                RuntimeWarning,
                stacklevel=3,
            )
            f.severity = "Low"
        valid.append(f)
    return valid


def _coerce_verdict(report: TriadCriticReport) -> None:
    """Enforce verdict consistency: Critical findings → BLOCK."""
    if report.verdict not in VALID_VERDICTS:
        report.verdict = "WARN"
    if report.has_critical() and report.verdict != "BLOCK":
        report.verdict = "BLOCK"


# ---------------------------------------------------------------------------
# Default stubs (injectable replacements)
# ---------------------------------------------------------------------------

def _default_critic_fn(
    plan_dict: dict[str, Any], context: dict[str, Any]
) -> TriadCriticReport:
    """Stub: returns PASS with no findings.

    Replace via _critic_executor or pass _critic_fn to run_triad().
    """
    return TriadCriticReport(verdict="PASS", findings=[])


def _default_architect_fn(
    plan_dict: dict[str, Any],
    critic_report: TriadCriticReport,
    context: dict[str, Any],
) -> Tuple[dict[str, Any], list[TriadDecision]]:
    """Stub: accepts all findings, returns original plan.

    Replace via _architect_executor or pass _architect_fn to run_triad().
    When Critic has Critical findings the stub records them as HOLD so that
    approved=False propagates correctly.
    """
    decisions = [
        TriadDecision(
            finding_title=f.title,
            verdict="HOLD" if f.severity == "Critical" else "ACCEPT",
            reason="architect stub — real agent not yet wired",
        )
        for f in critic_report.findings
    ]
    return plan_dict, decisions


# Module-level injectable executors (monkeypatched in tests or real agent wiring).
_critic_executor: Callable[
    [dict[str, Any], dict[str, Any]], TriadCriticReport
] = _default_critic_fn

_architect_executor: Callable[
    [dict[str, Any], TriadCriticReport, dict[str, Any]],
    Tuple[dict[str, Any], list[TriadDecision]],
] = _default_architect_fn


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

class TriadBlockedError(RuntimeError):
    """Raised when Triad has unresolved Critical findings after Architect review."""


def run_triad(
    plan_dict: dict[str, Any],
    context: dict[str, Any],
    *,
    _critic_fn: Callable[
        [dict[str, Any], dict[str, Any]], TriadCriticReport
    ] | None = None,
    _architect_fn: Callable[
        [dict[str, Any], TriadCriticReport, dict[str, Any]],
        Tuple[dict[str, Any], list[TriadDecision]],
    ] | None = None,
) -> TriadResult:
    """Orchestrate 正反合 plan review.

    1. 反 (Critic): attack plan_dict → TriadCriticReport
    2. Validate findings (drop evidence-free findings)
    3. 合 (Architect): resolve findings → (final_plan, decisions)
    4. Determine approved: False when any Critical finding not REJECT-ed by Architect

    Raises TriadBlockedError when approved=False — caller should block_run().
    """
    critic_fn = _critic_fn or _critic_executor
    architect_fn = _architect_fn or _architect_executor

    # 反 — Critic attacks the plan
    raw_report = critic_fn(plan_dict, context)

    # Enforce evidence contract — drop findings without concrete evidence
    raw_report.findings = _validate_findings(raw_report.findings)
    _coerce_verdict(raw_report)

    # 合 — Architect resolves
    final_plan, decisions = architect_fn(plan_dict, raw_report, context)

    # Approved = no Critical finding left unresolved (not REJECT-ed by Architect)
    rejected_titles = {d.finding_title for d in decisions if d.verdict == "REJECT"}
    unresolved = [
        f for f in raw_report.critical_findings()
        if f.title not in rejected_titles
    ]
    approved = len(unresolved) == 0
    block_reason = ""
    if not approved:
        titles = "; ".join(f.title for f in unresolved)
        block_reason = f"Triad: {len(unresolved)} unresolved Critical finding(s): {titles}"

    result = TriadResult(
        initial_plan=plan_dict,
        critic_report=raw_report,
        decisions=decisions,
        final_plan=final_plan,
        approved=approved,
        block_reason=block_reason,
    )

    if not approved:
        raise TriadBlockedError(block_reason)

    return result
