"""Stage 0 아티팩트 dataclass 정의 (설계 §7)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.control.verdicts import BlockCause, DomainVerdict


@dataclass
class ContextScanArtifact:
    artifact_type: str
    schema_version: int
    schema_hash: str
    work_dir: str
    work_kind: str
    blast_radius: str
    relevant_files: list[str] = field(default_factory=list)
    affected_modules: list[str] = field(default_factory=list)
    existing_tests: list[str] = field(default_factory=list)
    risk_signals: list[str] = field(default_factory=list)


@dataclass
class ProjectGoalArtifact:
    artifact_type: str
    question_set_id: str
    schema_version: int
    schema_hash: str
    work_kind: str
    goal_summary: str
    deployment_target: str
    success_criteria: list[str] = field(default_factory=list)
    out_of_scope: list[str] = field(default_factory=list)
    assumptions_used: list[str] = field(default_factory=list)
    # Q-S3 additive: QA 명료화 필드 (INV-Q7)
    observable_goal: str = ""
    golden_example: str = ""
    test_seam: str = ""
    manual_only: str = ""
    qa_provenance: dict[str, str] = field(default_factory=dict)  # output_field → provenance


@dataclass
class PausedHitlQuestion:
    question_set_id: str
    question_id: str


@dataclass
class DomainReviewArtifact:
    artifact_type: str
    question_set_id: str
    schema_version: int
    schema_hash: str
    domain_verdict: DomainVerdict
    block_cause: BlockCause | None
    domain_concerns: list[str] = field(default_factory=list)
    suggested_adrs: list[str] = field(default_factory=list)
    research_scope: list[str] = field(default_factory=list)
    review_questions: list[dict] = field(default_factory=list)
    paused_hitl_questions: list[PausedHitlQuestion] = field(default_factory=list)


@dataclass
class AssumptionLedgerEntry:
    artifact_type: str
    schema_version: int
    schema_hash: str
    timestamp: str
    question_set_id: str
    question_id: str
    output_field: str
    value: Any
    source: str  # llm_delegate | fallback | hitl
    rationale: str = ""


@dataclass
class PausedHitlArtifact:
    artifact_type: str
    status: str  # paused_hitl
    terminal_success: bool  # false
    report_required: bool  # true
    questions: list[PausedHitlQuestion]
    schema_version: int
    schema_hash: str
    resume_entrypoint: str
    reason: str
