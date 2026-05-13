"""
core/hooks/skill_self_evolution.py
===================================
스킬 자가 진화 훅.

동작:
  - post_execute() 에서 N회마다 전체 스킬 메타데이터 품질 자가 점검
  - 미비 스킬을 LLM으로 자동 보강 (bulk_enrich_all_skills)
  - on_skill_evolved() 에서 진화 이력을 로그 및 메모리에 기록
  - on_skill_quality_checked() 에서 품질 감사 결과 기록

PRIORITY = 80 (CheckpointHook=90, MemoryConsolidationHook=95 이전 실행)
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# trigger 문자열 whitelist (§6.3 / §7.2) — 모듈 상수로 정의해 클래스 내외부에서 동일 참조
_METADATA_TRIGGERS: frozenset[str] = frozenset({"metadata_enriched"})  # bus.py:138 일치
_CODE_EVOLUTION_TRIGGERS: frozenset[str] = frozenset({
    "fsa_failure",                      # fsa_loop.py:649
    "cross_verification",               # cross_verification.py:679
    "cross_verification_orchestrator",  # dynamic_orchestrator.py:613
})


class SkillSelfEvolutionHook:
    """
    스킬 자가 진화 훅.

    post_execute 마다 카운터를 증가시키고 check_interval 주기로
    전체 스킬 메타데이터 품질 감사를 비동기 실행합니다.
    """

    PRIORITY = 80

    def __init__(
        self,
        check_interval: int = 10,
        max_enrich_per_cycle: int = 5,
        quality_threshold: float = 0.5,
        coding_engine: Optional[str] = None,
        run_id: Optional[str] = None,   # Stage 1 추가 (F4) — 필수 권장, None 시 sentinel fallback
    ) -> None:
        self._check_interval = check_interval
        self._max_enrich = max_enrich_per_cycle
        self._quality_threshold = quality_threshold
        self._coding_engine = coding_engine
        self._run_id = run_id

        self._execution_count = 0
        self._audit_lock = threading.Lock()
        self._audit_in_progress = False

    def update_run_id(self, run_id: Optional[str]) -> None:
        """실행 중 run_id 갱신 — _audit_lock으로 보호하여 audit 스레드와 경합 방지."""
        with self._audit_lock:
            self._run_id = run_id

    # ------------------------------------------------------------------
    # Hook 인터페이스
    # ------------------------------------------------------------------

    def post_execute(self, agent_state: dict, result: dict) -> dict:
        """실행 완료 후 주기적 품질 감사 트리거."""
        # H4: _audit_lock으로 카운터 증가 + 조건 판별을 원자화 (parallel to_thread 환경 대응)
        # >= check_interval + reset 방식으로 스킵 없이 감사 발화 보장
        trigger_audit = False
        with self._audit_lock:
            self._execution_count += 1
            if self._execution_count >= self._check_interval:
                self._execution_count = 0
                trigger_audit = True

        if trigger_audit:
            self._trigger_audit_async()

        return result

    def on_skill_evolved(
        self,
        skill_id: str,
        old_version: str,
        new_version: str,
        trigger: str,
        decision: Optional[object] = None,  # EvolutionDecision — Optional import 순환 방지
    ) -> None:
        """스킬 진화 이벤트 수신 → trigger 종류별 분기 처리 + 메모리 기록 (§7.2)."""
        if trigger in _METADATA_TRIGGERS:
            logger.info("[SelfEvolution] 메타 보강: %s", skill_id)
        elif trigger in _CODE_EVOLUTION_TRIGGERS:
            logger.info(
                "[SelfEvolution] 코드 진화: %s (%s→%s)",
                skill_id, old_version or "?", new_version or "?",
            )
            self._notify_consolidation(skill_id)
        else:
            logger.warning(
                "[SelfEvolution] 알 수 없는 trigger: %s (skill=%s)", trigger, skill_id,
            )
        self._record_evolution_to_memory(skill_id, old_version, new_version, trigger, decision)

    def on_skill_quality_checked(self, skill_id: str, quality_report: dict) -> None:
        """품질 감사 결과 수신 → 로그."""
        score = quality_report.get("score", 0.0)
        enriched = quality_report.get("enriched", False)
        logger.debug(
            "[SelfEvolution] 품질 감사: %s score=%.2f enriched=%s",
            skill_id, score, enriched,
        )

    # ------------------------------------------------------------------
    # 내부 구현
    # ------------------------------------------------------------------

    def _trigger_audit_async(self) -> None:
        """품질 감사를 백그라운드 스레드에서 실행 (메인 파이프라인 차단 없음)."""
        with self._audit_lock:
            if self._audit_in_progress:
                logger.debug("[SelfEvolution] 감사 이미 실행 중, 스킵")
                return
            self._audit_in_progress = True

        thread = threading.Thread(
            target=self._run_quality_audit,
            name="SkillSelfEvolutionAudit",
            daemon=True,
        )
        thread.start()

    def _run_quality_audit(self) -> None:
        """
        전체 스킬 품질 감사 + 자동 보강.

        흐름:
          1. 전체 스킬 품질 점수 계산
          2. 미비 스킬 상위 N개 선정
          3. SkillMetaEnricher로 자동 보강
          4. 보강된 스킬을 SkillEvolutionBus로 캐시 무효화
        """
        try:
            from core.skill_enricher import bulk_enrich_all_skills
            from core.skill_evolution_bus import SkillEvolutionBus

            logger.info(
                "[SelfEvolution] 품질 감사 시작 (threshold=%.2f, max=%d)",
                self._quality_threshold, self._max_enrich,
            )

            enriched_ids = bulk_enrich_all_skills(
                coding_engine=self._coding_engine,
                max_skills=self._max_enrich,
                quality_threshold=self._quality_threshold,
            )

            if enriched_ids:
                evo_bus = SkillEvolutionBus.get_instance()
                evo_bus.on_bulk_enriched(enriched_ids)
                logger.info(
                    "[SelfEvolution] 자동 보강 완료: %d개 → %s",
                    len(enriched_ids), enriched_ids,
                )
            else:
                logger.debug("[SelfEvolution] 보강 대상 없음 (모든 스킬 품질 충분)")

        except Exception as e:
            logger.error("[SelfEvolution] 품질 감사 오류: %s", e)
        finally:
            with self._audit_lock:
                self._audit_in_progress = False

    def _notify_consolidation(self, skill_id: str) -> None:
        """코드 진화 후 memory_consolidation hook에 신호 전파."""
        try:
            from core.hooks.memory_consolidation import request_consolidation_hint
            request_consolidation_hint(skill_id)
        except Exception as e:
            logger.debug("[SelfEvolution] consolidation hint 전달 실패 (무시): %s", e)

    def _record_evolution_to_memory(
        self,
        skill_id: str,
        old_version: str,
        new_version: str,
        trigger: str,
        decision: Optional[object] = None,
    ) -> None:
        """진화 이벤트를 RunEventStore에 동기 기록.

        trigger 종류와 decision에 따라 RunEventType 4종 중 적절한 타입을 선택한다 (§6.3).
        """
        try:
            from core.events.run_event import RunEvent, RunEventType, get_default_store
            from core.evolution_types import EvolutionDecision

            # _audit_lock으로 스냅샷해 감사 스레드 실행 중 run_id 교체 경합 방지 (HIGH #3)
            with self._audit_lock:
                run_id = self._run_id or "_skill_evolution"

            if trigger in _METADATA_TRIGGERS:
                event_type = RunEventType.METADATA_ENRICHED
            elif decision == EvolutionDecision.PUBLISHED:
                event_type = RunEventType.EVOLUTION_PUBLISHED
            elif decision == EvolutionDecision.DEFERRED:
                # DEFERRED: 게이트 미신뢰 — payload.reason으로 ROLLED_BACK과 구분
                event_type = RunEventType.EVOLUTION_ROLLED_BACK
            elif decision in (EvolutionDecision.REJECTED, EvolutionDecision.ERROR):
                event_type = RunEventType.EVOLUTION_ROLLED_BACK
            elif decision is None and trigger in _CODE_EVOLUTION_TRIGGERS:
                event_type = RunEventType.EVOLUTION_REQUESTED
            else:
                event_type = RunEventType.EVOLUTION_REQUESTED

            payload: dict = {
                "skill_id": skill_id,
                "old_version": old_version,
                "new_version": new_version,
                "trigger": trigger,
            }
            if decision is not None:
                decision_val = decision.value if hasattr(decision, "value") else str(decision)
                payload["decision"] = decision_val
                if decision == EvolutionDecision.DEFERRED:
                    payload["reason"] = "deferred"

            store = get_default_store()
            store.append(RunEvent(
                run_id=run_id,
                event_type=event_type,
                payload=payload,
            ))
        except Exception as e:
            logger.debug("[SelfEvolution] 이벤트 기록 실패 (무시): %s", e)

    # ------------------------------------------------------------------
    # 상태 조회
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        with self._audit_lock:
            count = self._execution_count
            in_progress = self._audit_in_progress
        return {
            "execution_count": count,
            "check_interval": self._check_interval,
            "audit_in_progress": in_progress,
            "next_audit_in": self._check_interval - count,
        }
