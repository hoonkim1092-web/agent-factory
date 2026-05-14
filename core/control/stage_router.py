"""StageRouter — Stage 0 오케스트레이터 (설계 §4.2, §5.2.1, §3.1).

QuestionRouter 결과를 artifact로 렌더링하고 ledger에 기록한다.
파일 쓰기는 atomic write 전용. LLM 호출 없음 (QuestionRouter에 위임).
"""
from __future__ import annotations

import datetime
import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from core.control.question_router import (
    QuestionBatchResult,
    QuestionResult,
    load_question_schema,
    parse_questions,
)
from core.control.run_ledger import RunLedger
from core.control.stage_artifacts import (
    AssumptionLedgerEntry,
    DomainReviewArtifact,
    PausedHitlArtifact,
    PausedHitlQuestion,
    ProjectGoalArtifact,
)
from core.control.verdicts import BlockCause, DomainVerdict, QuestionRoute

_SCHEMA_VERSION = 1
_QUESTIONS_DIR = Path(__file__).parent / "questions"
_ACTIVE_SETS = ("goal_clarification", "brainstorming")

_assumptions_lock = threading.Lock()


class StageRouter:
    """Stage 0 아티팩트 생성 오케스트레이터.

    단독 실행 흐름:
      new_project → GoalClarificationQR → BrainstormingQR → artifacts
      maintenance 계열 → LightContextScan → BrainstormingQR → artifacts
      empty/non-enum → Stage 0 skip (기존 Stage 1~3 실행)
    """

    def __init__(self, workspace: str, run_ledger: RunLedger):
        self._workspace = workspace
        self._run_ledger = run_ledger
        # 모든 active YAML을 한 번에 로드하고 cross-yaml id uniqueness 검증
        self._active_schemas, self._schema_hashes = self._load_active_question_sets()
        self._validate_cross_yaml_id_uniqueness(self._active_schemas)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        work_dir: str,
        work_kind: str,
        blast_radius: str,
        run_id: str = "",
        question_router: Any = None,
        doc_root: str = "",
        slug: str = "",
    ) -> dict[str, str]:
        """Stage 0 실행. 반환값: file-path map (generate_work_items 계약 유지).

        work_kind가 empty/non-enum이면 Stage 0 skip → 빈 dict 반환 → caller가 Stage 1~3 진행.
        paused_hitl이면 sentinel 포함 file-path map 반환 → Stage 1~3 skip.
        """
        from core.control.work_kind import ISSUE_KIND_MAP

        # empty/non-enum compatibility guard (설계 §3.2)
        if not work_kind or work_kind not in ISSUE_KIND_MAP:
            return {}

        if work_kind == "new_project":
            return self._run_new_project(work_dir, blast_radius, run_id, question_router, doc_root, slug)
        else:
            return self._run_maintenance(work_dir, work_kind, blast_radius, run_id, question_router, doc_root, slug)

    # ------------------------------------------------------------------
    # 분기별 실행
    # ------------------------------------------------------------------

    def _run_new_project(
        self,
        work_dir: str,
        blast_radius: str,
        run_id: str,
        question_router: Any,
        doc_root: str = "",
        slug: str = "",
    ) -> dict[str, str]:
        files: dict[str, str] = {}

        # GoalClarification QR
        gc_schema = self._active_schemas.get("goal_clarification")
        gc_hash = self._schema_hashes.get("goal_clarification", "")
        gc_result: QuestionBatchResult | None = None
        if gc_schema and question_router:
            questions = parse_questions(gc_schema)
            gc_result = question_router.route_batch(
                questions, gc_schema, gc_hash, blast_radius
            )

        # Brainstorming QR
        br_result = self._run_brainstorming(blast_radius, question_router)

        # paused_hitl 감지
        hitl_ids = []
        if gc_result:
            hitl_ids.extend(gc_result.paused_hitl_ids)
        if br_result:
            hitl_ids.extend(br_result.paused_hitl_ids)

        if hitl_ids:
            return self._emit_paused(
                work_dir, blast_radius, run_id, hitl_ids, gc_result, br_result, files,
                doc_root=doc_root, slug=slug,
            )

        # 아티팩트 렌더링
        if gc_result:
            goal_path = self._write_project_goal(work_dir, gc_result, blast_radius)
            files["project_goal"] = goal_path
            self._append_assumptions(work_dir, gc_result, "goal_clarification")

        if br_result:
            dr_path = self._write_domain_review(work_dir, br_result, blast_radius)
            files["domain_review"] = dr_path
            self._append_assumptions(work_dir, br_result, "brainstorming")

        assumptions_path = os.path.join(work_dir, "assumptions.md")
        if os.path.exists(assumptions_path):
            files["assumptions"] = assumptions_path

        return files

    def _run_maintenance(
        self,
        work_dir: str,
        work_kind: str,
        blast_radius: str,
        run_id: str,
        question_router: Any,
        doc_root: str = "",
        slug: str = "",
    ) -> dict[str, str]:
        files: dict[str, str] = {}

        # Light Context Scan (LLM 0회)
        from core.control.context_scanner import LightContextScanner
        scanner = LightContextScanner()
        scan_art = scanner.scan(work_dir, work_kind, blast_radius)
        scan_path = self._write_context_scan(work_dir, scan_art)
        files["context_scan"] = scan_path

        # Brainstorming QR
        br_result = self._run_brainstorming(blast_radius, question_router)

        hitl_ids = br_result.paused_hitl_ids if br_result else []
        if hitl_ids:
            return self._emit_paused(
                work_dir, blast_radius, run_id, hitl_ids, None, br_result, files,
                doc_root=doc_root, slug=slug,
            )

        if br_result:
            dr_path = self._write_domain_review(work_dir, br_result, blast_radius)
            files["domain_review"] = dr_path
            self._append_assumptions(work_dir, br_result, "brainstorming")

        assumptions_path = os.path.join(work_dir, "assumptions.md")
        if os.path.exists(assumptions_path):
            files["assumptions"] = assumptions_path

        return files

    def _run_brainstorming(
        self, blast_radius: str, question_router: Any
    ) -> QuestionBatchResult | None:
        br_schema = self._active_schemas.get("brainstorming")
        br_hash = self._schema_hashes.get("brainstorming", "")
        if br_schema and question_router:
            questions = parse_questions(br_schema)
            return question_router.route_batch(
                questions, br_schema, br_hash, blast_radius
            )
        return None

    # ------------------------------------------------------------------
    # paused_hitl 방출
    # ------------------------------------------------------------------

    def _emit_paused(
        self,
        work_dir: str,
        blast_radius: str,
        run_id: str,
        hitl_ids: list[str],
        gc_result: QuestionBatchResult | None,
        br_result: QuestionBatchResult | None,
        partial_files: dict[str, str],
        doc_root: str = "",
        slug: str = "",
    ) -> dict[str, str]:
        from core.approval_gate import ApprovalGate

        # sentinel 생성
        paused_questions = [
            PausedHitlQuestion(
                question_set_id=self._find_question_set(qid, gc_result, br_result),
                question_id=qid,
            )
            for qid in hitl_ids
        ]
        bundle_hash = self._bundle_hash()
        artifact = PausedHitlArtifact(
            artifact_type="paused_hitl",
            status="paused_hitl",
            terminal_success=False,
            report_required=True,
            questions=paused_questions,
            schema_version=_SCHEMA_VERSION,
            schema_hash=bundle_hash,
            resume_entrypoint="ProjectPipeline",
            reason=f"{len(hitl_ids)} question(s) require HITL: {hitl_ids}",
        )
        paused_path = os.path.join(work_dir, "paused-hitl.md")
        _atomic_write_text(paused_path, _render_paused_hitl(artifact))

        # approval-gate.md 생성 (§9.1 계약)
        if doc_root and slug:
            gate = ApprovalGate(doc_root, slug, runtime_workspace=self._workspace)
            gate.initialize(
                run_id=run_id,
                status="paused_hitl",
                execution_open=False,
            )
        gate_path = os.path.join(work_dir, "approval-gate.md")

        # domain-review placeholder
        dr_path = os.path.join(work_dir, "domain-review.md")
        if not os.path.exists(dr_path):
            _atomic_write_text(dr_path, "- verdict: PASS\n# pending — HITL required\n")

        files = dict(partial_files)
        files["approval_gate"] = gate_path
        files["domain_review"] = dr_path
        files["paused_hitl"] = paused_path

        if gc_result or br_result:
            assumptions_path = os.path.join(work_dir, "assumptions.md")
            if os.path.exists(assumptions_path):
                files["assumptions"] = assumptions_path

        return files

    # ------------------------------------------------------------------
    # artifact 렌더링
    # ------------------------------------------------------------------

    def _write_project_goal(
        self, work_dir: str, result: QuestionBatchResult, blast_radius: str
    ) -> str:
        values = {r.output_field: r.value for r in result.results if r.value is not None}
        artifact = ProjectGoalArtifact(
            artifact_type="project_goal",
            question_set_id=result.question_set_id,
            schema_version=result.schema_version,
            schema_hash=result.schema_hash,
            work_kind="new_project",
            goal_summary=str(values.get("goal_summary", "")),
            deployment_target=str(values.get("deployment_target", "")),
            success_criteria=_to_list(values.get("success_criteria")),
            out_of_scope=_to_list(values.get("out_of_scope")),
            assumptions_used=_to_list(values.get("assumptions_used")),
        )
        path = os.path.join(work_dir, "project-goal.md")
        _atomic_write_text(path, _render_project_goal(artifact))
        return path

    def _write_domain_review(
        self, work_dir: str, result: QuestionBatchResult, blast_radius: str
    ) -> str:
        values = {r.output_field: r.value for r in result.results if r.value is not None}

        # DomainVerdict 파싱 — LLM 응답에서 verdict 추출
        verdict_raw = str(values.get("domain_verdict", "pass")).lower()
        try:
            verdict = DomainVerdict(verdict_raw)
        except ValueError:
            verdict = DomainVerdict.PASS

        bc_raw = values.get("block_cause")
        block_cause: BlockCause | None = None
        if bc_raw:
            try:
                block_cause = BlockCause(str(bc_raw))
            except ValueError:
                block_cause = None

        artifact = DomainReviewArtifact(
            artifact_type="domain_review",
            question_set_id=result.question_set_id,
            schema_version=result.schema_version,
            schema_hash=result.schema_hash,
            domain_verdict=verdict,
            block_cause=block_cause,
            domain_concerns=_to_list(values.get("domain_concerns")),
            suggested_adrs=_to_list(values.get("suggested_adrs")),
            research_scope=_to_list(values.get("research_scope")),
            review_questions=[],
            paused_hitl_questions=[],
        )
        path = os.path.join(work_dir, "domain-review.md")
        _atomic_write_text(path, _render_domain_review(artifact))
        return path

    def _write_context_scan(self, work_dir: str, artifact: Any) -> str:
        path = os.path.join(work_dir, "context-scan.md")
        _atomic_write_text(path, _render_context_scan(artifact))
        return path

    def _append_assumptions(
        self, work_dir: str, result: QuestionBatchResult, question_set_id: str
    ) -> None:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        entries = []
        for r in result.results:
            if r.source in ("llm_delegate", "fallback") and r.value is not None:
                entry = AssumptionLedgerEntry(
                    artifact_type="assumption",
                    schema_version=result.schema_version,
                    schema_hash=result.schema_hash,
                    timestamp=now,
                    question_set_id=question_set_id,
                    question_id=r.question_id,
                    output_field=r.output_field,
                    value=r.value,
                    source=r.source,
                    rationale=r.warning or "",
                )
                entries.append(entry)

        if not entries:
            return

        path = os.path.join(work_dir, "assumptions.md")
        lines = [
            json.dumps(
                {
                    "artifact_type": e.artifact_type,
                    "timestamp": e.timestamp,
                    "question_set_id": e.question_set_id,
                    "question_id": e.question_id,
                    "output_field": e.output_field,
                    "value": e.value,
                    "source": e.source,
                    "rationale": e.rationale,
                },
                ensure_ascii=False,
            )
            for e in entries
        ]
        line_block = "\n".join(lines) + "\n"

        with _assumptions_lock:
            os.makedirs(work_dir, exist_ok=True)
            try:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(line_block)
                    f.flush()
                    os.fsync(f.fileno())
            except Exception as exc:
                raise RuntimeError(f"[StageRouter] assumptions append failed: {exc}") from exc

    # ------------------------------------------------------------------
    # YAML 로드 / 검증
    # ------------------------------------------------------------------

    def _load_active_question_sets(self) -> tuple[dict[str, dict], dict[str, str]]:
        schemas: dict[str, dict] = {}
        hashes: dict[str, str] = {}
        for name in _ACTIVE_SETS:
            yaml_path = _QUESTIONS_DIR / f"{name}.yaml"
            if yaml_path.exists():
                schema, sha = load_question_schema(str(yaml_path))
                schemas[name] = schema
                hashes[name] = sha
        return schemas, hashes

    def _validate_cross_yaml_id_uniqueness(self, schemas: dict[str, dict]) -> None:
        seen: dict[str, str] = {}  # question_id -> question_set_id
        for set_id, schema in schemas.items():
            for q in schema.get("questions", []):
                qid = q["id"]
                if qid in seen:
                    raise RuntimeError(
                        f"Cross-YAML question.id collision: '{qid}' "
                        f"in both '{seen[qid]}' and '{set_id}'. "
                        f"MVP requires global active id uniqueness."
                    )
                seen[qid] = set_id

    def _bundle_hash(self) -> str:
        import hashlib
        combined = "|".join(
            f"{k}:{v}" for k, v in sorted(self._schema_hashes.items())
        )
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def _find_question_set(
        self,
        question_id: str,
        gc_result: QuestionBatchResult | None,
        br_result: QuestionBatchResult | None,
    ) -> str:
        for result in (gc_result, br_result):
            if result and question_id in result.paused_hitl_ids:
                return result.question_set_id
        return "unknown"


# ------------------------------------------------------------------
# atomic write helper
# ------------------------------------------------------------------

def _atomic_write_text(path: str, content: str) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d or ".", suffix=".tmp")
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


# ------------------------------------------------------------------
# 렌더러
# ------------------------------------------------------------------

def _render_project_goal(a: ProjectGoalArtifact) -> str:
    lines = [
        "# project-goal.md",
        f"artifact_type: {a.artifact_type}",
        f"question_set_id: {a.question_set_id}",
        f"schema_version: {a.schema_version}",
        f"schema_hash: {a.schema_hash}",
        f"work_kind: {a.work_kind}",
        "",
        f"## Goal Summary\n{a.goal_summary}",
        f"## Deployment Target\n{a.deployment_target}",
        "## Success Criteria",
    ]
    for c in a.success_criteria:
        lines.append(f"- {c}")
    lines.append("## Out of Scope")
    for o in a.out_of_scope:
        lines.append(f"- {o}")
    return "\n".join(lines) + "\n"


def _render_domain_review(a: DomainReviewArtifact) -> str:
    lines = [
        "# domain-review.md",
        f"- verdict: {a.domain_verdict.value.upper()}",
    ]
    if a.block_cause:
        lines.append(f"- block_cause: {a.block_cause.value}")
    lines += [
        f"artifact_type: {a.artifact_type}",
        f"question_set_id: {a.question_set_id}",
        f"schema_version: {a.schema_version}",
        f"schema_hash: {a.schema_hash}",
        "## Domain Concerns",
    ]
    for c in a.domain_concerns:
        lines.append(f"- {c}")
    lines.append("## Research Scope")
    for s in a.research_scope:
        lines.append(f"- {s}")
    return "\n".join(lines) + "\n"


def _render_context_scan(a: Any) -> str:
    lines = [
        "# context-scan.md",
        f"artifact_type: {a.artifact_type}",
        f"work_kind: {a.work_kind}",
        f"blast_radius: {a.blast_radius}",
        f"schema_version: {a.schema_version}",
        f"schema_hash: {a.schema_hash}",
        "## Relevant Files",
    ]
    for f in a.relevant_files:
        lines.append(f"- {f}")
    lines.append("## Affected Modules")
    for m in a.affected_modules:
        lines.append(f"- {m}")
    lines.append("## Existing Tests")
    for t in a.existing_tests:
        lines.append(f"- {t}")
    lines.append("## Risk Signals")
    for r in a.risk_signals:
        lines.append(f"- {r}")
    return "\n".join(lines) + "\n"


def _render_paused_hitl(a: PausedHitlArtifact) -> str:
    lines = [
        "# paused-hitl.md",
        f"artifact_type: {a.artifact_type}",
        f"status: {a.status}",
        f"terminal_success: {str(a.terminal_success).lower()}",
        f"report_required: {str(a.report_required).lower()}",
        f"resume_entrypoint: {a.resume_entrypoint}",
        f"schema_version: {a.schema_version}",
        f"schema_hash: {a.schema_hash}",
        f"reason: {a.reason}",
        "## Paused Questions",
    ]
    for q in a.questions:
        lines.append(f"- set_id={q.question_set_id} question_id={q.question_id}")
    return "\n".join(lines) + "\n"


def _to_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [str(value)]
