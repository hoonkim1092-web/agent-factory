"""
core/evolution_types.py
========================
Stage 1 진화 파이프라인 공유 타입 모듈.

Sprint 1에서 SelfEvolutionController(Sprint 2) 없이도
hook 모듈과 RunEventType 분기가 EvolutionDecision을 참조할 수 있도록 분리.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EvolutionDecision(Enum):
    PUBLISHED = "published"    # candidate → live atomic publish 성공
    REJECTED = "rejected"      # sandbox/quality gate 실패 → candidate 폐기
    DEFERRED = "deferred"      # 게이트 신뢰 불가 → 보수적 폐기 (FSALoop None 분기)
    ERROR = "error"            # 예외 발생 → candidate 폐기 + 로그


@dataclass
class EvolutionResult:
    skill_id: str
    decision: EvolutionDecision
    candidate_dir: Optional[str]   # ERROR/DEFERRED 시 None 가능
    new_version: Optional[str]
    rejection_reason: Optional[str]
    cost_tokens: int = field(default=0)   # F8: RunBudget 가산용
