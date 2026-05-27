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

1. [Critical] Proposed `af dogfood` commands are not wired to the packaged CLI entrypoint
   - Section: "`af dogfood start` ... `af dogfood complete`" and "`run_factory_cli.py: af interview and af dogfood command dispatch`"
   - Issue: Frozen AF builds use `run_factory_cli.py` as the PyInstaller entrypoint: [af.spec](/D:/warkSpaces/agent-factory/af.spec:23). But `run_factory_cli.py` only dispatches `interview`, not `dogfood`: [run_factory_cli.py](/D:/warkSpaces/agent-factory/run_factory_cli.py:601). Existing dogfood parsing is in `agent_launcher.py` and only supports `interview`, `run`, and `status`, not `start/review/resume/complete`: [agent_launcher.py](/D:/warkSpaces/agent-factory/agent_launcher.py:903).
   - Suggestion: Pick one canonical production entrypoint. If the command is truly `af dogfood ...`, add Stage 1 dispatch and usage in `run_factory_cli.py`, then define exactly which subcommands exist for MVP. Otherwise rewrite the design to say this is `python agent_launcher.py dogfood ...` and mark frozen `af.exe` out of scope.

2. [High] Research Brief is not connected to the real research pipeline
   - Section: "`Research should be constrained by the brief.`" and "`core/research_brief.py: convert intake decisions into bounded research questions`"
   - Issue: The real research path is `ProjectPipeline.prepare_brief()` using `HimariResearchAgent.collect_project_evidence()` / `research_project_brief()` and `ResearchRouter`: [core/project_pipeline.py](/D:/warkSpaces/agent-factory/core/project_pipeline.py:726), [core/researcher.py](/D:/warkSpaces/agent-factory/core/researcher.py:941). Current dogfood research phase is explicitly a stub returning the brief unchanged: [core/dogfood.py](/D:/warkSpaces/agent-factory/core/dogfood.py:303). The design does not specify how `ResearchBrief.questions` becomes a `ResearchPlan`, evidence bundle, coverage gate input, or fallback when NotebookLM/Tavily/LLM research fails.
   - Suggestion: Add a concrete adapter contract: `ResearchBrief -> ResearchPlan/evidence_bundle -> spec_compiler`, including degraded/offline behavior and whether existing `ProjectPipeline` research is reused or bypassed.

3. [High] Isolation is listed after implementation/retry even though it is a critical safety precondition
   - Section: "`Implementation executes in a git worktree connected to agent-factory.`" vs "`Implementation Priorities ... 8. Add Verify/Review/Retry loop ... 10. Add worktree/runtime isolation.`"
   - Issue: The order is unsafe for AF-on-AF work. Existing `core.dogfood.create_run()` defaults runtime state to `<workspace>/.af_runtime`: [core/dogfood.py](/D:/warkSpaces/agent-factory/core/dogfood.py:211), and implementation/verification commands run in `state.workspace`: [core/dogfood.py](/D:/warkSpaces/agent-factory/core/dogfood.py:385). If the dogfood runner is implemented before real worktree/runtime separation, it can modify the current checkout and runtime files before the isolation feature exists.
   - Suggestion: Move worktree/runtime isolation before implementation execution. Define `git worktree add`, dirty-tree refusal, allowed runtime paths, cleanup rules, and patch/merge-back behavior as phase 0 requirements.

4. [High] Execution safety is underspecified for plan-generated commands
   - Section: "`No destructive git operations without explicit approval.`" and "`Planner creates an executable plan from Spec + Premortem.`"
   - Issue: The design requires executable plans but does not define command schema, shell policy, allow/deny rules, or approval enforcement at the executor boundary. This matters because current `core.dogfood._default_command_runner()` runs command strings with `shell=True`: [core/dogfood.py](/D:/warkSpaces/agent-factory/core/dogfood.py:167). A planner-produced string can become shell injection or destructive execution if approval checks are only prose-level.
   - Suggestion: Require structured commands as argv lists, `shell=False`, command classification before execution, and a hard approval gate for destructive patterns. Store approval decisions in `dogfood_state.json`.

5. [Medium] Proposed module surface does not match current repository names
   - Section: "`core/express_router.py`", "`core/review_skill_router.py`", "`core/architect_agent.py (planned)`"
   - Issue: These files do not currently exist. The closest existing review router is `core/critic_skill_router.py`, already packaged in `af.spec`: [af.spec](/D:/warkSpaces/agent-factory/af.spec:187). The design says "current review router should evolve" but does not identify whether to extend `critic_skill_router.py`, `review_runner.py`, `scripts/review_gate.py`, or add a new router.
   - Suggestion: Add a dependency-impact section mapping each proposed module to existing callers and packaging updates. If adding new modules, explicitly require `af.spec` hiddenimports and Blueprint sync.

6. [Medium] Frozen/Windows verification is acknowledged but not specified enough
   - Section: "`Verification covers tests, CLI smoke, packaging impact, blueprint sync...`"
   - Issue: The design lists checks but not a Windows-safe command matrix. Existing premortem-style checks already use Unix commands such as `grep`: [core/premortem.py](/D:/warkSpaces/agent-factory/core/premortem.py:92). That is fragile for the project’s Windows-first paths and `dist/af/af.exe` compatibility.
   - Suggestion: Define verification commands as Python scripts or cross-platform subprocess argv. Include source-mode and frozen-mode smoke tests separately.

### Missing from Design

- Exact integration point between `agent_launcher.py` and `run_factory_cli.py`.
- Research external-service failure behavior: unavailable API, partial evidence, stale cached evidence, retry budget.
- Dirty worktree policy details: untracked files, unrelated modified files, branch naming, merge-back strategy.
- Command execution schema and approval-gate enforcement.
- Resume semantics for interrupted runs across process restarts.
- `af.spec` policy for every new `core/*.py` module and any non-Python data files.
- Migration plan from current `critic_skill_router.py` / review gate scripts to the proposed skill-specialized review router.

### Positive Observations

- The document correctly places Deep Interview before research and premortem after spec compilation; that matches the need to avoid broad, unfocused research.
- The acceptance criteria explicitly distinguish source diff, runtime artifacts, verification evidence, and unresolved risks, which is the right reporting shape for AF-on-AF work.