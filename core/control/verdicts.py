"""Stage 0 Question Router — verdict/route/cause enum 단일 원천."""
from enum import Enum


class QuestionRoute(Enum):
    PASS = "pass"
    LLM_DELEGATE = "llm_delegate"
    HITL = "hitl"
    BLOCK = "block"
    RESEARCH_SYNTHESIZE = "research_synthesize"  # 스킵 → ResearchRouter 합성 (INV-Q1)


class DomainVerdict(Enum):
    PASS = "pass"
    NEEDS_ADR = "needs_adr"
    BLOCK = "block"


class BlockCause(Enum):
    MISSING_REQUIRED_INPUT = "missing_required_input"
    DESIGN_CONFLICT = "design_conflict"
    HIGH_RISK = "high_risk"
    POLICY_VIOLATION = "policy_violation"
    SAFETY = "safety"
