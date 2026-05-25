"""
Express Router — §17 Step 18.

route_task() classifies a task description into four execution paths:
  direct  — trivial: direct execution, no interview overhead
  light   — simple: deep-skip only, minimal pipeline
  full    — complex/risky: deep interview + research + premortem + plan + verify
  dogfood — self-modifying: full + worktree isolation + triad + merge

Routing is deterministic (no LLM). Signals: token patterns, word count, explicit hints.
Design ref: docs/2026-05-21-deep-interview-research-dogfood-pipeline.md §8 §17 #11
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

RouteMode = str  # "direct" | "light" | "full" | "dogfood"

_VALID_MODES: frozenset[str] = frozenset(["direct", "light", "full", "dogfood"])

# ---------------------------------------------------------------------------
# Phase lists per route (mirrors DogfoodPhase string values)
# ---------------------------------------------------------------------------

_PHASES: dict[str, list[str]] = {
    "direct": ["implement", "verify"],
    "light": ["interview", "spec", "plan", "implement", "verify", "review"],
    "full": [
        "interview", "research_brief", "research",
        "spec", "premortem", "plan",
        "implement", "verify", "review", "finalize",
    ],
    "dogfood": [
        "interview", "research_brief", "research",
        "spec", "premortem", "plan",
        "isolate", "implement", "verify", "review", "finalize", "merge",
    ],
}

# ---------------------------------------------------------------------------
# Signal token sets
# ---------------------------------------------------------------------------

# High-confidence self-modifying / dogfood indicators
_SELF_MOD: tuple[str, ...] = (
    "core/",
    "af.spec",
    "master_blueprint",
    "dogfood",
    "self-modifying",
)

# Risk tokens — high-impact destructive or compliance operations
_RISK: tuple[str, ...] = (
    "delete",
    "migration",
    "security",
    "deploy",
    "breaking change",
    "drop table",
    "overwrite",
    "rollback",
)

# Research tokens — investigation or design required before implementation
_RESEARCH: tuple[str, ...] = (
    "research",
    "investigate",
    "analyze",
    "design",
    "evaluate",
    "trade-off",
    "tradeoff",
    "architecture",
    "feasibility",
)

# Complexity tokens — multi-scope or systemic changes
_COMPLEXITY: tuple[str, ...] = (
    "pipeline",
    "workflow",
    "across",
    "entire",
    "end-to-end",
    "framework",
    "integration",
    "interconnected",
)

# Trivial tokens — single-step informational actions
_TRIVIAL: tuple[str, ...] = (
    "status",
    "version",
    "list",
    "show",
    "print",
    "help",
    "health",
    "ping",
    "count",
    "what is",
    "where is",
)

# Word-count threshold: complexity tokens only escalate to "full" above this
_COMPLEXITY_WORD_THRESHOLD = 15

# Word-count ceiling: trivial classification only applies up to this
_TRIVIAL_WORD_CEILING = 10


# ---------------------------------------------------------------------------
# Public API — data shape
# ---------------------------------------------------------------------------


@dataclass
class RouteDecision:
    """Result of express routing for a task description."""

    mode: str  # one of _VALID_MODES
    requires_interview: bool
    requires_research: bool
    requires_premortem: bool
    requires_triad: bool
    requires_worktree: bool
    requires_merge: bool
    rationale: list[str] = field(default_factory=list)

    def phases(self) -> list[str]:
        """Ordered phase list (DogfoodPhase string values) for this route."""
        return list(_PHASES[self.mode])

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "requires_interview": self.requires_interview,
            "requires_research": self.requires_research,
            "requires_premortem": self.requires_premortem,
            "requires_triad": self.requires_triad,
            "requires_worktree": self.requires_worktree,
            "requires_merge": self.requires_merge,
            "rationale": list(self.rationale),
            "phases": self.phases(),
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _tokens_found(text: str, tokens: tuple[str, ...]) -> list[str]:
    """Return tokens present as substrings in text (case-insensitive)."""
    low = text.lower()
    return [t for t in tokens if t in low]


def _trivial_found(text: str) -> list[str]:
    """Return _TRIVIAL tokens using word-boundary matching (prevents 'helper'→'help')."""
    low = text.lower()
    return [t for t in _TRIVIAL if re.search(r"\b" + re.escape(t) + r"\b", low)]


def _classify(text: str, hints: list[str]) -> tuple[str, list[str]]:
    """Return (RouteMode, rationale_list) based on token analysis."""
    # Normalize Windows backslash paths so 'core\foo.py' matches 'core/' token
    combined = (text + " " + " ".join(hints)).replace("\\", "/")
    rationale: list[str] = []

    self_mod = _tokens_found(combined, _SELF_MOD)
    if self_mod:
        rationale.extend(f"self-mod:{t}" for t in self_mod)
        return "dogfood", rationale

    risk = _tokens_found(combined, _RISK)
    research = _tokens_found(combined, _RESEARCH)
    complexity = _tokens_found(combined, _COMPLEXITY)
    trivial = _trivial_found(combined)
    word_count = len(text.split())

    if risk:
        rationale.extend(f"risk:{t}" for t in risk)
    if research:
        rationale.extend(f"research:{t}" for t in research)
    if complexity:
        rationale.extend(f"complexity:{t}" for t in complexity)

    if risk or research or (complexity and word_count >= _COMPLEXITY_WORD_THRESHOLD):
        return "full", rationale

    # Guard: complexity token present → do not classify as trivial even if short
    if trivial and not complexity and word_count <= _TRIVIAL_WORD_CEILING:
        rationale.extend(f"trivial:{t}" for t in trivial)
        return "direct", rationale

    return "light", rationale


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def route_task(
    task: str,
    *,
    hints: list[str] | None = None,
    force_route: str | None = None,
) -> RouteDecision:
    """Map a task description to a RouteDecision.

    Args:
        task: free-form task description.
        hints: optional caller-provided signal tokens appended to task text.
        force_route: override classification to a specific route mode.
    """
    if force_route is not None:
        if force_route not in _VALID_MODES:
            raise ValueError(f"force_route must be one of {sorted(_VALID_MODES)}, got {force_route!r}")
        mode = force_route
        rationale: list[str] = [f"forced:{force_route}"]
    else:
        mode, rationale = _classify(task, hints or [])

    is_dogfood = mode == "dogfood"
    is_full_or_more = mode in ("full", "dogfood")

    return RouteDecision(
        mode=mode,
        requires_interview=mode != "direct",
        requires_research=is_full_or_more,
        requires_premortem=is_full_or_more,
        requires_triad=is_dogfood,
        requires_worktree=is_dogfood,
        requires_merge=is_dogfood,
        rationale=rationale,
    )
