"""
core/review_report.py
======================
통합 교차검증 보고서 생성 + 문서 교차검증 세션.

사용처:
  1. scripts/design_review_watcher.py — 설계/코드 리뷰 결과 저장
  2. core/project_pipeline.py — 런타임 문서 교차검증
  3. skills/evaluator/doc_qa/skill.py — 문서 QA 스킬
  4. .claude/agents/af-doc-qa.md — Claude Code 에이전트
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

from core.utils import now_iso


# ── 데이터 모델 ─────────────────────────────────────────────────────────────


@dataclass
class ReviewerResult:
    """개별 검증자의 리뷰 결과."""

    provider: str  # "claude" | "codex" | "gemini"
    role: str  # "critic" | "cross"
    raw_output: str  # LLM 원문 출력
    findings_count: int = 0
    verdict: str = ""  # "BLOCK"/"WARN"/"PASS" (critic) or "ACCEPT"/"REJECT"/"HOLD" (cross)
    elapsed_seconds: float = 0.0
    token_count: int = 0
    # Tier 2 Phase 2: vendor 다양성 라벨링.
    # - "multi": 외부 프로바이더(codex/gemini 등) 참여 → 진짜 cross-vendor 검증
    # - "single": cross-review SKIP 또는 same-vendor만 → single-vendor 모드
    # - "same-vendor": critic role 자체 (Anthropic 셀프 페르소나 비판)
    vendor_mode: str = "multi"


@dataclass
class JudgeResult:
    """판정자의 최종 판정 결과."""

    provider: str
    verdict: str  # "BLOCK" | "WARN" | "PASS"
    aggregated_output: str  # 통합 마크다운
    accept_count: int = 0
    reject_count: int = 0
    hold_count: int = 0
    elapsed_seconds: float = 0.0
    token_count: int = 0
    fix_instructions: dict[str, str] = field(default_factory=dict)


@dataclass
class ReviewReport:
    """교차검증 전체 보고서."""

    review_type: str  # "design" | "code" | "document"
    target: str  # 파일 경로 또는 work-item slug
    trigger: str  # "hook" | "pipeline" | "manual"
    round_num: int = 1
    max_rounds: int = 1
    critic: ReviewerResult | None = None
    cross: ReviewerResult | None = None
    judge: JudgeResult | None = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = now_iso()

    # ── 마크다운 보고서 ──────────────────────────────────────────────────

    def to_markdown(self) -> str:
        """§3.1 형식의 마크다운 보고서 생성."""
        lines: list[str] = []

        # 헤더
        type_label = {"design": "Design", "code": "Code", "document": "Document"}.get(
            self.review_type, self.review_type.title()
        )
        lines.append(f"# {type_label} Review: {os.path.basename(self.target)}")
        lines.append("")
        lines.append(f"> Source: {self.target}")
        lines.append(f"> Date: {self.timestamp}")
        lines.append(f"> Type: {self.review_type}")

        providers_parts = []
        if self.critic:
            providers_parts.append(f"critic={self.critic.provider}")
        if self.cross:
            providers_parts.append(f"cross={self.cross.provider}")
        if self.judge:
            providers_parts.append(f"judge={self.judge.provider}")
        lines.append(f"> Providers: {', '.join(providers_parts)}")

        mode = "cross-review" if self.cross else "single-provider"
        lines.append(f"> Mode: {mode}")
        lines.append(f"> Trigger: {self.trigger}")
        lines.append(f"> Round: {self.round_num}/{self.max_rounds}")
        lines.append("")
        lines.append("---")

        # Critic 섹션
        if self.critic:
            lines.append("")
            lines.append(f"## 검증자 A (Critic): {self.critic.provider}")
            lines.append("")
            lines.append(self.critic.raw_output.strip())
            lines.append("")
            lines.append(f"> Critic 소결: 발견 {self.critic.findings_count}개, 판정 {self.critic.verdict}")
            lines.append("")
            lines.append("---")

        # Cross 섹션
        if self.cross:
            lines.append("")
            lines.append(f"## 검증자 B (Cross): {self.cross.provider}")
            lines.append("")
            lines.append(self.cross.raw_output.strip())
            lines.append("")
            lines.append("---")

        # Judge 섹션
        if self.judge:
            lines.append("")
            lines.append(f"## 최종 판정 (Judge): {self.judge.provider}")
            lines.append("")
            lines.append(f"### 종합 판정: {self.judge.verdict}")
            lines.append("")
            lines.append(self.judge.aggregated_output.strip())
            lines.append("")
            lines.append("---")

        # 메타데이터
        total_tokens = sum(
            getattr(r, "token_count", 0)
            for r in [self.critic, self.cross, self.judge]
            if r
        )
        total_elapsed = sum(
            getattr(r, "elapsed_seconds", 0.0)
            for r in [self.critic, self.cross, self.judge]
            if r
        )
        lines.append("")
        lines.append("## 메타데이터")
        lines.append("")
        lines.append(f"- 총 토큰: {total_tokens}")
        lines.append(f"- 소요 시간: {total_elapsed:.1f}s")
        lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """JSON 직렬화용 딕셔너리."""
        return {
            "review_type": self.review_type,
            "target": self.target,
            "trigger": self.trigger,
            "round_num": self.round_num,
            "max_rounds": self.max_rounds,
            "timestamp": self.timestamp,
            "critic": {
                "provider": self.critic.provider,
                "verdict": self.critic.verdict,
                "findings_count": self.critic.findings_count,
            }
            if self.critic
            else None,
            "cross": {
                "provider": self.cross.provider,
                "verdict": self.cross.verdict,
                "findings_count": self.cross.findings_count,
            }
            if self.cross
            else None,
            "judge": {
                "provider": self.judge.provider,
                "verdict": self.judge.verdict,
                "accept_count": self.judge.accept_count,
                "reject_count": self.judge.reject_count,
                "hold_count": self.judge.hold_count,
            }
            if self.judge
            else None,
        }

    def save(self, workspace: str) -> str:
        """§3.2 규칙에 따라 파일 저장. 저장 경로 반환."""
        from core.file_io import write_text

        ts = time.strftime("%Y-%m-%d-%H%M%S")
        stem = os.path.basename(self.target).replace(".md", "").replace(".py", "")

        if self.review_type == "document":
            # work-item 디렉토리에 라운드별 누적 append
            report_dir = os.path.join(workspace, "docs", "work-items", self.target)
            os.makedirs(report_dir, exist_ok=True)
            report_path = os.path.join(report_dir, "verification-report.md")
            round_section = f"\n\n## Round {self.round_num}\n\n{self.to_markdown()}"
            if os.path.exists(report_path):
                with open(report_path, "a", encoding="utf-8") as f:
                    f.write(round_section)
            else:
                write_text(report_path, self.to_markdown())
        else:
            # design/code → docs/reviews/
            report_dir = os.path.join(workspace, "docs", "reviews")
            os.makedirs(report_dir, exist_ok=True)
            filename = f"{ts}-{stem}-{self.review_type}-review.md"
            report_path = os.path.join(report_dir, filename)
            write_text(report_path, self.to_markdown())

        return report_path


# ── DocumentReviewSession ────────────────────────────────────────────────────


class DocumentReviewSession:
    """
    런타임 문서 교차검증 세션.

    CrossVerificationLoop과 분리된 별도 클래스.
    CrossVerificationLoop은 런타임 코드 실행 검증 전용으로 유지.
    """

    def __init__(
        self,
        workspace: str,
        slug: str,
        level: str = "dynamic",
        max_rounds: int = 2,
    ) -> None:
        self.workspace = workspace
        self.slug = slug
        self.level = level
        self.max_rounds = max_rounds if level == "enterprise" else 1
        self.reports: list[ReviewReport] = []

    def run_review(
        self,
        documents: dict[str, str],
        round_num: int = 1,
        project_brief: dict | None = None,
    ) -> ReviewReport:
        """
        문서 세트에 대한 교차검증 1라운드 실행.

        Args:
            documents: {doc_type: content} — feature-plan, feature-spec 등
            round_num: 현재 라운드 번호
            project_brief: 원천 데이터 (정합성 검증용)

        Returns:
            ReviewReport with critic/cross/judge results
        """
        from core.review_runner import (
            detect_blocked_providers,
            detect_providers,
            run_aggregation,
            run_critic_review,
            run_cross_review,
            select_judge,
            select_review_pair,
        )

        # G5: AUTH_EXPIRED provider 있으면 즉시 BLOCK (부분 만료 포함)
        blocked = detect_blocked_providers()
        if blocked:
            return self._empty_report(
                round_num, "BLOCK",
                f"인증 만료 provider: {', '.join(blocked)} — `<cli> login` 후 재시도",
            )

        providers = detect_providers()
        if not providers:
            # G4: SKIP으로 분리 — 미검증이지만 메트릭은 PASS와 구분
            return self._empty_report(round_num, "SKIP", "사용 가능한 provider 없음 — T2/T3 검증 생략")

        # 문서 내용 합산
        doc_content = "\n\n---\n\n".join(
            f"## {dtype}\n\n{content}" for dtype, content in documents.items()
        )

        context = ""
        if project_brief:
            import json

            context = json.dumps(project_brief, ensure_ascii=False, indent=2)[:3000]

        # Critic 실행
        critic_provider = providers[0]
        critic_result = run_critic_review(
            provider=critic_provider,
            doc_content=doc_content,
            context=context,
            prompt_file="doc_critic",
        )

        # Cross 실행 (G2: enterprise 게이팅 제거 — provider 2개 이상이면 실행)
        cross_result = None
        if len(providers) >= 2:
            _, cross_provider = select_review_pair(providers)
            cross_result = run_cross_review(
                provider=cross_provider,
                doc_content=doc_content,
                context=context,
                prompt_file="doc_cross_review",
            )

        # Judge 실행 (cross가 있을 때만)
        judge_result = None
        if cross_result and critic_result:
            judge_provider = select_judge(providers)
            raw_agg = run_aggregation(
                judge_provider,
                critic_result.raw_output,
                cross_result.raw_output if cross_result else "",
                doc_content,
                self.workspace,
                prompt_name="doc_aggregation",
            )
            # str → JudgeResult 변환
            verdict_str = "BLOCK" if "BLOCK" in raw_agg.upper() else (
                "PASS" if "PASS" in raw_agg.upper() else "WARN"
            )
            judge_result = JudgeResult(
                provider=judge_provider,
                verdict=verdict_str,
                aggregated_output=raw_agg,
            )

        # provider 1개(critic만) — critic verdict를 그대로 사용
        if not judge_result and critic_result:
            judge_result = JudgeResult(
                provider=critic_provider,
                verdict=critic_result.verdict or "WARN",
                aggregated_output=critic_result.raw_output,
            )

        report = ReviewReport(
            review_type="document",
            target=self.slug,
            trigger="pipeline",
            round_num=round_num,
            max_rounds=self.max_rounds,
            critic=critic_result,
            cross=cross_result,
            judge=judge_result,
        )
        self.reports.append(report)
        # 저장은 호출자 책임 (이중 저장 방지)
        return report

    def _empty_report(self, round_num: int, verdict: str, reason: str) -> ReviewReport:
        """프로바이더 없을 때 빈 보고서 반환."""
        report = ReviewReport(
            review_type="document",
            target=self.slug,
            trigger="pipeline",
            round_num=round_num,
            max_rounds=self.max_rounds,
            judge=JudgeResult(
                provider="none",
                verdict=verdict,
                aggregated_output=reason,
            ),
        )
        self.reports.append(report)
        return report
