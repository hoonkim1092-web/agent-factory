# Design Review: 2026-05-21-deep-interview-research-dogfood-pipeline

> Source: docs/2026-05-21-deep-interview-research-dogfood-pipeline.md
> Date: 2026-05-24 17:11
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] Intake artifact contract is not implementable from current interview output
   - Section: `"Required outputs: intent scope success_criteria constraints approval_policy research_questions risk_hints assumptions"`
   - Issue: Existing `core/interview.py` only seeds `goal` and `task_input` (`core/interview.py:155`) and then forces `research_questions` / `risk_hints` to `[]` (`core/interview.py:126-127`). Its callee `core/clarification.py` only maps answers into `architecture_style`, `constraints`, `deliverables`, and `non_goals` (`core/clarification.py:159-172`). There is no current path that reliably produces `intent`, `scope`, `success_criteria`, `approval_policy`, or actual research questions.
   - Suggestion: Before implementation, define the exact intake JSON schema and update the clarification prompt/parser contract to generate these fields directly. Add tests proving `run_interview(..., deep_skip=True)` produces non-empty `success_criteria` and bounded `research_questions` for vague tasks.

2. [Critical] Empty Research Brief silently disables the design’s research constraint
   - Section: `"Research should be constrained by the brief. Findings outside the brief should be recorded as optional or follow-up"`
   - Issue: `core/research_brief.py` builds only from `research_questions` and `risk_hints` (`core/research_brief.py:31-48`). Because current interview defaults those fields to empty, `ResearchBrief.is_empty()` becomes true, and `_is_on_brief()` treats an empty brief as unconstrained (`core/research_brief.py:63-66`). `compile_spec()` then skips gap detection for empty briefs (`core/spec_compiler.py:127-133`). This directly contradicts the design’s central ordering claim.
   - Suggestion: Treat an empty brief as a blocking intake failure for `dogfood`/complex modes, or require a fallback brief generator that emits at least one research question before research can run.

3. [High] Proposed CLI surface does not match actual entry points
   - Section: `"MVP command set: af dogfood start ... af dogfood complete ..."`
   - Issue: `run_factory_cli.py` dispatches only `interview` as a Stage 1 subcommand (`run_factory_cli.py:624`, `run_factory_cli.py:672`). Dogfood currently appears in `agent_launcher.py`, not `run_factory_cli.py`, and only supports `run`, `interview`, and `status` (`agent_launcher.py:903-928`, `agent_launcher.py:964-1016`). There is no `start`, `review`, `resume`, or `complete` command in the actual caller path.
   - Suggestion: Specify the authoritative CLI owner. If frozen `af.exe` uses `run_factory_cli.py`, add a concrete dispatch plan there. Otherwise revise the design to target `agent_launcher.py` and rename commands to the current surface or explicitly add missing subcommands.

4. [High] Worktree isolation is mandatory in prose but absent from current state machine design
   - Section: `"The dogfood worktree must be a real git worktree"` and `"The dogfood runner refuses to continue when the target worktree has unrelated dirty source changes unless explicitly allowed"`
   - Issue: Current `core/dogfood.py` runs all commands in `state.workspace` (`core/dogfood.py:359-386`) and defaults runtime state to `<workspace>/.af_runtime` (`core/dogfood.py:221-225`). There is no git worktree creation, no dirty worktree check, no source/runtime path allowlist, and no final patch/merge path. The document defers `"Exact dirty-worktree policy and override flags"` as non-blocking (`docs/2026-05-21-deep-interview-research-dogfood-pipeline.md:1165-1175`), but that policy is core safety for AF-on-AF.
   - Suggestion: Make worktree lifecycle a blocking subdesign: create/list/remove worktree steps, branch naming, dirty-tree refusal rules, runtime path allowlist, finalization options, and Windows path handling.

5. [High] Review skill router conflicts with current review gate architecture
   - Section: `"current review router should evolve from 'should Tier 3 run?' into two decisions"`
   - Issue: Current review selection is static and blast-tier based: `_TIER_AGENTS` maps tier to fixed agents (`scripts/review_gate.py:85-90`), `_required_tiers_for()` only uses `blast_tier` (`scripts/review_gate.py:214-225`), and `scripts/check_pending_review.py` only prints agent instructions by tier (`scripts/check_pending_review.py:47-60`). The proposed `core/review_skill_router.py` does not exist, and the design does not describe how skill profiles are stored in `.af_review_queue`, consumed by hooks, or validated by `review_gate.py`.
   - Suggestion: Add an integration contract for review queue state: required tiers, agent names, skill profile payload, compatibility with existing `blast_tier`, and how `review_gate.py` validates profile-specific review completion.

6. [High] LLM-generated command execution lacks a safe command model
   - Section: `"No destructive commands without approval"` and `"Implementation executes in a git worktree"`
   - Issue: Current dogfood command runner executes string commands with `shell=True` (`core/dogfood.py:168-173`). The design allows executable plan commands but does not require list-form subprocess calls, command classification, approval interception, or shell injection prevention. This is especially risky because the pipeline plans implementation and retry actions from model-produced artifacts.
   - Suggestion: Define plan commands as structured arrays, not shell strings. Add an approval/classification layer before execution, forbid `shell=True` for generated commands, and require explicit handling for git, deletion, move, and cleanup operations.

7. [Medium] Architect Agent requirement is underspecified against missing modules and ADR state
   - Section: `"core/architect_agent.py (planned): Architect Agent context builder — loads Master_Blueprint.md + accepted ADRs + active git diff"`
   - Issue: `core/architect_agent.py`, `core/express_router.py`, and `core/review_skill_router.py` do not exist. `docs/decisions/` currently contains accepted ADR files, but the design does not specify ADR discovery/filtering, encoding handling, maximum context size, or what happens when Blueprint/ADR context exceeds the model window.
   - Suggestion: Add a concrete context builder contract: ADR file selection rules, Blueprint sections required, truncation/refusal behavior, output validation for `blueprint_section` references, and tests with real `docs/decisions/*.md`.

8. [Medium] Durable state lacks concurrency and atomicity requirements
   - Section: `"Dogfood completion needs durable state"`
   - Issue: `save_state()` writes through a fixed `.tmp` path and replaces it (`core/dogfood.py:191-197`), while other artifact writes use direct `Path.write_text()` (`core/dogfood.py:580-582`). The design does not address concurrent `resume`/`run` access, partial artifact writes, or file locking, despite the checklist requiring concurrent access and rollback/recovery paths.
   - Suggestion: Require `core/file_lock.py` or equivalent around dogfood run state, unique temp files for atomic writes, and recovery behavior for corrupt/missing phase artifacts.

### Missing from Design

- Exact intake schema and validation rules for `intent`, `scope`, `success_criteria`, `approval_policy`, and research questions.
- Concrete CLI ownership between `run_factory_cli.py` and `agent_launcher.py`.
- Worktree lifecycle and dirty-tree refusal policy before any AF-on-AF command runs.
- Safe command execution model for generated plan commands.
- Review queue schema changes needed for skill-specialized tiers.
- Failure behavior when research providers, CLI providers, or review agents are unavailable.
- Frozen build smoke matrix for new subcommands and missing hiddenimports for planned modules like `core.architect_agent`, `core.review_skill_router`, and `core.express_router`.

### Positive Observations

- The document correctly identifies that build success is insufficient and maps premortem risks into verification requirements.
- It explicitly separates runtime artifacts from source changes, which matches prior AF dogfooding failure patterns around workspace pollution.