# Agent Factory 3-Phase Workflow Review

Date: 2026-05-06
Reviewer: Codex

## Context

This document records the chat discussion about adding a staged development workflow to the `agent-factory` development environment.

The proposed workflow separates feature development into three explicit gates:

1. Phase 1: gstack-style brainstorming and plan review
2. Phase 2: grill-with-docs-style domain interview and lightweight spec
3. Phase 3: Superpowers plus Codex-style subagent-driven development, TDD, and cross review

The core argument is that one tool should not own every thinking mode. If planning is weak, execution can accurately build the wrong thing. If domain fit is skipped, code can be clean but conflict with the existing system. Each phase should enforce a different failure-prevention gate.

## User Proposal Summary

### Phase 1: Product and Architecture Gate

Purpose:

- Answer why the feature should exist before implementation.
- Challenge the product idea before writing code.
- Separate product thinking from engineering thinking.

Suggested flow:

1. `/office-hours`: YC-style brainstorming and challenge.
2. `/plan-ceo-review`: product review and user-value clarification.
3. `/plan-eng-review`: engineering review after the product direction is fixed.

Expected outputs:

- Self-validated idea or a decision not to build.
- Product definition.
- Architecture decisions, system boundaries, data flow, state transitions, and exposed assumptions.

### Phase 2: Domain Fit Gate

Purpose:

- Validate that the Phase 1 plan fits this project's domain language and prior decisions.
- Prevent local implementation quality from causing global system inconsistency.

Suggested flow:

1. Load project context such as `CONTEXT.md`.
2. Load previous ADRs.
3. Grill the plan against existing terminology, domain boundaries, and decisions.
4. Update docs immediately when new terms or decisions are accepted.

Expected outputs:

- Domain-aligned plan.
- Updated domain glossary.
- New or updated ADRs.

### Phase 3: Execution and Review Gate

Purpose:

- Turn the validated plan into working code.
- Enforce TDD, task decomposition, two-stage review, and independent model cross-checking.

Suggested flow:

1. `writing-plans`: split plan into small verifiable tasks.
2. `using-git-worktrees`: isolate execution workspace.
3. `subagent-driven-development`: dispatch implementer subagents.
4. Run spec compliance review.
5. Run code quality review.
6. Run Codex cross review.
7. Finish branch with integration tests and PR readiness.

Expected outputs:

- Working code.
- Passing tests.
- Review records.
- Codex cross-verification records.
- Merge-ready PR.

## Codex Review

The overall direction fits `agent-factory`, but the implementation should reuse the existing pipeline instead of adding a parallel external workflow.

The repository already has a planning-first structure:

- `docs/work-items/README.md` defines a work-item flow from `feature-plan.md` through `approval-gate.md`.
- `core/approval_gate.py` manages `approval-gate.md` and blocks execution until approval is open and document hashes match.
- `core/project_pipeline.py` already models prepare before execute.
- `scripts/review_gate.py` already implements a 3-tier review gate with `af-test-runner`, `af-critic`, and `af-cross-review`.
- `core/review_runner.py` already supports multi-provider review with Claude, Codex, and Gemini.

The main gap is not Phase 3. The strongest missing piece is Phase 2: a first-class domain and decision gate.

## Recommended Mapping To Agent Factory

### Step 1: Reframe Phase 1 Into Existing Work Items

Do not create a separate gstack pipeline.

Instead, add required sections to work-item documents:

- `feature-plan.md`: pain case, why now, 10-star version, non-goals, reasons not to build.
- `implementation-design.md`: architecture boundaries, data flow, state transitions, assumptions, rollback considerations.

Execution should remain blocked by `approval-gate.md`.

### Step 2: Add A Domain Gate

This should be the priority.

Recommended standard:

- `docs/PROJECT_CONTEXT.md`: shared source for project domain language, system boundaries, and conventions.
- `docs/decisions/ADR-xxxx.md`: decision records.
- `docs/work-items/<slug>/domain-review.md`: per-feature domain fit review.

The approval gate should eventually require `domain-review.md` for non-trivial features before execution opens.

This prevents the most important failure mode: clean code that conflicts with existing project language or decisions.

### Step 3: Strengthen Existing Execution And Review

Reuse current review infrastructure instead of replacing it:

- Keep `approval_gate` for execution permission.
- Keep `project_task_board` for task decomposition.
- Keep `review_gate` for tiered review.
- Keep `review_runner` for multi-provider review.

Add stricter provenance:

- Every implementation task should include a verification command.
- Every review should record provider, verdict, file path, and run id.
- Codex review failures should not silently become equivalent to substantive PASS unless policy explicitly allows it.

## Implementation Priority

1. Define the canonical context and ADR locations.
2. Add `domain-review.md` template under `docs/work-items/_template/`.
3. Extend approval gate policy so selected work kinds require domain review.
4. Add Phase 1 product/architecture challenge fields to work-item templates.
5. Tighten review provenance for Phase 3 cross-verification.

## Conclusion

The proposed 3-phase split is correct as a workflow philosophy.

For `agent-factory`, the right implementation is not to bolt on three independent tools. The better implementation is to map the phases onto existing primitives:

- Phase 1 maps to work-item planning and approval.
- Phase 2 should become a new domain/ADR gate.
- Phase 3 maps to the existing task board, review gate, and multi-provider review system.

The most valuable next development task is Phase 2 standardization, because Phase 1 and Phase 3 already have partial implementations while domain fit is still weakly enforced.
