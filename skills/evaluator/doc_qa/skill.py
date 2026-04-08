"""
skills/evaluator/doc_qa/skill.py
=================================
문서 품질 QA 스킬 — 프로젝트 파이프라인에서 자동 호출.

역할:
  1. work-item 문서 4개의 개별 품질 검증
  2. 문서 간 교차 일관성 검증 (9개 체크)
  3. 연구 증거와의 정합성 검증
  4. verification-report.md 생성

호출:
  - ProjectPipeline.prepare() → DocumentReviewSession (자동)
  - CLI: af eval doc-qa --workspace <path> --slug <work-item-slug>
"""
from __future__ import annotations

import os
from typing import Any

from core.skill_metadata import SkillCategory, SkillMetadata, SkillType, skill_metadata


@skill_metadata(SkillMetadata(
    skill_id="doc-qa",
    name="doc-qa",
    category=SkillCategory.EVAL,
    skill_type=SkillType.TOOL,
    description="Work-item 문서 세트의 품질 + 정합성 교차검증 QA",
    tags=["qa", "document", "cross-verification", "pipeline"],
))
class DocQASkill:
    """문서 교차검증 QA 스킬."""

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Work-item 문서 세트에 대한 교차검증 QA 실행.

        Args:
            context:
                workspace: str — 프로젝트 워크스페이스 경로
                slug: str — work-item slug
                level: "starter" | "dynamic" | "enterprise"
                documents: dict[str, str] — {doc_type: content} (선택)
                project_brief: dict — 원천 데이터 (선택)

        Returns:
            verdict: "PASS" | "WARN" | "BLOCK"
            report_path: str
            findings: list[dict]
            confidence: float
        """
        workspace = context.get("workspace", "")
        slug = context.get("slug", "")
        level = context.get("level", "dynamic")
        project_brief = context.get("project_brief")

        if not workspace or not slug:
            return {
                "verdict": "PASS",
                "report_path": "",
                "findings": [],
                "confidence": 0.0,
                "error": "workspace 또는 slug 미지정",
            }

        # 문서 내용 수집 (context에 없으면 파일에서 읽기)
        documents = context.get("documents")
        if not documents:
            documents = self._load_documents(workspace, slug)

        if not documents:
            return {
                "verdict": "PASS",
                "report_path": "",
                "findings": [],
                "confidence": 0.0,
                "error": "문서 없음",
            }

        # DocumentReviewSession으로 교차검증 실행
        from core.review_report import DocumentReviewSession

        session = DocumentReviewSession(
            workspace=workspace,
            slug=slug,
            level=level,
            max_rounds=2 if level == "enterprise" else 1,
        )

        final_report = None
        for round_num in range(1, session.max_rounds + 1):
            report = session.run_review(
                documents=documents,
                round_num=round_num,
                project_brief=project_brief,
            )
            final_report = report
            verdict = report.judge.verdict if report.judge else "PASS"

            if verdict == "PASS":
                break
            if verdict == "WARN" or round_num == session.max_rounds:
                break

            # BLOCK → 문서 수정 후 재시도
            if report.judge and report.judge.fix_instructions:
                from core.work_item_generator import _refine_document

                for dtype, instr in report.judge.fix_instructions.items():
                    if dtype in documents:
                        documents[dtype] = _refine_document(
                            original=documents[dtype],
                            feedback=instr,
                            project_brief=project_brief,
                        )

        if not final_report or not final_report.judge:
            return {
                "verdict": "PASS",
                "report_path": "",
                "findings": [],
                "confidence": 0.0,
            }

        # save는 호출자(여기)에서만 1회 실행 (run_review 내부에서는 저장 안 함)
        report_path = final_report.save(workspace)
        return {
            "verdict": final_report.judge.verdict,
            "report_path": report_path,
            "findings": [],  # 상세 findings는 보고서 파일에 기록
            "confidence": 1.0 if final_report.judge.verdict == "PASS" else 0.6,
        }

    def _load_documents(self, workspace: str, slug: str) -> dict[str, str]:
        """work-item 디렉토리에서 문서 파일들을 읽어온다."""
        work_dir = os.path.join(workspace, "docs", "work-items", slug)
        doc_files = [
            "feature-plan.md",
            "feature-spec.md",
            "implementation-design.md",
            "implementation-tasks.md",
        ]
        documents: dict[str, str] = {}
        for fname in doc_files:
            fpath = os.path.join(work_dir, fname)
            if os.path.exists(fpath):
                try:
                    with open(fpath, encoding="utf-8") as f:
                        documents[fname] = f.read()
                except Exception:
                    pass
        return documents
