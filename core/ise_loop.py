"""
core/ise_loop.py
================
ISELoop — FSALoop 얇은 래퍼 (Phase 3에서 dead code 해소).

FSALoop이 Level 1~5 에스컬레이션 파이프라인을 완전 구현하므로
ISELoop은 FSALoop.run_mission으로 직접 위임한다.
기존 호출 코드(ise_loop.ISELoop)와의 API 호환성을 유지한다.
"""
from __future__ import annotations

from core.fsa_loop import FSALoop
from core.agent_runner import AgentRunner


class ISELoop:
    """FSALoop에 대한 호환 래퍼. 신규 코드는 FSALoop을 직접 사용할 것."""

    def __init__(
        self,
        fsa_loop: FSALoop,
        runner: AgentRunner,
        agent_mgr=None,
        visualizer=None,
    ):
        self.fsa = fsa_loop
        self.runner = runner
        self.agent_mgr = agent_mgr
        self._visualizer = visualizer

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
        """FSALoop.run_mission에 위임한다."""
        return self.fsa.run_mission(
            agent=agent,
            task_input=task_input,
            run_id=run_id,
            workspace=workspace,
            runtime_workspace=runtime_workspace,
            lineage_id=lineage_id,
            initial_failure_result=initial_failure_result,
        )
