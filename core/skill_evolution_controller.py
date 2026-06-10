"""
core/skill_evolution_controller.py
====================================
Stage 1 스킬 진화 단일 진입점.

호출자는 trigger + feedback을 제공한다. Controller는 candidate dir 생성,
LLM 진화, sandbox 검증, quality gate, publish 또는 폐기까지 한 번에 처리하고
EvolutionResult를 반환한다.

Sprint 3 구현 범위:
- _create_candidate: 절대경로 (config_paths.CANDIDATES_DIR 기준)
- knowledge skill 지원: skill.py 없어도 SKILL.md 있으면 sandbox 검증 스킵
- 호출 사이트 교체: fsa_loop / cross_verification / dynamic_orchestrator → submit()
"""
from __future__ import annotations

import logging
import os
import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from core.config_paths import CANDIDATES_DIR
from core.evolution_types import EvolutionDecision, EvolutionResult

if TYPE_CHECKING:
    from core.evolution_ledger import EvolutionLedger
    from core.run_budget import RunBudget

logger = logging.getLogger(__name__)

# LLM 진화 1회 평균 예상 비용 (§9.2 step 2, 보수적으로 설정)
_ESTIMATED_EVOLUTION_COST = 2000


class SelfEvolutionController:
    """
    스킬 진화 단일 진입점.

    호출자는 trigger와 feedback을 제공한다. Controller는 candidate dir 생성,
    LLM 진화, sandbox 검증, quality gate, publish 또는 폐기까지 처리한다.

    Bus 시그니처: skill_evolution_bus.py:72의 on_skill_evolved는 skill_dir=""
    default를 보유한다. Stage 1은 Optional 유지 + Controller가 명시 전달.
    """

    def __init__(
        self,
        ledger: Optional["EvolutionLedger"] = None,
        run_id: Optional[str] = None,
        budget: Optional["RunBudget"] = None,
    ) -> None:
        self._ledger = ledger
        self._run_id = run_id or ""
        self._budget = budget

    # ── 공개 API ──────────────────────────────────────────────────────────

    def submit(
        self,
        *,
        skill_dir: str,
        skill_id: str,
        trigger: str,
        feedback: str = "",
        error_log: str = "",
    ) -> EvolutionResult:
        """
        진화 파이프라인 단일 진입점.

        skill_id는 호출자 책임 — _detect_failed_skill_dir 오탐 위험은 §11 참조.

        Returns:
            EvolutionResult — decision은 항상 4종 중 하나.
        """
        # 1. 예산 소진 시 즉시 REJECTED (§9.2 step 1)
        if self._budget and self._budget.is_exhausted():
            return self._make_result(
                skill_id=skill_id,
                decision=EvolutionDecision.REJECTED,
                candidate_dir=None,
                new_version=None,
                rejection_reason="budget_exhausted_pre_call",
                cost_tokens=0,
                trigger=trigger,
            )

        # 2. 잔여 예산 사전 점검 (§9.2 step 2)
        if self._budget and self._budget.remaining() < _ESTIMATED_EVOLUTION_COST:
            return self._make_result(
                skill_id=skill_id,
                decision=EvolutionDecision.REJECTED,
                candidate_dir=None,
                new_version=None,
                rejection_reason="budget_insufficient_remaining",
                cost_tokens=0,
                trigger=trigger,
            )

        candidate_dir: Optional[str] = None
        old_version: str = ""  # try 전 초기화 — ERROR 경로 Ledger 기록용
        cost_tokens: int = 0   # try 전 초기화 — _record_budget 이후 예외 시에만 실제 소비 반영; 그 이전 예외 시 0
        pre_consumed: int = 0  # try 전 초기화 — try 안 L4에서 실제 캡처, 이 값은 budget=None 분기용
        try:
            old_version = self._read_live_version(skill_dir)

            # 3. Candidate dir 생성 — live 미수정 (F1/F3/F9)
            candidate_dir = self._create_candidate(skill_dir)

            # 4. candidate 생성 이후 consumed 캡처:
            #    candidate 복사는 LLM 미사용 → delta에 evolve+record 비용만 반영
            pre_consumed = self._budget.consumed if self._budget else 0

            # 5. LLM 진화 (candidate_dir에 쓰므로 live 안전)
            from core.skill_creator import evolve_skill
            success = evolve_skill(
                skill_dir=candidate_dir,
                feedback=feedback,
                error_log=error_log,
            )
            if not success:
                logger.warning("[Controller] evolve_skill 실패: %s", skill_id)
                self._discard_candidate(candidate_dir)
                return self._make_result(
                    skill_id=skill_id,
                    decision=EvolutionDecision.REJECTED,
                    candidate_dir=None,
                    new_version=None,
                    rejection_reason="evolve_skill_failed",
                    cost_tokens=(self._budget.consumed - pre_consumed) if self._budget else 0,
                    trigger=trigger,
                    old_version=old_version,
                )

            # 6. RunBudget — candidate skill.py 크기로 비용 추정 (§9.2 step 5, §9.2.1 한계)
            self._record_budget(candidate_dir)
            cost_tokens = (self._budget.consumed - pre_consumed) if self._budget else 0

            # 7. Sandbox 검증 (quick_guard + run_isolated)
            # knowledge skill: SKILL.md 기반 — skill.py 없음은 정상이므로 sandbox 스킵
            # action skill: skill.py 없으면 evolve 후 파일 생성 실패 → REJECTED
            skill_py = os.path.join(candidate_dir, "skill.py")
            if not os.path.exists(skill_py):
                if self._is_knowledge_skill(candidate_dir):
                    verified = True
                else:
                    logger.warning("[Controller] evolve 후 skill.py 미생성: %s", skill_id)
                    self._discard_candidate(candidate_dir)
                    return self._make_result(
                        skill_id=skill_id,
                        decision=EvolutionDecision.REJECTED,
                        candidate_dir=None,
                        new_version=None,
                        rejection_reason="skill_py_not_found_after_evolve",
                        cost_tokens=cost_tokens,
                        trigger=trigger,
                        old_version=old_version,
                    )
            else:
                verified = self._verify_sandbox(skill_py, skill_id)
            if not verified:
                self._discard_candidate(candidate_dir)
                return self._make_result(
                    skill_id=skill_id,
                    decision=EvolutionDecision.REJECTED,
                    candidate_dir=None,
                    new_version=None,
                    rejection_reason="sandbox_verification_failed",
                    cost_tokens=cost_tokens,
                    trigger=trigger,
                    old_version=old_version,
                )

            # 8. Quality gate (baseline=skill_dir: 진화 전 live 스킬)
            gate_result = self._run_quality_gate(candidate_dir, skill_id, baseline_dir=skill_dir)
            if gate_result is None:
                # gate 자체 예외 → DEFERRED (게이트 신뢰 불가, 보수적 폐기)
                logger.warning("[Controller] quality gate 미완료 (DEFERRED): %s", skill_id)
                self._discard_candidate(candidate_dir)
                return self._make_result(
                    skill_id=skill_id,
                    decision=EvolutionDecision.DEFERRED,
                    candidate_dir=None,
                    new_version=None,
                    rejection_reason="quality_gate_incomplete",
                    cost_tokens=cost_tokens,
                    trigger=trigger,
                    old_version=old_version,
                )

            if not gate_result.passed:
                reasons = "; ".join(gate_result.failure_reasons)
                logger.warning("[Controller] quality gate 실패 (%s): %s", skill_id, reasons)
                self._discard_candidate(candidate_dir)
                return self._make_result(
                    skill_id=skill_id,
                    decision=EvolutionDecision.REJECTED,
                    candidate_dir=None,
                    new_version=None,
                    rejection_reason=f"quality_gate_failed: {reasons}",
                    cost_tokens=cost_tokens,
                    trigger=trigger,
                    old_version=old_version,
                )

            # 9. Publish — candidate → live atomic (old_version은 try 블록 시작에서 이미 읽음)
            new_version = self._read_candidate_version(candidate_dir)
            self._publish(
                candidate_dir,
                skill_dir,
                skill_id=skill_id,
                old_version=old_version,
                new_version=new_version,
                trigger=trigger,
            )
            logger.info("[Controller] publish 완료: %s (%s)", skill_id, new_version)

            return self._make_result(
                skill_id=skill_id,
                decision=EvolutionDecision.PUBLISHED,
                candidate_dir=None,  # publish 후 candidate 경로 소멸 (§4.3 사후분석은 ledger 참조)
                new_version=new_version,
                rejection_reason=None,
                cost_tokens=cost_tokens,
                trigger=trigger,
                old_version=old_version,
            )

        except Exception as e:
            logger.error("[Controller] submit 예외 (%s): %s", skill_id, e)
            if candidate_dir and os.path.isdir(candidate_dir):
                self._discard_candidate(candidate_dir)
            return self._make_result(
                skill_id=skill_id,
                decision=EvolutionDecision.ERROR,
                candidate_dir=None,
                new_version=None,
                rejection_reason=f"exception: {e}",
                cost_tokens=cost_tokens,  # _record_budget 이후 예외 시 실제 소비 기록
                trigger=trigger,
                old_version=old_version,  # try 시작 시 읽은 값 (실패 시 "")
            )

    # ── 내부 메서드 ───────────────────────────────────────────────────────

    def _create_candidate(self, live_dir: str) -> str:
        """
        candidates/{skill_id}/{run_id}/{ts}_{trigger_hash}/ 형태로 candidate dir 생성.

        live 파일을 candidate로 복사하여 LLM 진화가 live를 수정하지 않도록 격리 (F1/F3/F9).
        """
        skill_id = os.path.basename(live_dir.rstrip(os.sep))
        run_id_part = self._run_id or "_no_run"
        ts = str(int(time.time() * 1000))
        candidate_dir = os.path.join(CANDIDATES_DIR, skill_id, run_id_part, ts)
        os.makedirs(candidate_dir, exist_ok=True)

        # live 파일 복사
        for name in os.listdir(live_dir):
            src = os.path.join(live_dir, name)
            dst = os.path.join(candidate_dir, name)
            if os.path.isfile(src):
                shutil.copy2(src, dst)

        # candidate lock 생성 (동시 진화 방지)
        lock_path = os.path.join(candidate_dir, ".candidate.lock")
        try:
            Path(lock_path).touch()
        except OSError:
            pass

        logger.debug("[Controller] candidate 생성: %s → %s", live_dir, candidate_dir)
        return candidate_dir

    @staticmethod
    def _is_knowledge_skill(candidate_dir: str) -> bool:
        """SKILL.md 있고 skill.py 없으면 knowledge skill (sandbox 검증 불필요)."""
        return (
            os.path.exists(os.path.join(candidate_dir, "SKILL.md")) or
            os.path.exists(os.path.join(candidate_dir, "skill.md"))
        )

    def _verify_sandbox(self, skill_py: str, skill_id: str) -> bool:
        """quick_guard + run_isolated. skill_evolution_safety.verify_*와 동일 로직."""
        try:
            from core.skill_evolution_safety import verify_evolved_skill_sandbox
            result = verify_evolved_skill_sandbox(skill_py, skill_id, timeout_sec=15)
            if not result:
                logger.warning("[Controller] sandbox 검증 실패: %s", skill_id)
            return result
        except Exception as e:
            logger.error("[Controller] sandbox 검증 예외 (%s): %s", skill_id, e)
            return False

    def _run_quality_gate(self, candidate_dir: str, skill_id: str, *, baseline_dir: str | None = None):
        """SkillQualityGate 실행. 예외 시 None 반환 (DEFERRED 트리거)."""
        try:
            from core.skill_quality_gate import SkillQualityGate
            gate = SkillQualityGate()
            return gate.validate(
                candidate_dir,
                baseline_skill_path=baseline_dir,
                auto_register=False,
            )
        except Exception as e:
            logger.error("[Controller] quality gate 예외 (%s): %s", skill_id, e)
            return None

    def _publish(
        self,
        candidate_dir: str,
        live_dir: str,
        *,
        skill_id: str,
        old_version: str,
        new_version: str,
        trigger: str,
    ) -> None:
        """
        candidate → live atomic publish (shutil.move, 같은 파티션).

        publish 후 SkillEvolutionBus.on_skill_evolved 발화.
        시그니처는 default(skill_dir="") 유지 + Controller가 명시 전달.
        """
        # lock 파일 제거
        lock_path = os.path.join(candidate_dir, ".candidate.lock")
        if os.path.exists(lock_path):
            try:
                os.remove(lock_path)
            except OSError:
                pass

        # 파일 목록 수집 (우선순위 파일 먼저, .bak/.candidate.lock 제외)
        _PRIORITY = ("skill.py", "SKILL.md", "meta.yaml")
        all_names = list(_PRIORITY) + [
            n for n in os.listdir(candidate_dir)
            if not n.startswith(".") and n not in _PRIORITY and not n.endswith(".bak")
        ]

        # live 파일 스냅샷 — partial publish 복구용 (아주 짧은 수명, 이동 완료 즉시 삭제)
        # 스냅샷 실패 시 publish 자체를 abort — 불완전 복구 방지
        _SNAP_SUFFIX = ".__publish_snap__"
        live_snapshots: dict[str, str] = {}  # live_file → snap_path
        for name in all_names:
            live_file = os.path.join(live_dir, name)
            if os.path.isfile(live_file):
                snap = live_file + _SNAP_SUFFIX
                try:
                    shutil.copy2(live_file, snap)
                    live_snapshots[live_file] = snap
                except Exception as snap_exc:
                    # 스냅샷 없이 publish하면 복원 보장 불가 → abort
                    for existing_snap in live_snapshots.values():
                        try:
                            os.remove(existing_snap)
                        except OSError:
                            pass
                    self._discard_candidate(candidate_dir)
                    raise RuntimeError(
                        f"[Controller] live 스냅샷 생성 실패, publish abort: {live_file}"
                    ) from snap_exc

        try:
            for name in all_names:
                candidate_file = os.path.join(candidate_dir, name)
                live_file = os.path.join(live_dir, name)
                if not os.path.isfile(candidate_file):
                    continue
                shutil.move(candidate_file, live_file)
        except Exception as move_exc:
            # partial publish → 스냅샷으로 기존 live 복원, 신규 live 파일 제거, candidate 폐기
            logger.error("[Controller] publish 이동 실패 — live 복원 시작: %s", move_exc)
            for live_file, snap in live_snapshots.items():
                try:
                    shutil.move(snap, live_file)
                except Exception as rb_exc:
                    logger.warning("[Controller] live 복원 실패 (%s): %s", live_file, rb_exc)
                    # 복원 실패 시 snap 파일이 live dir에 잔류하지 않도록 제거 시도
                    try:
                        if os.path.exists(snap):
                            os.remove(snap)
                    except OSError:
                        pass
            # 신규 파일(live에 없던 것)은 스냅샷이 없으므로 이동 직후 제거해야 live 오염 방지
            for name in all_names:
                live_file = os.path.join(live_dir, name)
                if live_file not in live_snapshots and os.path.isfile(live_file):
                    try:
                        os.remove(live_file)
                    except OSError as rm_exc:
                        logger.warning("[Controller] 신규 live 파일 제거 실패 (%s): %s", live_file, rm_exc)
            self._discard_candidate(candidate_dir)
            # submit의 except: os.path.isdir(candidate_dir) == False → 재폐기 없음
            raise

        # 성공 — 스냅샷 정리 후 candidate 폐기
        for snap in live_snapshots.values():
            if os.path.exists(snap):
                try:
                    os.remove(snap)
                except OSError:
                    pass
        self._discard_candidate(candidate_dir)

        # SkillEvolutionBus 통지 — 캐시 무효화 7단계 체인 트리거 (§1.3)
        # decision=PUBLISHED 명시: hook 라우팅이 §7.2 EVOLUTION_PUBLISHED 분기로 진입
        try:
            from core.skill_evolution_bus import SkillEvolutionBus
            SkillEvolutionBus.get_instance().on_skill_evolved(
                skill_id=skill_id,
                skill_dir=live_dir,
                old_version=old_version,
                new_version=new_version,
                trigger=trigger,
                decision=EvolutionDecision.PUBLISHED,
            )
        except Exception as bus_exc:
            logger.error("[Controller] SkillEvolutionBus 통지 실패 (%s): %s", skill_id, bus_exc)

    def _discard_candidate(self, candidate_dir: str) -> None:
        """candidate dir 폐기 (publish 실패 / REJECTED / DEFERRED / ERROR)."""
        if candidate_dir and os.path.isdir(candidate_dir):
            try:
                shutil.rmtree(candidate_dir)
                logger.debug("[Controller] candidate 폐기: %s", candidate_dir)
            except Exception as e:
                logger.warning("[Controller] candidate 폐기 실패: %s — %s", candidate_dir, e)

    def _record_budget(self, candidate_dir: str) -> None:
        """candidate skill.py 크기로 RunBudget record() 호출 (§9.2 step 5)."""
        if not self._budget:
            return
        try:
            skill_py = os.path.join(candidate_dir, "skill.py")
            content = Path(skill_py).read_text(encoding="utf-8")
            self._budget.record(content)
        except (OSError, IOError) as e:
            logger.warning("[Controller] skill.py 읽기 실패 (비용 추정 불가): %s", e)

    def _read_candidate_version(self, candidate_dir: str) -> str:
        """candidate meta.yaml에서 version 읽기. 실패 시 'unknown'."""
        return self._read_version_from_dir(candidate_dir)

    def _read_live_version(self, live_dir: str) -> str:
        """live meta.yaml에서 old_version 읽기. 실패 시 'unknown'."""
        return self._read_version_from_dir(live_dir)

    def _read_version_from_dir(self, dir_path: str) -> str:
        try:
            import yaml  # type: ignore[import]
            meta_path = os.path.join(dir_path, "meta.yaml")
            if os.path.exists(meta_path):
                with open(meta_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                return data.get("version", "unknown")
        except Exception:
            pass
        return "unknown"

    def _make_result(
        self,
        *,
        skill_id: str,
        decision: EvolutionDecision,
        candidate_dir: Optional[str],
        new_version: Optional[str],
        rejection_reason: Optional[str],
        cost_tokens: int,
        trigger: str,
        old_version: str = "",
    ) -> EvolutionResult:
        """EvolutionResult 생성 + Ledger append + ROLLED_BACK RunEvent (PUBLISHED 제외)."""
        result = EvolutionResult(
            skill_id=skill_id,
            decision=decision,
            candidate_dir=candidate_dir,
            new_version=new_version,
            rejection_reason=rejection_reason,
            cost_tokens=cost_tokens,
        )
        self._append_ledger(result, trigger=trigger, old_version=old_version)
        if decision != EvolutionDecision.PUBLISHED:
            self._emit_rolled_back_event(result, trigger=trigger)
        return result

    def _emit_rolled_back_event(self, result: EvolutionResult, *, trigger: str) -> None:
        """REJECTED/DEFERRED/ERROR 결정 시 EVOLUTION_ROLLED_BACK RunEvent 기록."""
        try:
            from core.events.run_event import RunEvent, RunEventType, get_default_store
            event = RunEvent(
                run_id=self._run_id or "unknown",
                event_type=RunEventType.EVOLUTION_ROLLED_BACK,
                payload={
                    "skill_id": result.skill_id,
                    "decision": result.decision.value,
                    "rejection_reason": result.rejection_reason,
                    "trigger": trigger,
                    "cost_tokens": result.cost_tokens,
                },
            )
            get_default_store().append(event)
        except Exception as e:
            logger.warning("[Controller] EVOLUTION_ROLLED_BACK 이벤트 기록 실패: %s", e)

    def _append_ledger(self, result: EvolutionResult, *, trigger: str, old_version: str = "") -> None:
        """EvolutionLedger.append — ledger=None이면 no-op (병렬 트랙, §4.4)."""
        if self._ledger is None:
            return
        try:
            import datetime
            from core.evolution_ledger import LedgerEntry
            entry = LedgerEntry(
                skill_id=result.skill_id,
                old_version=old_version,
                new_version=result.new_version or "",
                trigger=trigger,
                decision=result.decision,
                cost_tokens=result.cost_tokens,
                candidate_dir=result.candidate_dir or "",
                rejection_reason=result.rejection_reason,
                run_id=self._run_id,
                ts=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
            self._ledger.append(entry)
        except Exception as e:
            logger.warning("[Controller] ledger append 실패: %s", e)
