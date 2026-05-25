"""
Skill-specialized 3-tier review routing — §17 Step 17.

route_review_skills() maps a ReviewContext to a ReviewSkillPlan: which review
tiers are required and which skill profiles each tier receives.  Selection is
deterministic (no LLM), driven by changed-file paths, blast tier, work kind,
and risk tokens.

Design ref: docs/2026-05-21-deep-interview-research-dogfood-pipeline.md §11.4
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

WorkKind = Literal["dogfood", "feature", "bug-fix", "docs", "infra"]

# ---------------------------------------------------------------------------
# Public API — data shapes
# ---------------------------------------------------------------------------


@dataclass
class ReviewContext:
    """Inputs for skill routing."""

    changed_files: list[str]
    blast_tier: int  # 1, 2, or 3
    work_kind: WorkKind = "feature"
    risk_tokens: list[str] = field(default_factory=list)
    has_packaging_impact: bool = False
    is_self_modifying: bool = False


@dataclass
class TierSkillProfile:
    """Skill profile assigned to one review tier."""

    tier: str
    skills: list[str]

    def to_dict(self) -> dict:
        return {"tier": self.tier, "skills": list(self.skills)}


@dataclass
class ReviewSkillPlan:
    """Full routing decision: which tiers run and with which skills."""

    required_tiers: list[str]
    profiles: dict[str, TierSkillProfile]

    def to_dict(self) -> dict:
        return {
            "required_tiers": list(self.required_tiers),
            "profiles": {k: v.to_dict() for k, v in self.profiles.items()},
        }


# ---------------------------------------------------------------------------
# Base skill sets per tier (§11.1-11.3)
# ---------------------------------------------------------------------------

_BASE_TEST_RUNNER: list[str] = [
    "af-test-runner",
    "verification-before-completion",
]

_BASE_CRITIC: list[str] = [
    "af-code-review",
    "af-architecture",
    "systematic-debugging",
]

_BASE_CROSS: list[str] = [
    "af-code-review",
    "verification-before-completion",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _has_blueprint_impact(files: list[str]) -> bool:
    """True when any changed file triggers blueprint-sync obligations."""
    for f in files:
        n = f.replace("\\", "/")
        if (
            n.startswith("core/")
            or n.endswith("Master_Blueprint.md")
            or n == "af.spec"
        ):
            return True
    return False


def _is_worktree_work(ctx: ReviewContext) -> bool:
    """True when the change is worktree/isolation or dogfood-related."""
    if ctx.work_kind == "dogfood" or ctx.is_self_modifying:
        return True
    if "worktree" in ctx.risk_tokens:
        return True
    return any("dogfood" in f or "worktree" in f for f in ctx.changed_files)


def _dedup(lst: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


def route_review_skills(ctx: ReviewContext) -> ReviewSkillPlan:
    """Map ReviewContext → ReviewSkillPlan.

    Tier 1 → only af-test-runner with base skills.
    Tier 2/3 → all three tiers; each tier's skill set is shaped by blueprint
    impact, worktree/self-modifying risk, packaging impact, and blast level.
    """
    if ctx.blast_tier == 1:
        return ReviewSkillPlan(
            required_tiers=["af-test-runner"],
            profiles={
                "af-test-runner": TierSkillProfile(
                    tier="af-test-runner",
                    skills=list(_BASE_TEST_RUNNER),
                )
            },
        )

    # Tier 2 or 3 — all three tiers
    blueprint_impact = _has_blueprint_impact(ctx.changed_files)
    worktree_work = _is_worktree_work(ctx)
    tier3 = ctx.blast_tier == 3

    # af-test-runner skill set
    tr_skills: list[str] = list(_BASE_TEST_RUNNER)
    if blueprint_impact:
        tr_skills.append("af-blueprint-sync")
    if ctx.has_packaging_impact:
        tr_skills.append("af-architecture")

    # af-critic skill set
    critic_skills: list[str] = list(_BASE_CRITIC)
    if blueprint_impact:
        critic_skills.append("af-blueprint-sync")
    if worktree_work:
        critic_skills.extend(["using-git-worktrees", "context-degradation"])
    if tier3:
        critic_skills.append("verification-before-completion")

    # af-cross-review skill set
    cross_skills: list[str] = list(_BASE_CROSS)
    if worktree_work:
        cross_skills.extend(["context-degradation", "using-git-worktrees"])
    if tier3:
        cross_skills.extend(["context-optimization", "multi-agent-patterns"])

    profiles = {
        "af-test-runner": TierSkillProfile("af-test-runner", _dedup(tr_skills)),
        "af-critic": TierSkillProfile("af-critic", _dedup(critic_skills)),
        "af-cross-review": TierSkillProfile("af-cross-review", _dedup(cross_skills)),
    }
    return ReviewSkillPlan(
        required_tiers=["af-test-runner", "af-critic", "af-cross-review"],
        profiles=profiles,
    )
