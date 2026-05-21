# Deep Interview, Research Brief, Dogfood Completion Pipeline

Date: 2026-05-21
Status: Draft
Audience: Agent Factory maintainers, pipeline implementers

## 1. Summary

Agent Factory should not stop at checking whether code builds. The target product behavior is a completion-driven agent loop: clarify intent, research only what matters, produce an executable spec, plan, implement, verify, review, retry on failure, and finish only when the requested outcome is actually satisfied.

The key decision is that Deep Interview belongs before research. It is the intake gate that decides what research is needed. Research is the evidence-gathering step. Premortem belongs after research and spec compilation, because realistic risks depend on the chosen direction.

Recommended top-level flow:

```text
User Request
-> Deep Interview / Deep Skip
-> Intent & Scope Spec
-> Research Brief
-> Research
-> Spec Compile
-> Premortem
-> Plan
-> Implement
-> Verify
-> Review
-> Retry / Complete
```

For self-modifying AF work, this should be wrapped as:

```bash
af dogfood complete "..."
```

Internally:

```text
interview/deep-skip
-> research brief
-> research
-> spec
-> premortem
-> plan
-> implement
-> verify
-> review
-> retry if blocked
-> complete
```

## 2. Problem

Current AF behavior is stronger in maintenance, memory, review gates, and continuity than lightweight coding wrappers, but it still has a gap if the goal is "drive to completion like Oh My Open Agent."

The gap is not only build verification. The larger failure modes are:

- The requested outcome is vague.
- Completion criteria are not explicit.
- Research scope expands in the wrong direction.
- The implementation plan is generated before risk is understood.
- Verification checks build success but not user-level completion.
- Review failures do not reliably feed back into another implementation attempt.
- Self-modifying runs can corrupt or pollute the working tree unless isolated.

Therefore, AF needs a front-to-back completion pipeline, not just a build/test runner.

## 3. Deep Interview Decision

Deep Interview should be treated as the pipeline intake gate.

It is not a feature for asking many questions. Its job is to reduce completion failure by converting a vague user request into structured decisions.

Required outputs:

```text
intent
scope
success_criteria
constraints
approval_policy
research_questions
risk_hints
assumptions
```

Deep Interview must answer these categories:

- What is the real goal?
- What is in scope?
- What is explicitly out of scope?
- What counts as done?
- What actions require human approval?
- What should be researched before planning?
- What risks are already visible?
- Which assumptions are being made?

Example:

```text
Input:
Make AF work like Oh My Open Agent.

Structured goal:
Add a dogfood complete loop to AF.

Completion criteria:
One af dogfood complete "..." command performs interview, research, planning,
implementation, verification, review, and failure retry.

Constraints:
- Do not hardcode questions.
- Do not run heavy interview for trivial tasks.
- Preserve approval boundaries for risky work.
- Isolate self-modifying work through worktree/runtime separation.
```

## 4. Deep Skip Decision

Deep Skip is not "skip thinking." It skips asking the user, but it still produces the same structured artifact as Deep Interview.

Difference:

```text
Deep Interview = asks the user and records decisions
Deep Skip      = LLM generates reasonable defaults and records assumptions
```

Both modes should produce the same artifact shape:

```json
{
  "intent": "...",
  "scope": ["..."],
  "success_criteria": ["..."],
  "constraints": ["..."],
  "approval_policy": "...",
  "research_questions": ["..."],
  "risk_hints": ["..."],
  "assumptions": [
    {
      "id": "A1",
      "statement": "...",
      "source": "deep_skip",
      "confidence": "medium"
    }
  ]
}
```

Deep Skip must not hardcode canned questions. It should use the same LLM-backed question/spec generation path as Deep Interview, then auto-fill default answers and record them as assumptions.

## 5. Ambiguity Score Caution

Oh My Open Agent-style ambiguity scoring is useful as UX, but percent-style numbers are risky if they are only LLM estimates.

Problematic UX:

```text
Ambiguity: 7%
```

This looks like a measured value, but it may be only a subjective model estimate.

AF should prefer decision coverage:

```text
Required decisions: 5/7 complete
Blocking questions: 1 remaining
Optional questions: 3 skippable
Auto-inferred assumptions: 4
```

This is more auditable, easier to debug, and less misleading.

If a score is still shown, it should be derived from decision coverage, not presented as a precise semantic truth.

## 6. Research Placement

Research must come after Deep Interview / Deep Skip.

Reason: research is efficient only when the questions are already known. If the user says "make it like Oh My Open Agent," an unconstrained research phase may investigate installation, settings, UX, memory, MCP, routing, and product positioning. That may be wasteful if the actual goal is dogfooding completion.

Deep Interview should generate a Research Brief.

Example Research Brief:

```text
- What is the relevant OMO deep interview UX flow?
- Which AF clarification/router components already exist?
- How should AF store dogfood run state?
- What should stop a retry loop?
- How should self-modifying work be isolated from the current workspace?
- Which verification gates prove completion beyond build success?
```

Research should be constrained by the brief. Findings outside the brief should be recorded as optional or follow-up, not allowed to silently expand the implementation scope.

## 7. Premortem Placement

Premortem should happen after research and spec compilation, before planning.

Doing premortem too early produces generic risks:

```text
- Tests may fail.
- Server may go down.
- Permissions may be wrong.
```

AF needs repo-context risks:

```text
- core/*.py changes may require Master_Blueprint.md synchronization.
- CLI additions may require af.spec hiddenimports.
- dogfood execution may pollute the current workspace.
- deep-skip may accidentally bypass approval boundaries.
- retry loops may become unbounded.
- review failures may not be reinjected into the implementation loop.
```

Premortem output must become verification requirements, not just a prose warning.

Example:

```text
Risk:
CLI subcommand added but packaged build misses hidden import.

Verification:
- py_compile run_factory_cli.py core/dogfood.py
- af.spec contains core.dogfood
- python run_factory_cli.py dogfood --help
```

## 8. Triad Planning

The Planner / Fact-Based Critic / Mediator structure is useful, but should not be applied to every task.

Recommended routing:

```text
trivial task:
  direct execution, no interview

simple task:
  short confirmation or deep-skip

complex task:
  deep interview + research + plan

risky task:
  deep interview + research + premortem + review

self-modifying dogfood task:
  deep interview/deep-skip + research + premortem + triad + verify + retry
```

Triad should be mandatory for `af dogfood complete` because AF modifying AF is a self-referential high-risk workflow.

Roles:

```text
Planner:
  proposes the implementation path

Fact-Based Critic:
  challenges the plan with evidence, finds failure modes, missing tests,
  architecture violations, packaging risks, and scope leaks

Mediator:
  resolves disagreement and emits the final executable plan
```

Triad must not be three generic agents with different names. Each role needs a distinct skill profile and a different evaluation lens.

Required role specialization:

```text
Planner:
  primary job:
    propose an executable implementation plan

  required skills:
    task decomposition
    dependency ordering
    implementation sequencing
    test planning
    scope control
    cost/time estimation

  outputs:
    plan steps
    target files/modules
    required tests
    expected artifacts
    completion criteria
```

```text
Fact-Based Critic:
  primary job:
    attack the plan before implementation using concrete evidence

  required skills:
    architecture review
    repo-specific risk discovery
    failure mode analysis
    packaging impact analysis
    backward compatibility review
    security/destructive-action review
    missing-test detection

  outputs:
    blockers
    high-risk assumptions
    required design changes
    verification requirements
    no-go conditions
```

The Critic must not produce vague disagreement. Every criticism must include at least one evidence source:

```text
allowed evidence:
  file path and line reference
  failing or missing test
  git diff / git status observation
  command output
  existing design doc or ADR
  packaging config impact
  prior dogfooding failure log
  explicit user constraint

not sufficient:
  "this may be risky"
  "this seems complex"
  "consider adding tests"
  "architecture might be affected"
```

Critic finding format:

```json
{
  "severity": "high",
  "claim": "The plan can miss packaging support for a new runtime module.",
  "evidence": [
    {
      "type": "file",
      "ref": "af.spec",
      "detail": "New core modules used by CLI entry points must be present in hiddenimports."
    }
  ],
  "impact": "Packaged af.exe may fail even if source tests pass.",
  "required_change": "Add the new module to af.spec and include a packaging smoke check."
}
```

The Critic should be adversarial toward the plan, not toward the user. Its job is to prevent false completion.

```text
Mediator:
  primary job:
    resolve Planner vs Critic disagreement into a final executable plan

  required skills:
    conflict resolution
    trade-off evaluation
    decision logging
    approval-boundary enforcement
    final plan normalization
    acceptance criteria consolidation

  outputs:
    accepted decisions
    rejected alternatives
    final plan
    unresolved risks
    required approval points
```

Triad output should be a structured decision artifact, not only prose:

```json
{
  "planner_plan": "...",
  "critic_findings": [
    {
      "severity": "high",
      "issue": "...",
      "evidence": ["..."],
      "required_change": "..."
    }
  ],
  "mediator_decisions": [
    {
      "decision": "...",
      "reason": "...",
      "source": "planner|architect|user|repo_context"
    }
  ],
  "final_plan": ["..."],
  "approval_points": ["..."],
  "verification_requirements": ["..."]
}
```

For AF-on-AF work, these roles should be backed by concrete AF skills or equivalent role prompts:

```text
Planner:
  af-architecture
  writing-plans
  planning-with-files

Fact-Based Critic:
  af-code-review
  af-blueprint-sync
  af-test-runner
  systematic-debugging
  verification-before-completion

Mediator:
  af-architecture
  receiving-code-review
  finishing-a-development-branch
```

If the runtime cannot invoke named skills directly, the dogfood runner must inject equivalent skill instructions into each role prompt. The requirement is role capability separation, not a specific implementation mechanism.

## 9. Completion Driver

AF should drive to completion, not only run a build.

The dogfood loop should include:

1. Requirement refinement
2. Research scope creation
3. Research execution
4. Spec compilation
5. Repo-aware premortem
6. Plan generation
7. Implementation
8. Build/test/smoke verification
9. Code review
10. Failure analysis
11. Retry with failure feedback
12. Completion report

The loop should end only when the success criteria from the intake artifact are satisfied or a bounded blocker is reached.

## 10. Verification Beyond Build

Build success is necessary but insufficient.

Verification should include:

- Changed-file relevant tests
- `scripts/test_gap_analyzer.py`
- CLI smoke tests for new commands
- Blueprint sync checks for `core/*.py`
- `af.spec` hidden import checks for new CLI/runtime modules
- Review gate status
- Runtime state isolation checks for dogfood/self-run workflows
- User-visible completion criteria from the spec

Example:

```text
Feature:
af dogfood complete

Verification:
- python -m py_compile core/dogfood.py run_factory_cli.py
- python run_factory_cli.py dogfood --help
- python scripts/test_gap_analyzer.py --workspace .
- relevant pytest files pass
- no unexpected writes outside allowed runtime/worktree paths
- review gate produces PASS or actionable BLOCK
```

## 11. Skill-Specialized 3-Tier Review

The 3-tier review gate should also use specialized skill profiles. It should not be three generic review agents.

Triad validates the plan before implementation:

```text
Planner -> Fact-Based Critic -> Mediator
```

3-tier review validates the result after implementation:

```text
af-test-runner -> af-critic -> af-cross-review
```

Each tier must answer a different question:

```text
af-test-runner:
  What actually passed, and what evidence proves it?

af-critic:
  Where can this implementation fail, with concrete evidence?

af-cross-review:
  Can we trust the runner and critic conclusions, and what blind spots remain?
```

### 11.1 af-test-runner Skill Profile

Primary job:

```text
Produce verification evidence.
```

Required skills:

```text
af-test-runner
verification-before-completion
systematic-debugging
test-driven-development
af-architecture
af-blueprint-sync
```

Responsibilities:

```text
run relevant pytest targets
run py_compile for changed Python entry points
run scripts/test_gap_analyzer.py
run CLI smoke tests for new commands
check af.spec hidden imports for new runtime modules
check Master_Blueprint sync for core/*.py changes
check packaging/build impact where applicable
check runtime/source isolation for dogfood runs
```

Required output shape:

```json
{
  "agent": "af-test-runner",
  "evidence": [
    {
      "command": "python -m pytest tests/test_x.py -q",
      "result": "pass"
    }
  ],
  "untested_risks": ["..."],
  "verdict": "pass|warn|block|fail"
}
```

### 11.2 af-critic Skill Profile

Primary job:

```text
Find concrete implementation failures before the user trusts the result.
```

Required skills:

```text
af-code-review
af-architecture
af-blueprint-sync
systematic-debugging
verification-before-completion
receiving-code-review
using-git-worktrees
finishing-a-development-branch
context-degradation
memory-systems
```

Responsibilities:

```text
find code defects
find architecture violations
find state/race/locking bugs
find non-atomic file writes
find approval-boundary bypasses
find runtime/source pollution
find unbounded retry loops
find packaging omissions
check whether tests actually cover the changed behavior
```

Critic findings must be fact-based. A finding without evidence should be downgraded to an advisory question or rejected.

Allowed evidence:

```text
file path and line reference
failing or missing test
git diff / git status observation
command output
existing design doc or ADR
packaging config impact
prior dogfooding failure log
explicit user constraint
```

### 11.3 af-cross-review Skill Profile

Primary job:

```text
Independently verify the runner and critic conclusions.
```

Required skills:

```text
af-code-review
verification-before-completion
requesting-code-review
systematic-debugging
context-degradation
context-optimization
multi-agent-patterns
using-git-worktrees
```

Responsibilities:

```text
verify whether critic findings are factually supported
find risks the critic missed
check whether test evidence is overstated
check whether review scope matches changed files
check packaging and deployment impact
check whether the final implementation satisfies the original user request
```

Cross-review must not merely repeat `af-critic`. Its output should validate or challenge both previous tiers:

```json
{
  "agent": "af-cross-review",
  "runner_evidence_assessment": "...",
  "critic_finding_assessment": [
    {
      "finding_id": "C1",
      "judgment": "accept|reject|needs-more-evidence",
      "reason": "..."
    }
  ],
  "additional_findings": ["..."],
  "verdict": "pass|warn|block|fail"
}
```

### 11.4 Review Skill Router

The review system should route skill profiles per tier using:

```text
changed files
blast tier
risk tokens
work kind
packaging impact
prior failure patterns
dogfood/self-modifying flag
```

Example:

```text
Change:
  core/dogfood.py

af-test-runner:
  af-test-runner
  verification-before-completion
  af-blueprint-sync

af-critic:
  af-code-review
  af-architecture
  af-blueprint-sync
  systematic-debugging

af-cross-review:
  af-code-review
  context-degradation
  verification-before-completion
  using-git-worktrees
```

This means the current review router should evolve from "should Tier 3 run?" into two decisions:

```text
1. Which review tiers are required?
2. Which skill profile should each required tier receive?
```

## 12. Retry Policy

Failure should not immediately return control to the user unless it is unsafe, blocked by missing credentials, or outside the approval boundary.

Retry loop:

```text
verify/review failure
-> classify failure
-> update failure brief
-> revise plan
-> implement fix
-> rerun targeted verification
-> repeat until pass or retry budget exhausted
```

Required safeguards:

- Maximum attempts per phase
- No destructive commands without approval
- Approval boundary preserved even in Deep Skip
- Failure reason stored in state
- Next command/action stored for resume
- Human-readable completion or blocker report

## 13. State And Memory

Dogfood completion needs durable state.

Suggested state path:

```text
.af_runtime/dogfood/<run_id>/dogfood_state.json
```

Minimum fields:

```json
{
  "run_id": "...",
  "task": "...",
  "phase": "verify",
  "workspace": "...",
  "runtime_workspace": "...",
  "interview_path": "...",
  "research_brief_path": "...",
  "spec_path": "...",
  "plan_path": "...",
  "attempts": 2,
  "last_failure": "...",
  "next_action": "...",
  "approval_policy": "...",
  "completion_criteria": ["..."]
}
```

Memory should store reusable lessons:

- failure patterns
- successful verification recipes
- risky files and required sync actions
- routing decisions that reduced overhead
- dogfood run summaries

## 14. Worktree And Runtime Isolation

Self-modifying work must avoid polluting the current workspace.

AF should separate:

```text
user workspace:
  files the agent is allowed to edit

runtime workspace:
  state, agents, telemetry, temporary artifacts, logs

worktree:
  isolated git checkout for risky/self-modifying implementation
```

This separation is required because prior dogfooding runs showed that internal state and user file edits can be coupled if a single workspace variable drives both provider cwd and runtime storage.

Completion criteria for isolation:

- Intended repo files are changed.
- Runtime files are written only under the runtime workspace.
- `projects/default`, global registries, and agent/generated folders do not receive accidental writes.
- The final diff contains only intended changes.

Important clarification: isolation is not a separate product destination. It is only a way to protect the main working copy while AF edits AF.

The final result must still belong to the `agent-factory` git repository.

Recommended layout:

```text
main workspace:
  D:/hoonProJect/worktrees/agent-factory

dogfood worktree:
  D:/tmp/af-dogfood-<run_id>/agent-factory

runtime workspace:
  D:/tmp/af-runtime/<run_id>
```

The dogfood worktree must be a real `git worktree`, not an untracked copy. That keeps the result connected to the same git repository and branch model.

```text
agent-factory.git
  main workspace
  dogfood worktree
```

Expected flow:

```text
1. Create an isolated git worktree for the dogfood run.
2. Run AF-on-AF implementation in that worktree.
3. Write logs, state, temporary agents, and telemetry to runtime workspace.
4. Keep source changes inside the dogfood worktree's agent-factory checkout.
5. Verify the dogfood worktree diff.
6. Commit, create PR, merge, or apply the final patch back to the main workspace.
7. Package from the final agent-factory repository state, not from runtime files.
```

This means isolation protects the work process, while git integration preserves the product result.

Files that should be isolated:

```text
dogfood_state.json
logs
temporary prompts
temporary agents
telemetry
failed attempt snapshots
scratch artifacts
```

Files that must remain normal repository outputs when intentionally changed:

```text
core/*.py
tests/*.py
run_factory_cli.py
af.spec
Master_Blueprint.md
docs/*.md
skills/*/SKILL.md
packaging config
```

Packaging safety criteria:

- The final source diff is in the `agent-factory` git worktree.
- Runtime-only files are not required to build or package AF.
- `af.spec` includes any new hidden imports needed by new runtime modules.
- Build/package verification runs against the final repository state.
- The final report lists which changes are source changes and which artifacts are runtime-only.

Isolation should reduce packaging risk because it prevents accidental runtime files from entering the final diff.

## 15. Express Router Interaction

Deep Interview must not make AF slow for trivial work.

Routing should happen before full intake:

```text
direct:
  one-line, low-risk edits; no deep interview

light:
  simple task; short clarification or deep-skip

full:
  complex/risky work; deep interview

dogfood:
  self-modifying work; deep interview/deep-skip + research + premortem + triad
```

This prevents a 1-line change from paying the full orchestration cost.

## 16. Proposed Commands

MVP command set:

```bash
af interview "..."
af interview --deep-skip "..."

af dogfood start "..."
af dogfood run
af dogfood review
af dogfood resume
af dogfood complete "..."
```

Expected behavior:

```text
af dogfood start:
  create run state, run deep-skip/interview, create research brief

af dogfood run:
  execute research, spec, premortem, plan, implementation

af dogfood review:
  run verification and review gates

af dogfood resume:
  continue from dogfood_state.json

af dogfood complete:
  run the whole loop with bounded retries
```

## 17. Implementation Priorities

Recommended order:

1. Connect Deep Interview output to Research Brief.
2. Make Deep Skip produce the same artifact shape as Deep Interview.
3. Constrain Research to the Research Brief.
4. Compile Research + Interview into an executable Spec.
5. Add repo-context Premortem after Spec.
6. Add Plan generation from Spec + Premortem.
7. Add Dogfood state machine.
8. Add Verify/Review/Retry loop.
9. Add skill-specialized 3-tier review routing.
10. Add worktree/runtime isolation.
11. Add Express Router to avoid overhead on trivial tasks.

## 18. AF-On-AF Required Work Checklist

To make AF reliably build AF, the implementation needs all of these work items. Missing any one of the critical items turns dogfooding into a demo instead of a stable product loop.

Critical path:

- `af interview` produces a durable intake artifact.
- `--deep-skip` produces the same artifact shape as interactive interview.
- Intake output compiles into a Research Brief.
- Research is constrained by the Research Brief.
- Research output compiles into a Spec.
- Spec includes user-visible completion criteria.
- Premortem converts repo-specific risks into verification requirements.
- Planner creates an executable plan from Spec + Premortem.
- Triad review is mandatory for self-modifying AF work.
- Dogfood state machine persists phase, attempts, failures, and next action.
- Implementation executes in a git worktree connected to `agent-factory`.
- Runtime state is separated from source edits.
- Verification covers tests, CLI smoke, packaging impact, blueprint sync, and skill-specialized review gates.
- Review failures are reinjected into the next implementation attempt.
- Retry loop has a bounded attempt budget.
- Completion report separates source diff, runtime artifacts, verification evidence, and remaining risks.

Operational safety:

- No destructive git operations without explicit approval.
- Approval policy from intake is enforced during Deep Skip.
- The dogfood runner refuses to continue when the target worktree has unrelated dirty source changes unless explicitly allowed.
- Runtime cleanup does not delete source worktree files.
- Packaging is always performed from the final `agent-factory` repository state.
- Commit/PR/patch export is an explicit finalization step.

Implementation surfaces:

```text
core/interview.py:
  intake and deep-skip artifact generation

core/research_brief.py:
  convert intake decisions into bounded research questions

core/dogfood.py:
  dogfood state machine and command orchestration

core/premortem.py:
  repo-aware risk discovery and verification mapping

core/express_router.py:
  direct/light/full/dogfood routing

core/review_skill_router.py:
  tier-specific skill profile routing for af-test-runner, af-critic, and af-cross-review

run_factory_cli.py:
  af interview and af dogfood command dispatch

af.spec:
  hidden imports for new modules

tests/:
  unit, CLI smoke, state persistence, retry, isolation, and packaging-impact tests

Master_Blueprint.md:
  architecture and change-log sync for core changes
```

## 19. Non-Goals

This design does not require:

- Cloning every OMO feature.
- Showing fake precision ambiguity percentages.
- Asking many questions for every task.
- Making research broad by default.
- Treating build success as completion.
- Allowing Deep Skip to bypass approval boundaries.

## 20. Acceptance Criteria

The pipeline is acceptable when:

- A vague request can become a structured intent/scope/spec artifact.
- Deep Skip can run non-interactively while recording assumptions.
- Research is constrained by generated research questions.
- Premortem produces concrete verification requirements.
- `af dogfood complete "..."` can drive a self-modifying change through implementation, verification, review, and retry.
- Failures are reinjected into the loop instead of only reported.
- Completion reports include changed files, verification results, unresolved risks, and remaining blockers.
- Trivial tasks can bypass the heavy path through Express Router.
- The final AF-on-AF source changes live in an `agent-factory` git worktree.
- Runtime artifacts are not required for packaging.
- The final repository state can be packaged without depending on the dogfood runtime directory.
- Review tiers receive role-specific skill profiles rather than generic reviewer prompts.

## 21. Completeness Check

This document covers the major required areas for using AF to build AF:

```text
intake:
  Deep Interview, Deep Skip, decision coverage

research:
  Research Brief and constrained research

planning:
  Spec Compile, Premortem, Triad

execution:
  Dogfood state machine, implementation, retry

verification:
  tests, CLI smoke, skill-specialized review gates, packaging impact

isolation:
  git worktree for source, runtime workspace for state

finalization:
  commit/PR/patch export back into agent-factory
```

Known details still need lower-level design documents before implementation:

- Exact JSON schema for intake, research brief, spec, premortem, and dogfood state.
- Exact retry budget defaults per phase.
- Exact dirty-worktree policy and override flags.
- Exact packaging command matrix for source, PyInstaller, and any future distribution format.
- Exact review-gate command integration and failure classification taxonomy.
- Exact review skill profile schema and router rules.
- Exact cleanup policy for runtime directories.

Those details are implementation specs, not blockers for this architecture decision.

## 22. Final Position

AF should define these concepts as follows:

```text
Deep Interview:
  decision collection to reduce completion failure

Deep Skip:
  automatic decision generation with explicit assumptions

Research Brief:
  constraint document that tells research what to answer

Premortem:
  repo-aware failure prediction converted into verification requirements

Dogfood Complete:
  self-modifying completion loop that implements, verifies, reviews, retries, and reports
```

The short version:

```text
AF front-end: ask or infer the right decisions
AF middle: build an evidence-backed plan
AF back-end: keep going until completion or a real blocker
```
