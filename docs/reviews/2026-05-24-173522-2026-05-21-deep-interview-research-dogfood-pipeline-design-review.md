# Design Review: 2026-05-21-deep-interview-research-dogfood-pipeline

> Source: docs/2026-05-21-deep-interview-research-dogfood-pipeline.md
> Date: 2026-05-24 17:35
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] Dogfood pipeline is described as complete, but the current implementation cannot execute the core loop
   - Section: "`af dogfood complete \"...\"` can drive a self-modifying change through implementation, verification, review, and retry."
   - Issue: The current caller path is `agent_launcher.py` -> `core.dogfood.run_all()`. In [core/dogfood.py](/D:/warkSpaces/agent-factory/core/dogfood.py:303), `_run_research_phase()` is explicitly a stub and just returns the research brief. In [core/dogfood.py](/D:/warkSpaces/agent-factory/core/dogfood.py:508), implementation runs with an empty context, and [core/dogfood.py](/D:/warkSpaces/agent-factory/core/dogfood.py:381) skips every plan step without commands. `core/planner.py` generates implementation steps without commands at [core/planner.py](/D:/warkSpaces/agent-factory/core/planner.py:161).
   - Suggestion: Before implementation proceeds, split this design into “architecture target” and “MVP executable path.” Define exactly how `IMPLEMENT` invokes the existing AF agent runner or project pipeline, how it writes source changes, and how review failures become the next implementation input.

2. [High] Proposed command surface does not match the real CLI surface
   - Section: "`af dogfood start`, `af dogfood run`, `af dogfood review`, `af dogfood resume`, `af dogfood complete`"
   - Issue: The actual dogfood parser in [agent_launcher.py](/D:/warkSpaces/agent-factory/agent_launcher.py:903) only registers `dogfood run`, `dogfood interview`, and `dogfood status`. The main `af` entrypoint in [run_factory_cli.py](/D:/warkSpaces/agent-factory/run_factory_cli.py:603) has `interview` in stage-1 dispatch, but no `dogfood` dispatch. The design names [run_factory_cli.py](/D:/warkSpaces/agent-factory/run_factory_cli.py:129) as an implementation surface, but does not resolve whether dogfood belongs in `run_factory_cli.py`, `agent_launcher.py`, or both.
   - Suggestion: Add a CLI ownership section with exact parser changes and compatibility tests. Either move dogfood dispatch into `run_factory_cli.py` or document `agent_launcher.py` as the authoritative dogfood CLI path and make `af` route to it.

3. [High] Research Brief is claimed to constrain research, but no real research integration is specified
   - Section: "Research should be constrained by the brief. Findings outside the brief should be recorded as optional or follow-up"
   - Issue: [core/research_brief.py](/D:/warkSpaces/agent-factory/core/research_brief.py:31) only extracts `research_questions` and `risk_hints`. [core/spec_compiler.py](/D:/warkSpaces/agent-factory/core/spec_compiler.py:63) only consumes evidence keys `local_refs`, `web_refs`, `llm_prior`, and `references`. The existing real researcher emits different shapes such as `local_references`, `web_references`, `llm_prior_references`, and `structured_evidence` in [core/researcher.py](/D:/warkSpaces/agent-factory/core/researcher.py). The design does not specify the adapter between these contracts.
   - Suggestion: Define the exact research execution call, evidence schema, and normalization layer. Add tests proving `ResearchBrief -> HimariResearchAgent.collect_project_evidence() -> compile_spec()` preserves on-brief and supplemental evidence.

4. [High] Worktree isolation is required but scheduled too late
   - Section: "Implementation executes in a git worktree connected to `agent-factory`."
   - Issue: The priority list puts "Add Dogfood state machine" at step 7 and "Add worktree/runtime isolation" at step 10. Current state defaults runtime storage under the same workspace in [core/dogfood.py](/D:/warkSpaces/agent-factory/core/dogfood.py:211), and execution uses `state.workspace` directly for commands in [core/dogfood.py](/D:/warkSpaces/agent-factory/core/dogfood.py:385). That means the early MVP can pollute the main repo before isolation exists.
   - Suggestion: Move worktree/runtime isolation before any self-modifying implementation phase. Make `create_run()` carry `source_workspace`, `worktree_workspace`, and `runtime_workspace`, and refuse self-modifying runs without a clean worktree unless explicitly overridden.

5. [High] LLM-generated shell commands would hit an existing security risk pattern
   - Section: "Plan generation from Spec + Premortem" and "Implementation executes..."
   - Issue: [core/dogfood.py](/D:/warkSpaces/agent-factory/core/dogfood.py:167) runs plan commands through `subprocess.run(cmd, shell=True)`. The project review checklist flags shell injection as a critical pattern. If future Planner/Triad output emits commands, this becomes an LLM-to-shell path.
   - Suggestion: Require commands to be structured argv arrays, not strings. Add an approval gate for destructive commands and block `shell=True` for dogfood execution.

6. [Medium] Deep Skip behavior is underspecified against current code
   - Section: "Deep Skip = LLM generates reasonable defaults and records assumptions"
   - Issue: Current `deep_skip` uses `auto_apply_defaults()` at [core/interview.py](/D:/warkSpaces/agent-factory/core/interview.py:165), then records those defaults as assumptions at [core/interview.py](/D:/warkSpaces/agent-factory/core/interview.py:129). The design says LLM generates defaults, but does not define whether `auto_apply_defaults()` is acceptable or must be replaced.
   - Suggestion: Specify whether Deep Skip must call an LLM answer generator distinct from default selection. If defaults are acceptable for MVP, rename the requirement to “auto-default Deep Skip” and mark LLM inference as a later phase.

7. [Medium] Architect Agent requires full Blueprint and ADR context, but no cost/context strategy is provided
   - Section: "Master_Blueprint.md: The entire Blueprint, not a summary" and "ADR history: All accepted ADRs"
   - Issue: `Master_Blueprint.md` is large, and `docs/decisions/` already contains accepted ADR files. Injecting all of that plus active diff into a Mediator role can exceed provider context or dominate token budget. The design also does not say how this works in frozen `af.exe`.
   - Suggestion: Define a bounded context builder: exact sections required by changed files, ADR index + full text only for matching ADRs, active diff truncation rules, and failure behavior when context exceeds budget.

8. [Medium] Review router names do not match current files
   - Section: "`core/review_skill_router.py`: tier-specific skill profile routing"
   - Issue: `core/review_skill_router.py` does not exist. The repo currently has `core/critic_skill_router.py`, plus `core/request_router.py`, `core/research_router.py`, and `core/retrieval_router.py`. The design proposes a new router without explaining whether it replaces or extends the existing critic router.
   - Suggestion: Add a dependency impact section mapping old-to-new router responsibilities. State whether `critic_skill_router.py` is reused, renamed, or left alone.

### Missing from Design

- Exact ownership of `af dogfood ...` between `run_factory_cli.py` and `agent_launcher.py`.
- Exact research evidence schema and adapter from `HimariResearchAgent` output to `CompiledSpec`.
- Structured command execution model that avoids `shell=True`.
- Dirty worktree policy before implementation begins, not after MVP.
- Resume semantics for dogfood state; current `run_factory_cli.py resume` is checkpoint-based, not dogfood-state-based.
- Frozen build smoke matrix for `af.exe dogfood ...`, not only source-mode CLI checks.
- Concurrency/locking behavior for two dogfood runs sharing the same runtime workspace or run_id.
- Failure classification taxonomy for retry vs block vs approval-required.

### Positive Observations

- The design correctly identifies `af.spec` hidden imports and `Master_Blueprint.md` sync as first-class verification concerns; current `af.spec` already includes `core.interview`, `core.research_brief`, `core.spec_compiler`, `core.premortem`, `core.planner`, and `core.dogfood`.
- The separation between Deep Interview and Deep Skip is useful because it gives non-interactive runs an auditable assumptions artifact instead of silently proceeding.