# Revisit Notes After Claude Research Changes

Date: 2026-05-06
Purpose: Preserve the discussion context for re-review after Claude finishes research-related feature changes.

## Why This Exists

Claude is currently modifying and adding research-related functionality in `agent-factory`.

After that implementation is complete, this note should be used together with:

- `docs/codex/2026-05-06-agent-factory-3-phase-workflow-review.md`
- the final Claude implementation diff
- the relevant research pipeline docs and tests

The goal is to re-check whether the completed implementation still fits the 3-phase workflow discussed in chat:

1. Phase 1: product and architecture validation before implementation
2. Phase 2: domain fit, terminology, and decision-record validation
3. Phase 3: execution, TDD, review, and Codex cross-verification

## Preserved Conversation Context

The user proposed that feature development in `agent-factory` should be separated into three explicit thinking modes instead of handled by one generic tool:

- Phase 1 should force the question: "why build this, and how should it be designed?"
- Phase 2 should force the question: "does this fit this project's domain language and existing decisions?"
- Phase 3 should force the question: "how do we implement this accurately with tests, subagents, and cross-review?"

The key concern was that if planning is weak, accurate execution still builds the wrong thing. If domain fit is skipped, clean code may conflict with the existing system. The phases are valuable because each one prevents a different failure mode.

## Codex Initial Position

Codex agreed with the overall workflow philosophy, but recommended implementing it through existing `agent-factory` primitives instead of adding a separate external workflow.

Current mapping:

- Phase 1 mostly maps to existing work-item planning and approval gates.
- Phase 2 is the weakest area and should become a first-class domain/ADR gate.
- Phase 3 already has partial support through task boards, review gates, and multi-provider review.

The highest-value implementation target is Phase 2 standardization.

## Revisit Checklist

Use this checklist after Claude's research-related changes are complete.

- Did the implementation add or strengthen a domain-fit gate, or only improve research retrieval?
- Is there a canonical project context file such as `docs/PROJECT_CONTEXT.md`, `CONTEXT.md`, or an equivalent?
- Are domain terms, project-specific meanings, and naming distinctions written somewhere durable?
- Are new architectural or domain decisions recorded as ADRs or decision records?
- Does the work-item approval flow require domain review for non-trivial features?
- Does research output flow into `feature-plan.md`, `implementation-design.md`, or equivalent planning artifacts?
- Does the implementation avoid hardcoded one-domain logic unless it is isolated in config or manifests?
- Are research sufficiency checks deterministic and test-covered?
- Do review artifacts record provider, verdict, run id, and file path?
- If Codex cross-review fails, is the fallback policy explicit rather than silently treated as a substantive pass?

## Specific Risks To Re-check

- Research improvements may look like Phase 2, but retrieval alone is not a domain gate.
- A domain detector can create false positives if it uses substring matching instead of token/word-boundary matching.
- Domain manifests should be externalized, not hardcoded in core logic.
- ADR generation should not be added as noisy boilerplate; it should record actual accepted decisions.
- The approval gate should avoid blocking small safe changes with excessive documentation requirements.

## Expected Outcome Of The Re-review

After Claude's implementation is complete, Codex should produce a second review answering:

1. What changed in the research pipeline?
2. Which parts of the 3-phase workflow are now implemented?
3. Which parts are still missing?
4. Whether Phase 2 is truly enforced or only documented.
5. What should be implemented next.

