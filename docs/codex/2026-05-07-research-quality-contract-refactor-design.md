# Research Quality Contract Refactor Design

Date: 2026-05-07
Author: Codex
Status: Proposed

## Context

This document records the proposed refactor for the Agent Factory research quality gate.

The immediate discussion started from `_detect_domain()` and `poker.yaml`:

- `_detect_domain()` runs before the LLM call.
- Its current purpose is to decide which YAML checklist to load.
- If a request is detected as poker, `poker.yaml` is loaded and used by `RecoverySearchLoop` as the gap-check basis.
- If no checklist is loaded, current behavior effectively treats the result as having no gaps.

The critical bug is not only that Korean compound words such as `포커게임` may fail detection. The deeper bug is that domain detection failure can silently remove the research quality gate.

```python
if not checklist:
    return []
```

This treats "no evaluation criteria exist" as "no gaps exist". That is an invalid interpretation.

## Core Decision

Research quality criteria should not be selected by domain YAML detection alone.

They should be generated from a structured `WorkSpec`, then assembled into a `QualityContract`.

Target model:

```text
user_request
  -> WorkSpecExtractor
  -> QualityContractBuilder
       - base pack
       - artifact pack
       - capability packs
       - domain overlays
       - LLM request-specific additions
  -> ChecklistMerger
  -> RecoverySearchLoop
  -> research_evidence.json
```

The one-line rule:

```text
No checklist is not a pass. It is a quality-contract build failure.
```

## Current Failure Mode

Current behavior is approximately:

```text
user_request
  -> _detect_domain()
  -> load matching domain checklist YAML
  -> RecoverySearchLoop gap check
```

That creates these failure cases:

| Request | Detected Domain | Checklist | Result |
| --- | --- | --- | --- |
| `포커 만들기` | `poker` | `poker.yaml` | quality gate runs |
| `포커게임 만들기` | possibly empty | none | quality gate may be skipped |
| `체스 게임 만들기` | empty | none | quality gate skipped |
| `쇼핑몰 만들기` | empty | none | quality gate skipped |
| `블로그 시스템 만들기` | empty | none | quality gate skipped |

This conflicts with Agent Factory's goal: it must handle unknown project requests, not only pre-registered domains.

## Design Principle

The system should not ask only:

```text
Which domain YAML applies?
```

It should first ask:

```text
What kind of work is this, what capabilities are requested, and what risks must be covered?
```

For example, the request:

```text
8인 네트워크 포커게임 만들어줘
```

contains multiple independent axes:

| Axis | Example Value |
| --- | --- |
| Artifact type | `game` |
| Capabilities | `multiplayer`, `realtime`, `rules_engine` |
| Domain | `poker` |
| Risk areas | `anti_cheat`, `randomness`, `authoritative_server` |
| Constraints | `8_players` |

The current domain-only design collapses this into:

```text
domain == poker ? poker.yaml : no checklist
```

That is too weak.

## Proposed Components

### 1. WorkSpecExtractor

`WorkSpecExtractor` converts the user request into a structured work description.

Example output:

```json
{
  "artifact_type": "game",
  "domain": "poker",
  "capabilities": ["multiplayer", "realtime", "rules_engine"],
  "risk_areas": ["anti_cheat", "randomness", "authoritative_server"],
  "constraints": ["8_players"],
  "domain_hints": ["poker"]
}
```

This can use an LLM because it is semantic classification. Regex can still contribute hints, but it must not be the final source of truth.

Rename the current function:

```python
_detect_domain()
```

to:

```python
_detect_domain_hints()
```

Its role changes from "decide the checklist" to "suggest possible overlays".

Detection failure should produce:

```python
domain_hints = []
```

It must not disable the quality gate.

### 2. QualityContractBuilder

`QualityContractBuilder` assembles criteria from multiple sources.

Recommended pack layers:

```text
base
artifact:<artifact_type>
capability:<capability>
domain:<domain>
llm_additions
```

Example for poker multiplayer game:

```text
base:
  - requirements coverage
  - architecture rationale
  - implementation feasibility
  - test strategy
  - major failure modes

artifact:game:
  - game loop
  - state model
  - action validation
  - win/loss condition

capability:multiplayer:
  - synchronization
  - disconnect/reconnect
  - server/client responsibility
  - concurrency handling

capability:realtime:
  - latency handling
  - event ordering
  - state reconciliation

domain:poker:
  - hand ranking
  - betting rounds
  - blinds
  - side pots
  - shuffle fairness
  - anti-cheat
```

This means that even if poker detection fails, `game`, `multiplayer`, and `realtime` criteria still run.

### 3. Domain Overlays

Existing YAML such as `poker.yaml` should not be discarded.

It should be reclassified as a domain overlay:

```text
checklists/poker.yaml
  -> research/packs/domains/poker.yaml
```

Domain overlays are valuable for stable, high-risk, domain-specific requirements:

- poker hand ranking
- betting round order
- side pots
- card randomness
- anti-cheat
- server-authoritative game state

The priority changes:

```text
Before: YAML selected by domain detection is the checklist.
After: YAML overlay strengthens a contract that already exists.
```

### 4. LLM Request-Specific Additions

The LLM should not generate the whole checklist from scratch.

Reason:

- output may vary across runs
- common quality items can be missed
- regression tests become weaker
- generated criteria can become shallow

Instead:

```text
deterministic packs provide the baseline
LLM additions cover request-specific requirements
```

Example:

If the user says:

```text
토너먼트 모드도 포함해줘
```

the LLM may add:

```json
{
  "id": "tournament_structure",
  "title": "Tournament structure",
  "source": "llm_addition",
  "required": false,
  "priority": "medium",
  "reason": "The user requested tournament-style poker support.",
  "acceptance": "Evidence describes tournament progression, elimination, table balancing, or prize/ranking behavior."
}
```

LLM additions may add criteria, but must not remove deterministic required criteria.

### 5. ChecklistMerger

A simple union is not enough because semantically equivalent items can appear under different names.

Example:

```text
LLM: server-side state validation
Overlay: authoritative server architecture
```

These should merge into one canonical item.

Merge rules:

1. Every item has a canonical `id`.
2. Items with the same `id` merge.
3. Overlay items may override `required`, `priority`, and `acceptance`.
4. LLM additions may not delete deterministic required items.
5. LLM-only additions require a `reason`.
6. The final checklist must not be empty.

Do not add numeric `weight` in the first implementation.

`weight=0.7` or `weight=1.0` looks precise but has no operational meaning until a scoring model exists. Use `required`, `priority`, `source`, and `acceptance` first.

## Proposed Schema

### WorkSpec

```json
{
  "artifact_type": "game",
  "domain": "poker",
  "capabilities": ["multiplayer", "realtime", "rules_engine"],
  "risk_areas": ["anti_cheat", "randomness", "authoritative_server"],
  "constraints": ["8_players"],
  "domain_hints": ["poker"]
}
```

### QualityContract

```json
{
  "contract_id": "research_quality_contract",
  "work_spec": {
    "artifact_type": "game",
    "domain": "poker",
    "capabilities": ["multiplayer", "realtime", "rules_engine"],
    "risk_areas": ["anti_cheat", "randomness", "authoritative_server"]
  },
  "packs_applied": [
    "base",
    "artifact:game",
    "capability:multiplayer",
    "capability:realtime",
    "domain:poker"
  ],
  "checklist": [
    {
      "id": "authoritative_server",
      "title": "Authoritative server",
      "source": "capability_pack",
      "required": true,
      "priority": "high",
      "acceptance": "Evidence explains how server-owned state prevents invalid client actions."
    }
  ]
}
```

### Evidence Gap

```json
{
  "checklist_id": "authoritative_server",
  "severity": "high",
  "reason": "No source supports server-authoritative game state handling.",
  "recovery_query": "authoritative server multiplayer poker game anti cheat"
}
```

## RecoverySearchLoop Contract

`RecoverySearchLoop` should not build the checklist.

Its responsibility:

```text
Given a QualityContract, determine whether the evidence satisfies each required item.
```

Bad behavior:

```python
if not checklist:
    return []
```

Replacement:

```python
if not quality_contract.checklist:
    raise QualityContractBuildError("quality contract has no checklist items")
```

If runtime behavior cannot raise, return a degraded evidence bundle:

```json
{
  "status": "degraded",
  "error": "quality_contract_empty",
  "gaps": [
    {
      "severity": "critical",
      "reason": "No checklist was generated, so research quality cannot be evaluated."
    }
  ]
}
```

The important rule is that checklist absence must never be interpreted as gap absence.

## Suggested File Layout

```text
core/
  research/
    work_spec.py
    quality_contract.py
    checklist_merger.py
    recovery_search_loop.py

core/research/packs/
  base.yaml
  artifacts/
    game.yaml
    webapp.yaml
    backend_service.yaml
    data_pipeline.yaml
  capabilities/
    multiplayer.yaml
    realtime.yaml
    auth.yaml
    payments.yaml
    search.yaml
  domains/
    poker.yaml
    chess.yaml
    ecommerce.yaml
```

If the existing project prefers a flatter `core/researcher.py` structure, these can initially be introduced as helper modules without moving the whole research pipeline.

## Migration Plan

### Phase 1: Temporary D3 Unblock

Purpose: finish the current poker-specific D3 verification without pretending the root issue is fixed.

Actions:

- Patch compound detection such as `포커게임`.
- Record in `NEXT_STEPS` that this is a temporary D3 compatibility patch.
- Explicitly move the root redesign into a follow-up P4 task.

### Phase 2: Introduce QualityContract

Actions:

- Add `WorkSpec` model.
- Add `QualityContract` model.
- Add `base`, `artifact:game`, `capability:multiplayer`, `capability:realtime`, and `domain:poker` packs.
- Keep existing research output shape as stable as possible.

### Phase 3: Convert Domain Checklist To Overlay

Actions:

- Move or reinterpret `poker.yaml` as a domain overlay.
- Rename `_detect_domain()` to `_detect_domain_hints()`.
- Ensure hint failure does not skip base/artifact/capability packs.

### Phase 4: Add LLM Request-Specific Criteria

Actions:

- Ask the LLM for request-specific checklist additions after deterministic packs are selected.
- Require `id`, `title`, `reason`, and `acceptance`.
- Reject additions that duplicate existing canonical items.

### Phase 5: Remove Silent Pass

Actions:

- Delete `if not checklist: return []`.
- Replace it with `QualityContractBuildError` or degraded critical gap output.
- Add regression tests proving empty contract is not a pass.

### Phase 6: Regression Test Multiple Domains

Minimum test prompts:

- `포커 만들기`
- `포커게임 만들기`
- `8인 네트워크 포커게임 만들어줘`
- `체스 게임 만들기`
- `쇼핑몰 만들기`
- `블로그 시스템 만들기`
- `실시간 채팅앱 만들기`

Expected result:

- All prompts produce a non-empty quality contract.
- Poker prompts apply poker overlay when detected or inferred.
- Non-poker prompts still apply base and artifact/capability packs.
- No prompt passes because checklist is empty.

## Open Questions

1. Should `WorkSpecExtractor` be fully LLM-based, or should it combine deterministic hint extraction plus LLM normalization?
2. Should domain overlays be selected by LLM suggestion, regex hints, or both?
3. Where should the canonical pack registry live?
4. Should `research_evidence.json` include the full `QualityContract`, or only contract metadata plus checklist results?
5. Which downstream consumers require backward-compatible fields during migration?

## Recommendation

Implement the refactor as a compatibility-preserving migration, not a full rewrite.

The first durable milestone should be:

```text
Every research request produces a non-empty QualityContract before RecoverySearchLoop runs.
```

The second milestone should be:

```text
Domain detection failure never disables the research quality gate.
```

The final target:

```text
Research quality criteria are assembled from WorkSpec-derived packs and overlays, not selected by a single domain detector.
```

