"""
core/skill_evolution_safety.py
==============================
스킬 진화 안전망 헬퍼. fsa_loop와 cross_verification이 공유.

# DEPRECATED (Stage 2 정리 대상): SelfEvolutionController._verify_sandbox()가 현재 위임 호출 중.
# 삭제 전 Controller에 인라인 후 제거할 것 — Sprint 4 이후 예정.
"""
from __future__ import annotations

import logging
import os
import shutil

from core.security_guard import quick_guard, run_isolated

logger = logging.getLogger(__name__)


def verify_evolved_skill_sandbox(skill_py: str, skill_name: str, *, timeout_sec: int = 15) -> bool:
    """
    진화된 스킬을 보안 검사 + 샌드박스 실행으로 검증.

    SelfEvolutionController._verify_sandbox (Sprint 1+)에서 위임 호출하는 로직:
      1. quick_guard(code) — 금지 import/함수 정적 검사
      2. run_isolated(skill_py) — 서브프로세스 + 타임아웃 실행

    두 단계 모두 통과해야 True. 한 단계라도 실패하면 False.
    """
    if not os.path.exists(skill_py):
        logger.warning("[evolution_safety] skill_py 미존재: %s", skill_py)
        return False
    try:
        with open(skill_py, "r", encoding="utf-8") as f:
            code = f.read()
        safe, violations = quick_guard(code)
        if not safe:
            logger.warning(
                "[evolution_safety] 보안 검사 실패 (%s): %s",
                skill_name, violations,
            )
            return False

        ok, result, stderr = run_isolated(skill_py, timeout_sec=timeout_sec)
        if not ok:
            reason = result.get("reason") or result.get("error") or stderr
            logger.warning(
                "[evolution_safety] 샌드박스 검증 실패 (%s): %s",
                skill_name, reason,
            )
            return False
        logger.info("[evolution_safety] 샌드박스 검증 통과: %s", skill_name)
        return True
    except Exception as e:
        logger.error("[evolution_safety] 검증 중 예외 (%s): %s", skill_name, e)
        return False


def rollback_evolved_skill(skill_dir: str, skill_name: str) -> bool:
    """
    진화 실패 시 .bak으로 복원. meta.yaml/meta.json 포함 (H5 v2 정합).

    각 파일별 복원 실패는 warning으로 기록 (silent fail 금지, H2' 일관).
    하나라도 복원되면 True.
    """
    restored = False
    for filename in ("skill.py", "SKILL.md", "skill.md", "meta.yaml", "meta.json"):
        bak = os.path.join(skill_dir, filename + ".bak")
        src = os.path.join(skill_dir, filename)
        if os.path.exists(bak):
            try:
                shutil.move(bak, src)  # same-partition atomic rename
                restored = True
            except Exception as e:
                logger.warning(
                    "[evolution_safety] rollback 실패 %s/%s: %s",
                    skill_dir, filename, e,
                )
    if not restored:
        logger.warning("[evolution_safety] rollback 대상 .bak 없음: %s", skill_name)
    return restored
