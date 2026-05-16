"""
core/fsa_loop.py
================
Full Self Automation (FSA) Loop Orchestrator — ISE와 동일한 에스컬레이션 파이프라인.

ISE Loop과 동일한 ANALYZE → ESCALATE(Level 1~5) → ACT 구조를 사용하되,
루프 횟수만 max_cycles(기본 5회)로 제한한다.

에스컬레이션 레벨:
  Level 1: 단순 재시도 (피드백 주입)
  Level 2: 전략 피벗 (접근법 변경)
  Level 3: 설계 재시작 (아키텍처 재구성)
  Level 4: 스킬 진화 + 설계 재시작
  Level 5: 태스크 분해 (서브태스크 분할 → 각각 실행)

탈출 조건:
  - 성공 (ok=True)
  - max_cycles 초과
  - 사용자 명시 중단
  - KeyboardInterrupt

Git 범위 원칙:
  - commit/rollback은 workspace(프로젝트 디렉토리) 안에서만 동작한다.
  - factory 코드(core/, skills/ 등)는 에이전트 git 조작 범위 밖이다.
  - rollback은 tracked 파일 변경만 되돌린다. untracked 파일은 보존된다.
"""
from __future__ import annotations

import logging
import os
import json
import re
import time
import inspect

logger = logging.getLogger(__name__)

from core.agent_runner import AgentRunner
from core.git_manager import GitManager
from core.utils import now_iso, print_agent_msg, safe_json_load
from core.evaluator import StrategyEvaluator
from core.config_paths import SKILLS_DIR, PROJECT_SKILLS_DIR
from core.ise_strategy_ledger import StrategyLedger
from core.ise_analyzer import ISEAnalyzer, ISEAnalysis
from core.ise_redesigner import ISERedesigner
from core.ise_stall_detector import StallDetector


def parse_evaluator_response(result: dict) -> dict:
    """Parse an evaluator agent's run result into action/reasoning/new_instruction."""
    if not result.get("ok"):
        return {"action": "abort", "reasoning": f"Evaluator agent failed: {result.get('reason', '')}", "new_instruction": ""}

    output = result.get("output", "") or result.get("reason", "")
    if isinstance(output, dict):
        return {
            "action": str(output.get("action", "abort")).strip().lower(),
            "reasoning": str(output.get("reasoning", "")),
            "new_instruction": str(output.get("new_instruction", "")),
        }

    data = safe_json_load(output) if isinstance(output, str) else {}
    if data and "action" in data:
        return {
            "action": str(data.get("action", "abort")).strip().lower(),
            "reasoning": str(data.get("reasoning", "")),
            "new_instruction": str(data.get("new_instruction", "")),
        }

    return {"action": "abort", "reasoning": "Could not parse evaluator response", "new_instruction": ""}


class FSALoop:
    """
    Full Self Automation Loop — ISE와 동일한 에스컬레이션 파이프라인 (max_cycles 제한).
    """

    def __init__(self, runner: AgentRunner, agent_mgr=None, visualizer=None):
        self.runner = runner
        self.agent_mgr = agent_mgr
        self._visualizer = visualizer
        self.max_cycles = 5
        # DEFERRED/ERROR로 진화가 불가능했던 스킬 — run 중 재시도 차단
        self._evolution_failed_skills: set[str] = set()

        # ISE-level 분석/재설계/정체감지 엔진
        model_name = "gemini-1.5-pro-latest"
        if hasattr(runner, "mr") and hasattr(runner.mr, "pick"):
            model_name = runner.mr.pick("evaluator") or model_name
        self.analyzer = ISEAnalyzer(model_name=model_name)
        self.redesigner = ISERedesigner(model_name=model_name)
        self.stall_detector = StallDetector()

        # Legacy fallback evaluator (StrategyEvaluator)
        self.evaluator = StrategyEvaluator(model_name=model_name)

        # NOTE: GitManager는 __init__에서 생성하지 않는다.
        # run_mission()에서 workspace를 받아 그 범위로 생성한다.

    def run_mission(
        self,
        agent: dict,
        task_input: str,
        run_id: str,
        workspace: str | None = None,
        runtime_workspace: str | None = None,
        lineage_id: str | None = None,
        initial_failure_result: dict | None = None,
    ) -> dict:
        """
        FSA 메인 루프 — ISE와 동일한 에스컬레이션 파이프라인.

        lineage_id: 야간 파이프라인 lineage 추적용 ID.
        initial_failure_result: 이미 실행된 실패 결과. 제공 시 cycle 1에서 실행을 건너뛰고
            분석부터 시작한다 (dynamic_orchestrator가 최초 실행 후 위임할 때 사용).

        Returns:
            {
                "ok": bool,
                "reason": str,
                "meta_cycles": int,
                "max_escalation_level": int,
                "strategy_ledger": dict,
                "lineage_id": str | None,
            }
        """
        # run 단위 상태 초기화
        self._evolution_failed_skills = set()

        # ── 워크스페이스 설정 ──
        target_workspace = workspace or os.getcwd()
        if not target_workspace or not os.path.isdir(target_workspace):
            return {"ok": False, "reason": f"유효하지 않은 워크스페이스: {target_workspace}"}
        state_workspace = os.path.abspath(runtime_workspace) if runtime_workspace else target_workspace
        os.makedirs(state_workspace, exist_ok=True)
        self.workspace = target_workspace
        git = GitManager(target_workspace)

        agent_name = agent.get("name", "Agent") if isinstance(agent, dict) else "Agent"
        _lineage_id = lineage_id or run_id

        # ── lineage 원장 로드 ──
        try:
            from core.lineage_ledger import get_lineage_ledger
            _ledger_obj = get_lineage_ledger(state_workspace)
        except Exception:
            _ledger_obj = None

        # ── 전략 원장 초기화 ──
        ledger = StrategyLedger(run_id=run_id, original_task=task_input)
        current_task = task_input
        current_agent = agent
        max_level_reached = 0
        evolved_skill_name = None
        gate_result = None
        last_analysis = None  # P1: 실패 종료 경로에서 root_cause/패턴 채우기 위해 보존

        print_agent_msg("FSA", f"풀 셀프 자동화 모드(FSA) 시작: {run_id}", "🌀")
        print_agent_msg("FSA", f"최대 {self.max_cycles} 사이클 | workspace={target_workspace}", "📋")
        if _lineage_id:
            print_agent_msg("FSA", f"lineage_id={_lineage_id}", "🔗")

        try:
            for cycle in range(1, self.max_cycles + 1):
                # ── 토큰 예산 체크 (dynamic_orchestrator와 동일한 가드) ──
                try:
                    from core.run_budget import get_run_budget
                    if get_run_budget().is_exhausted():
                        print_agent_msg("FSA", "Run budget exhausted — stopping.", "💰")
                        break
                except Exception:
                    pass

                if self._visualizer:
                    self._visualizer.update_from_fsa_step(agent_name, "execute", cycle, self.max_cycles)
                else:
                    print(
                        f"\n🔄 [Cycle {cycle}/{self.max_cycles}] "
                        f"실행 (최대 에스컬레이션: Level {max_level_reached})"
                    )

                # ── 정체 감지 ──
                stall_action = self.stall_detector.check(ledger)
                if stall_action == "human_escalation":
                    human_result = self._request_human_help(ledger, cycle)
                    if human_result.get("continue"):
                        hint = human_result.get("hint", "")
                        if hint:
                            current_task = (
                                f"[사용자 힌트]\n{hint}\n\n"
                                f"[Original Task]\n{task_input}"
                            )
                        ledger.reset_escalation_counters()
                        continue
                    else:
                        ledger.save(state_workspace)
                        return {
                            "ok": False,
                            "reason": human_result.get("reason", "사용자 중단"),
                            "meta_cycles": cycle,
                            "max_escalation_level": max_level_reached,
                            "strategy_ledger": ledger.to_dict(),
                        }
                elif stall_action == "creativity_injection":
                    current_task = self.redesigner.inject_creativity(current_task, ledger)

                # ── Step 1: Pre-Commit (워크스페이스 스냅샷) ──
                # cycle 1에서 initial_failure_result가 있으면 실행 생략 (이미 실행됨)
                _use_initial_failure = cycle == 1 and initial_failure_result is not None
                if not _use_initial_failure:
                    git.commit(f"AEE Auto-Save: {run_id} Cycle {cycle}")

                # ── Step 2: EXECUTE ──
                if _use_initial_failure:
                    result = initial_failure_result
                    print_agent_msg("FSA", "초기 실패 결과 인수인계, 실행 건너뜀", "⏩")
                else:
                    result = self._run_agent(
                        current_agent,
                        current_task,
                        run_id=f"{run_id}_c{cycle}",
                        workspace=target_workspace,
                        runtime_workspace=state_workspace,
                    )

                # ── 성공 체크 ──
                if result.get("ok"):
                    if self._visualizer:
                        self._visualizer.mark_completed(agent_name)
                    else:
                        print_agent_msg("FSA", f"Cycle {cycle}에서 성공!", "✅")
                    ledger.save(state_workspace)
                    self._record_episode(task_input, result, evolved_skill_name, gate_result, cycle)
                    if _ledger_obj:
                        try:
                            _ledger_obj.on_task_success(_lineage_id, max_level_reached)
                        except Exception:
                            pass
                    return {
                        **result,
                        "meta_cycles": cycle,
                        "max_escalation_level": max_level_reached,
                        "strategy_ledger": ledger.to_dict(),
                        "lineage_id": _lineage_id,
                    }

                # ── Step 3: Rollback (workspace tracked 파일만) ──
                if self._visualizer:
                    self._visualizer.update_from_fsa_step(agent_name, "eval", cycle, self.max_cycles)
                else:
                    print(f"⚠️ [Cycle {cycle}] 실패: {str(result.get('reason', ''))[:120]}")

                # cycle 1 + initial_failure_result인 경우도 rollback을 수행한다.
                # pre-commit이 없어 HEAD가 없는 순수 신규 워크스페이스에서는 no-op.
                try:
                    git.rollback()
                except Exception as e:
                    print_agent_msg("Critical", f"Rollback 실패: {e}", "🛑")

                # ── Step 4: ANALYZE (ISE-style 구조화 분석) ──
                print_agent_msg("FSA", "실패 분석 중...", "🔍")
                analysis = self.analyzer.analyze_failure(
                    task=current_task,
                    result=result,
                    ledger=ledger,
                )
                last_analysis = analysis  # P1: 실패 종료 시 episode에 패스

                # ── Step 5: ESCALATE — 에스컬레이션 레벨 결정 ──
                level = self._decide_escalation(ledger, analysis)
                level, detected_skill_dir = self._apply_evolution_guard(level, result, analysis)
                max_level_reached = max(max_level_reached, level)

                # 원장에 시도 기록
                ledger.record_attempt(
                    meta_cycle=cycle,
                    task_input=current_task,
                    result=result,
                    analysis=analysis.to_dict(),
                    escalation_level=level,
                    strategy_description=analysis.suggested_strategy,
                )

                # lineage 원장 업데이트
                if _ledger_obj:
                    try:
                        _ledger_obj.on_task_failure(
                            _lineage_id,
                            new_level=level,
                            reason=str(result.get("reason", ""))[:200],
                        )
                    except Exception:
                        pass

                print_agent_msg(
                    "FSA",
                    f"에스컬레이션 Level {level} | "
                    f"에러: {analysis.error_category} | "
                    f"근본적: {analysis.is_fundamental}",
                    "📊",
                )

                # ── Step 6: ACT — 레벨별 대응 ──
                if level == 1:
                    current_task = self.redesigner.apply_retry_feedback(task_input, analysis)

                elif level == 2:
                    current_task = self.redesigner.apply_pivot(task_input, analysis, ledger)

                elif level == 3:
                    print_agent_msg("FSA", "설계 재시작: 아키텍처를 전면 재구성합니다", "🏗️")
                    current_task = self.redesigner.redesign_task(task_input, analysis, ledger)

                elif level == 4:
                    print_agent_msg("FSA", "스킬 진화 + 설계 재시작", "🧬")
                    gate_result = self._try_evolve_failed_skill(
                        error_reason=result.get("reason", ""),
                        eval_reasoning=analysis.evaluator_reasoning,
                        run_id=run_id,
                        cycle=cycle,
                        skill_dir=detected_skill_dir,
                    )
                    if gate_result is not None and gate_result.passed:
                        evolved_skill_name = (
                            gate_result.skill_path.split(os.sep)[-1]
                            if gate_result.skill_path else None
                        )
                    if gate_result is None:
                        # 진화 실패/불가/미탐지 → 전략 전환
                        current_task = self.redesigner.apply_pivot(task_input, analysis, ledger)
                    else:
                        # gate_result는 항상 GateResult(passed=True) — PUBLISHED 성공
                        current_task = self.redesigner.redesign_task(task_input, analysis, ledger)

                elif level == 5:
                    print_agent_msg("FSA", "태스크 분해: 서브태스크로 분할 실행합니다", "🔀")
                    sub_results = self._decompose_and_execute(
                        task_input, current_agent, analysis, ledger,
                        run_id, cycle, target_workspace, state_workspace,
                    )
                    if sub_results and all(r.get("ok") for r in sub_results):
                        print_agent_msg("FSA", "모든 서브태스크 성공!", "✅")
                        ledger.save(state_workspace)
                        success_result = {
                            "ok": True,
                            "reason": "FSA 태스크 분해 후 전체 성공",
                            "meta_cycles": cycle,
                            "max_escalation_level": 5,
                            "strategy_ledger": ledger.to_dict(),
                        }
                        self._record_episode(task_input, success_result, evolved_skill_name, gate_result, cycle)
                        return success_result
                    # 분해 실패: 카운터 리셋 후 피벗
                    print_agent_msg("FSA", "서브태스크 일부 실패, 카운터 리셋 후 재시도", "🔁")
                    ledger.reset_escalation_counters()
                    current_task = self.redesigner.apply_pivot(task_input, analysis, ledger)

                # ── Step 7: 원장 영속화 ──
                ledger.save(state_workspace)

                # ── 지수 백오프 (같은 레벨 반복 시) ──
                backoff = self.stall_detector.compute_backoff(ledger, level)
                if backoff > 0:
                    print_agent_msg("FSA", f"백오프 대기: {backoff:.1f}초", "⏳")
                    time.sleep(backoff)

        except KeyboardInterrupt:
            print_agent_msg("FSA", "사용자 인터럽트 — 루프 중단", "⛔")
            ledger.save(state_workspace)
            return {
                "ok": False,
                "reason": "KeyboardInterrupt",
                "meta_cycles": cycle if 'cycle' in dir() else 0,
                "max_escalation_level": max_level_reached,
                "strategy_ledger": ledger.to_dict(),
                "failure_patterns": ["user_interrupt"],
                "root_cause": "KeyboardInterrupt",
            }

        # ── max_cycles 초과 ──
        # P1: last_analysis가 있으면 root_cause/error_category를 final_result에 노출 →
        # _record_episode가 EpisodeRecord.failure_pattern/root_cause를 채울 수 있게 함.
        _final_patterns: list[str] = []
        _final_root_cause = ""
        if last_analysis is not None:
            if getattr(last_analysis, "error_category", ""):
                _final_patterns.append(str(last_analysis.error_category))
            _final_root_cause = str(getattr(last_analysis, "root_cause", "") or "")
        final_result = {
            "ok": False,
            "reason": f"최대 재시도 횟수({self.max_cycles}회) 초과로 중단되었습니다.",
            "meta_cycles": self.max_cycles,
            "max_escalation_level": max_level_reached,
            "strategy_ledger": ledger.to_dict(),
            "lineage_id": _lineage_id,
            "failure_patterns": _final_patterns,
            "root_cause": _final_root_cause,
        }
        ledger.save(state_workspace)
        self._record_episode(task_input, final_result, evolved_skill_name, gate_result, self.max_cycles)
        return final_result

    # ══════════════════════════════════════════════════════════════
    #  에스컬레이션 결정 (ISE와 동일)
    # ══════════════════════════════════════════════════════════════

    def _decide_escalation(self, ledger: StrategyLedger, analysis: ISEAnalysis) -> int:
        """
        전략 원장과 분석 결과를 바탕으로 에스컬레이션 레벨을 결정한다.

        Level 1: 첫 실패 또는 일시적 에러
        Level 2: 같은 에러 반복 2회+ (전략 피벗 필요)
        Level 3: 피벗 3회+ 실패 or abort 판정 or 근본적 결함
        Level 4: 설계 재시작 실패 + 스킬 결함 식별
        Level 5: Level 4 실패 (태스크 분해)
        """
        repeat_count = ledger.consecutive_same_error_count()
        pivot_count = ledger.pivot_count()
        redesign_count = ledger.redesign_count()

        # 근본적 결함이면 바로 Level 3 이상으로 에스컬레이션
        if analysis.is_fundamental:
            if redesign_count == 0:
                return 3
            elif ledger.has_skill_failure():
                return 4
            else:
                return 5

        # abort 판정이면 설계 재시작
        if analysis.evaluator_action == "abort":
            if redesign_count == 0:
                return 3
            elif ledger.has_skill_failure():
                return 4
            else:
                return 5

        # 점진적 에스컬레이션
        if repeat_count == 0:
            return 1
        elif repeat_count <= 2 and pivot_count < 3:
            return 2
        elif pivot_count >= 3 and redesign_count == 0:
            return 3
        elif redesign_count >= 1 and ledger.has_skill_failure():
            return 4
        else:
            if redesign_count >= 2 or ledger.decompose_count() == 0:
                return 5
            return 2

    # ══════════════════════════════════════════════════════════════
    #  태스크 분해 + 실행 (ISE와 동일)
    # ══════════════════════════════════════════════════════════════

    def _decompose_and_execute(
        self,
        original_task: str,
        agent: dict,
        analysis: ISEAnalysis,
        ledger: StrategyLedger,
        run_id: str,
        cycle: int,
        workspace: str,
        runtime_workspace: str | None = None,
    ) -> list[dict]:
        """태스크를 분해하고 각 서브태스크를 개별 실행한다."""
        subtasks = self.redesigner.decompose_task(original_task, analysis, ledger)
        if not subtasks:
            return [{"ok": False, "reason": "태스크 분해 실패"}]

        print_agent_msg("FSA", f"{len(subtasks)}개 서브태스크로 분해됨", "📋")
        results = []
        completed_indices: set[int] = set()

        # 의존 관계 순서대로 실행
        for priority_pass in range(1, len(subtasks) + 1):
            for i, st in enumerate(subtasks):
                if i in completed_indices:
                    continue
                deps = st.get("dependencies", [])
                if not all(d in completed_indices for d in deps):
                    continue

                sub_task = st["subtask"]
                sub_run_id = f"{run_id}_c{cycle}_sub{i}"

                print_agent_msg(
                    "FSA",
                    f"서브태스크 {i + 1}/{len(subtasks)}: {sub_task[:80]}...",
                    "▶️",
                )

                sub_result = self._run_agent(
                    agent,
                    sub_task,
                    run_id=sub_run_id,
                    workspace=workspace,
                    runtime_workspace=runtime_workspace,
                )
                results.append(sub_result)

                if sub_result.get("ok"):
                    completed_indices.add(i)
                    print_agent_msg("FSA", f"서브태스크 {i + 1} 완료", "✅")
                else:
                    print_agent_msg(
                        "FSA",
                        f"서브태스크 {i + 1} 실패: {sub_result.get('reason', '')[:100]}",
                        "❌",
                    )
                    return results

            if len(completed_indices) == len(subtasks):
                break

        return results

    def _run_agent(
        self,
        agent: dict,
        task_input: str,
        run_id: str,
        workspace: str,
        runtime_workspace: str | None = None,
    ) -> dict:
        """Call AgentRunner with runtime_workspace when the runner supports it."""
        params = inspect.signature(self.runner.run).parameters
        kwargs = {}
        if "run_id" in params:
            kwargs["run_id"] = run_id
        if "auto_approve" in params:
            kwargs["auto_approve"] = True
        if "workspace" in params:
            kwargs["workspace"] = workspace
        if "runtime_workspace" in params:
            kwargs["runtime_workspace"] = runtime_workspace
        return self.runner.run(agent, task_input, **kwargs)

    # ══════════════════════════════════════════════════════════════
    #  사용자 에스컬레이션 (ISE와 동일)
    # ══════════════════════════════════════════════════════════════

    def _request_human_help(self, ledger: StrategyLedger, cycle: int) -> dict:
        """사용자에게 도움을 요청한다. abort가 아닌 일시정지."""
        print("\n" + "=" * 60)
        print("  [FSA] 정체 감지 — 사용자 도움 요청")
        print("=" * 60)
        print(f"  사이클: {cycle}/{self.max_cycles}")
        print(f"  총 시도: {len(ledger.entries)}회")
        print(f"  경과 시간: {ledger.total_elapsed_sec():.0f}초")

        top_errors = ledger.top_error_signatures(3)
        if top_errors:
            print(f"\n  반복 에러 패턴:")
            for sig, count in top_errors:
                print(f"    - [{count}회] {sig[:80]}")

        failed_descs = ledger.failed_strategy_descriptions(5)
        if failed_descs:
            print(f"\n  실패한 접근법:")
            for desc in failed_descs:
                print(f"    - {desc}")

        print(f"\n  레벨별 시도 횟수: {ledger.level_counts()}")
        print()
        print("  [1] 힌트를 제공하고 계속 (hint)")
        print("  [2] 파일을 수동 수정 후 계속 (manual)")
        print("  [3] 완전 중단 (abort)")
        print()

        try:
            choice = input("  선택 [1/2/3]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return {"ok": False, "reason": "FSA 루프: 입력 불가 — 중단", "continue": False}

        if choice in ("1", "hint"):
            try:
                hint = input("  힌트 입력: ").strip()
            except (EOFError, KeyboardInterrupt):
                return {"ok": False, "reason": "FSA 루프: 입력 불가 — 중단", "continue": False}
            ledger.record_human_hint(hint)
            print_agent_msg("FSA", f"사용자 힌트 반영: {hint[:80]}", "💡")
            return {"ok": False, "reason": "human_hint_provided", "hint": hint, "continue": True}
        elif choice in ("2", "manual"):
            try:
                input("  수정 후 Enter를 누르세요...")
            except (EOFError, KeyboardInterrupt):
                pass
            print_agent_msg("FSA", "수동 수정 반영, 루프 계속", "🔧")
            return {"ok": False, "reason": "manual_edit", "continue": True}
        else:
            return {"ok": False, "reason": "FSA 루프: 사용자 중단", "continue": False}

    # ══════════════════════════════════════════════════════════════
    #  스킬 진화 (기존 FSA 로직 보존)
    # ══════════════════════════════════════════════════════════════

    def _apply_evolution_guard(
        self, level: int, result: dict, analysis
    ) -> tuple[int, str | None]:
        """Level 4→5 강제 가드: 현재 사이클 탐지 스킬이 이미 차단됐을 때만 강제.

        탐지 실패(_cand_name=None) 시에도 Level 5로 강제해 무한 루프를 방지한다.
        Returns (adjusted_level, detected_skill_dir_or_None).
        detected_skill_dir는 _try_evolve_failed_skill에 전달해 이중 탐색을 방지한다.
        """
        if level != 4 or not self._evolution_failed_skills:
            return level, None
        cand_dir = self._detect_failed_skill_dir(
            result.get("reason", ""), analysis.evaluator_reasoning
        )
        cand_name = os.path.basename(cand_dir) if cand_dir else None
        if not cand_name:
            logger.warning("[EvolutionGuard] 스킬명 탐지 실패 — Level 5 강제 에스컬레이션")
            return 5, None
        if cand_name in self._evolution_failed_skills:
            return 5, cand_dir
        return level, cand_dir

    def _try_evolve_failed_skill(
        self,
        error_reason: str,
        eval_reasoning: str,
        run_id: str,
        cycle: int,
        skill_dir: str | None = None,
    ):
        """
        실패 원인에서 스킬 이름을 추출하고 SelfEvolutionController로 진화시킵니다.

        Returns:
            GateResult | None: PUBLISHED → GateResult(passed=True), 그 외 모두 → None
        """
        if skill_dir is None:
            skill_dir = self._detect_failed_skill_dir(error_reason, eval_reasoning)
        if not skill_dir:
            return None

        skill_name = os.path.basename(skill_dir)

        # 이미 이 run에서 DEFERRED/ERROR 이력이 있는 스킬은 재시도하지 않음
        if skill_name in self._evolution_failed_skills:
            logger.info("[SkillEvolve] 이미 진화 불가 판정(%s) — 재시도 스킵", skill_name)
            return None

        print_agent_msg("SkillEvolve", f"스킬 진화 시도: {skill_name} (cycle {cycle})", "🧬")

        from core.skill_evolution_controller import SelfEvolutionController
        from core.evolution_types import EvolutionDecision
        from core.skill_quality_gate import GateResult

        controller = SelfEvolutionController(run_id=run_id)
        result = controller.submit(
            skill_dir=skill_dir,
            skill_id=skill_name,
            trigger="fsa_failure",
            feedback=eval_reasoning,
            error_log=error_reason,
        )

        if result.decision == EvolutionDecision.PUBLISHED:
            try:
                self._hot_reload_registry(skill_name)
            except Exception as reload_exc:
                logger.error("[SkillEvolve] hot_reload 예외 (%s): %s", skill_name, reload_exc)
            print_agent_msg("SkillEvolve", f"스킬 진화 성공: {skill_name}", "✅")
        else:
            print_agent_msg(
                "SkillEvolve",
                f"진화 결과: {result.decision.value} ({result.rejection_reason})",
                "⚠️",
            )

        # PUBLISHED만 성공 — REJECTED/DEFERRED/ERROR 모두 run 내 재시도 차단
        if result.decision != EvolutionDecision.PUBLISHED:
            self._evolution_failed_skills.add(skill_name)
            return None

        return GateResult(
            passed=True,
            skill_path=skill_dir,
            recommended_stage="active",
            pass_rate=1.0,
            eval_report_path="",
        )

    def _detect_failed_skill_dir(self, error_reason: str, eval_reasoning: str) -> str | None:
        """에러 로그에서 실패한 스킬 디렉토리를 추출합니다."""
        combined = f"{error_reason}\n{eval_reasoning}".lower()

        search_dirs = []
        if PROJECT_SKILLS_DIR and os.path.isdir(PROJECT_SKILLS_DIR):
            search_dirs.append(PROJECT_SKILLS_DIR)
        if os.path.isdir(SKILLS_DIR):
            search_dirs.append(SKILLS_DIR)

        _SKIP = {"forge", "_external_cache", "__pycache__", "warehouse"}
        for base_dir in search_dirs:
            try:
                for item in os.listdir(base_dir):
                    skill_dir = os.path.join(base_dir, item)
                    if not os.path.isdir(skill_dir):
                        continue
                    if item.startswith(".") or item in _SKIP:
                        continue
                    skill_name_lower = item.lower().replace("-", "_")
                    pattern = rf"(?<![a-zA-Z0-9_]){re.escape(skill_name_lower)}(?![a-zA-Z0-9_])"
                    if re.search(pattern, combined) or re.search(
                        rf"(?<![a-zA-Z0-9_]){re.escape(item.lower())}(?![a-zA-Z0-9_])", combined
                    ):
                        return skill_dir
            except Exception:
                continue

        return None

    # ══════════════════════════════════════════════════════════════
    #  에피소드 기록 / 유틸
    # ══════════════════════════════════════════════════════════════

    def _record_episode(
        self,
        task_input: str,
        result: dict,
        evolved_skill_name: str | None,
        gate_result,
        cycle: int,
    ) -> None:
        """실행 에피소드를 UnifiedMemoryFacade에 비동기 기록합니다 (graceful degradation)."""
        try:
            from core.memory_system.facade import UnifiedMemoryFacade
            from core.memory_system.models import EpisodeRecord
            facade = UnifiedMemoryFacade.get_instance()
            if facade._initialised:
                _patterns = result.get("failure_patterns") or []
                _fp = ";".join(str(p) for p in _patterns)[:120] if not result.get("ok") else ""
                # max_cycles 종료 경로에서 reason은 "최대 재시도 횟수…" 고정 문자열이므로
                # last_analysis에서 채운 root_cause를 우선해야 의미 있는 정보가 보존됨.
                _rc = str(result.get("root_cause") or result.get("reason") or "")[:200] if not result.get("ok") else ""
                episode = EpisodeRecord(
                    task_input=task_input,
                    outcome="success" if result.get("ok") else "failure",
                    event_type="fsa_cycle",
                    failure_pattern=_fp,
                    root_cause=_rc,
                    metadata={
                        "failure_patterns": _patterns,
                        "skill_evolved": evolved_skill_name or "",
                        "gate_result": gate_result.pass_rate if gate_result else 0.0,
                        "cycle_count": cycle,
                    },
                )
                from core.agent_runner import _run_async_safe
                _run_async_safe(facade.record_episode(episode))
        except Exception:
            pass

    def _hot_reload_registry(self, skill_name: str):
        """레지스트리를 강제 리로딩하여 진화된 스킬을 반영합니다."""
        try:
            from core.skill_registry import get_global_registry
            registry = get_global_registry()
            registry.auto_load_from_directories(force=True)
            print_agent_msg("SkillEvolve", f"레지스트리 핫리로딩 완료 ({registry.count()}개 스킬)", "🔄")
        except Exception as e:
            print_agent_msg("SkillEvolve", f"핫리로딩 실패: {e}", "⚠️")

    def _read_skill_version(self, skill_dir: str) -> str:
        """meta.yaml에서 현재 스킬 버전을 읽어옵니다."""
        meta_path = os.path.join(skill_dir, "meta.yaml")
        if not os.path.exists(meta_path):
            return "0.1.0"
        try:
            import yaml
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = yaml.safe_load(f) or {}
            return str(meta.get("version", "0.1.0"))
        except Exception:
            return "0.1.0"
