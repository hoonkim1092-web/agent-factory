# Review BLOCK Learning And Evolution Design

## Purpose

This document captures the design position for connecting repeated 3-Tier review BLOCK patterns to AF skill or instruction evolution.

The goal is not to automatically rewrite skills or common instructions whenever a review fails. The goal is to learn from repeated BLOCK findings, identify when the process itself is causing repeated mistakes, and produce controlled evolution proposals.

### v1 Scope

The first implementation detects only the known pattern families enumerated in Step 2 (hiddenimport, production caller wiring, Blueprint, absolute path, fixture-only, pre-commit, provider instruction). Findings that do not match a known family are recorded as `unknown:<hash>` but are **not** aggregated toward the recurrence threshold: free-text finding titles vary by provider and edit site, so two genuinely related novel findings would receive different keys and never reach the same `pattern_key`. Detecting novel recurring patterns (clustering `unknown` findings by similarity) is therefore explicitly out of scope for v1 and deferred until enough captured data exists to justify it. The Purpose above ("learn from repeated mistakes") is the long-term target; v1 only re-detects the already-known families.

## Position

AF should learn from repeated 3-Tier BLOCK patterns.

AF should not directly auto-publish skill or instruction changes from a single BLOCK finding.

Review BLOCK findings mix two different causes:

```text
A. One-off implementation mistake
B. Repeated process/tool/skill/instruction weakness
```

Only B should become an evolution candidate.

If AF treats A as a skill or instruction defect, the system will overfit to isolated mistakes and may degrade broader behavior. If AF ignores B, it will repeat the same preventable failures.

Therefore, the correct architecture is:

```text
3-Tier BLOCK
  -> structured finding capture
  -> recurring pattern detection
  -> cause attribution candidate
  -> evolution proposal
  -> human approval
  -> skill/checklist/instruction change
  -> verification
  -> post-change recurrence tracking
```

## What Counts As A Review BLOCK Pattern

Examples of BLOCK patterns that may recur:

```text
production caller wiring missing
Blueprint update missing
af.spec hiddenimport missing
hardcoded absolute path
tests cover fixtures but not production path
review evidence too broad or not finding-specific
provider-specific instruction drift
pre-commit gate bypass misuse
```

These should be stored as normalized pattern keys, not only raw Markdown text.

Example normalized record:

```json
{
  "pattern_key": "production_caller_wiring_missing",
  "severity": "high",
  "source_agent": "af-cross-review",
  "finding_title": "New parameter not wired to production caller",
  "changed_files": ["core/project_pipeline.py"],
  "evidence_files": ["core/project_pipeline.py", "agent_launcher.py"],
  "work_kind": "code",
  "timestamp": "2026-06-20T00:00:00+09:00"
}
```

## What Should Not Trigger Evolution

The following should not directly trigger skill/instruction evolution:

```text
one isolated BLOCK
user changed requirements mid-task
external provider outage
auth/session failure
network/rate-limit failure
test failure caused by project code under edit
review finding with weak or unverifiable evidence
BLOCK caused by explicitly accepted tradeoff
```

These may still be recorded, but they should not become evolution proposals without recurrence and attribution evidence.

## Threshold Policy

Recommended initial thresholds:

```text
1 occurrence
  -> fix current task only
  -> record finding

2 occurrences
  -> mark as recurring candidate
  -> no automatic evolution

3 occurrences with same or related cause candidate
  -> create evolution proposal

human approval
  -> apply skill/checklist/instruction update

post-change monitoring
  -> track whether recurrence decreases
```

The threshold should be configurable later, but hardcoding this conservative default is acceptable for the first implementation.

## Cause Attribution

The hardest part is not detecting repetition. The hardest part is deciding what should evolve.

Example:

```text
BLOCK: af.spec hiddenimport missing
```

Possible causes:

```text
coder ignored existing rule
planner did not include frozen-build checklist
af-critic failed to detect missing hiddenimport
af-test-runner did not run build-path verification
common instruction exists but is buried and ineffective
```

AF should not assume the first cause is correct.

Cause attribution should produce candidates:

```json
{
  "pattern_key": "hiddenimport_missing",
  "attribution_candidates": [
    {
      "target_type": "skill",
      "target_id": "af-test-runner",
      "reason": "verification did not include frozen import path"
    },
    {
      "target_type": "skill",
      "target_id": "af-critic",
      "reason": "review did not flag known core/*.py hiddenimport rule"
    },
    {
      "target_type": "instruction",
      "target_id": "INSTRUCTIONS.md",
      "reason": "rule may be too low-salience for repeated enforcement"
    }
  ]
}
```

The proposal should include evidence, not just a conclusion.

## Evolution Targets

Possible targets:

```text
skill
  -> SKILL.md checklist, prompts, examples, validation steps

review checklist
  -> af-critic / af-cross-review / af-test-runner behavior

agent instruction
  -> role-specific guidance

common provider instruction
  -> INSTRUCTIONS.md, propagated to CLAUDE.md / GEMINI.md / AGENTS.md

gate logic
  -> pre-commit, review-gate, design-review gate
```

Risk by target:

```text
low risk
  -> skill-local checklist update
  -> review prompt clarification

medium risk
  -> test-runner verification command
  -> agent role instruction

high risk
  -> INSTRUCTIONS.md common policy
  -> review-gate blocking logic
  -> pre-commit behavior
```

High-risk targets must require explicit human approval.

## Proposal-First Rule

Repeated review BLOCKs should produce an evolution proposal first.

They should not directly call `SelfEvolutionController.submit()` and publish changes.

Proposed output:

```text
docs/evolution-proposals/EVP-YYYYMMDD-HHMMSS-<pattern>.md
```

Example proposal sections:

```markdown
# Evolution Proposal: hiddenimport_missing

## Pattern

Repeated BLOCK: new core/*.py file missing af.spec hiddenimport.

## Evidence

- Review 1: ...
- Review 2: ...
- Review 3: ...

## Suspected Cause

af-test-runner does not explicitly verify frozen import path for new core files.

## Proposed Change

Update af-test-runner SKILL.md to include hiddenimport verification when new core/*.py files are added.

## Risk

Low. Skill-local checklist update only.

## Verification

Run targeted tests and simulate a diff with new core/*.py file.
```

## Relationship To Existing SelfEvolutionController

Existing `SelfEvolutionController` is suitable for candidate-based skill evolution:

```text
candidate copy
  -> LLM modification
  -> sandbox
  -> quality gate
  -> publish/discard
  -> SkillEvolutionBus cache invalidation
```

However, review BLOCK learning should not feed directly into it at first.

Recommended layering:

```text
ReviewBlockPatternStore
  -> RecurrenceDetector
  -> CauseAttribution
  -> EvolutionProposal
  -> human approval
  -> SelfEvolutionController only for approved skill-local changes
```

For common instructions and gates, use a separate controlled path:

```text
EvolutionProposal
  -> human approval
  -> manual or guarded patch to INSTRUCTIONS.md / gate code
  -> provider instruction sync
  -> tests
```

## Data Store

Initial storage can be JSONL.

Proposed file:

```text
data/review-block-patterns.jsonl
```

Record shape:

```json
{
  "pattern_key": "production_caller_wiring_missing",
  "severity": "high",
  "review_agent": "af-cross-review",
  "source_report": "docs/reviews/2026-06-20-...md",
  "changed_files": ["core/foo.py"],
  "finding_title": "New parameter not wired to production caller",
  "finding_excerpt": "...",
  "accepted": true,
  "task_context": "feature implementation",
  "created_at": "2026-06-20T00:00:00+09:00"
}
```

Later this can move into the existing knowledge graph or run event store, but JSONL is enough for the first pass.

## Minimal Implementation Plan

### Step 1: Capture

Parse 3-Tier review outputs and store accepted BLOCK findings as structured records.

Do not alter review verdict behavior.

### Step 2: Normalize

Map findings to stable `pattern_key` values.

Use conservative matching first:

```text
hiddenimport
production caller
Blueprint
absolute path
fixture only
pre-commit
provider instruction
```

Unknown findings can use:

```text
unknown:<hash>
```

### Step 3: Detect Recurrence

Aggregate over recent history.

Initial criteria:

```text
same pattern_key >= 3
within recent N accepted BLOCK findings
not marked as accepted tradeoff
```

### Step 4: Generate Proposal

Create a Markdown proposal with:

```text
pattern
evidence
attribution candidates
recommended target
risk level
proposed change
verification plan
```

### Step 5: Human Approval

When a proposal is generated it must be surfaced, or the approval step becomes unreachable and the proposal is a silent dead-letter. At minimum:

```text
- record the proposal path (docs/evolution-proposals/EVP-*.md) in NEXT_STEPS.md
- expose a read-only listing command (e.g. `af evolution list`) that prints open EVP proposals
```

A proposal written to disk but never surfaced breaks the control loop this design depends on. Notification is part of the Human Approval contract, not an optional add-on.

Do not automatically modify:

```text
INSTRUCTIONS.md
CLAUDE.md
AGENTS.md
GEMINI.md
review-gate code
pre-commit hook
```

Skill-local proposals may later become semi-automatic, but the first version should still require approval.

### Step 6: Apply And Verify

After approval:

```text
skill-local change
  -> SelfEvolutionController or direct patch
  -> SkillQualityGate
  -> SkillEvolutionBus

instruction/gate change
  -> patch
  -> sync_provider_instructions.py if INSTRUCTIONS.md changed
  -> targeted tests
  -> pre-commit behavior check
```

### Step 7: Measure Effect

Track whether the same pattern continues after the change.

If recurrence does not decrease, mark the evolution as ineffective and avoid repeating the same proposal.

## Guardrails

Required guardrails:

```text
never evolve from a single BLOCK
never auto-edit common instructions
never auto-edit review gate/pre-commit blocking logic
never attribute cause without evidence
never treat provider outage or auth failure as review-learning signal
never delete or weaken rules just to reduce BLOCK count
```

Success means reducing repeated valid BLOCK findings, not reducing review strictness.

## Summary

AF should connect repeated 3-Tier BLOCK patterns to learning.

AF should not directly connect every BLOCK to automatic self-evolution.

The correct first architecture is:

```text
BLOCK finding
  -> structured record
  -> recurrence detection
  -> cause attribution
  -> proposal
  -> approval
  -> controlled evolution
  -> recurrence measurement
```

This avoids automatic overreaction while giving AF a path to stop repeating the same process mistakes.
