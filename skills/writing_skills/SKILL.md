---
id: writing_skills
name: Writing Skills
version: 0.1.0
inspired_by: superpowers/writing-skills
description: SKILL.md knowledge skill authoring guide — external patterns, local procedures, and review learnings into concise, triggerable AF skills.
when_to_use: When creating or updating SKILL.md-only knowledge skills, absorbing external playbooks into AF, or converting repeatable guidance into a reusable skill.
when_NOT_to_use: When implementing executable skill.py action skills, changing core skill loading code, or writing one-off project documentation that should not be auto-invoked.
when_to_use_keywords:
  - skill
  - SKILL.md
  - writing-skills
  - external skill
  - skill absorption
  - knowledge skill
  - pattern absorption
  - 스킬
  - 스킬흡수
  - 외부스킬
category: skill-authoring
skill_type: knowledge
auto_invocable: true
user_invocable: true
planner_invocable: true
tags:
  - skills
  - authoring
  - absorption
  - documentation
---

# Writing Skills Guide

Use this when turning an external workflow or repeated local practice into an AF `SKILL.md` knowledge skill. The goal is a compact, discoverable procedure that changes future agent behavior without adding unnecessary code.

## Fit Check

Create a `SKILL.md` knowledge skill only when all of these are true:

1. The guidance is repeatable across tasks, not a one-off project note.
2. The trigger can be described clearly in frontmatter.
3. The workflow benefits from being loaded only when relevant.
4. The expected behavior can be verified by reading the skill and checking discovery paths.
5. No executable tool is needed for deterministic work.

Do not create a skill just to preserve background research. Put broad analysis in `docs/` and keep the skill procedural.

## Frontmatter Contract

Every AF knowledge skill should include:

- `id`: stable snake_case directory-aligned identifier.
- `name`: short human-readable name.
- `version`: start at `0.1.0` for newly absorbed guidance.
- `inspired_by`: external source path or identifier when derived from outside AF.
- `description`: one sentence that includes both the topic and the trigger surface.
- `when_to_use`: concrete invocation conditions.
- `when_NOT_to_use`: explicit boundaries to reduce false positives.
- `when_to_use_keywords`: Korean and English terms likely to appear in requests.
- `category`, `skill_type: knowledge`, invocation booleans, and tags.

Keep frontmatter factual. Do not promise automation that the skill does not implement.

## Body Structure

Use this layout unless the target domain has a stronger local convention:

1. Purpose: what behavior changes after the skill loads.
2. Fit check: when to use the skill and when to avoid it.
3. Workflow: 3 to 6 ordered steps.
4. Output or verification contract: what must be true before completion.
5. Checklist: short, operational, and testable.

Prefer specific commands or file paths when they are stable. Avoid long essays, motivational language, and generic advice the model already knows.

## Absorption Workflow

1. Read the external source and identify the non-obvious behavioral pattern.
2. Compare with existing AF mechanisms in `docs/` or `core/` so the new skill does not duplicate stronger built-in behavior.
3. Choose a narrow `id` and directory under `skills/`.
4. Write `SKILL.md` as a knowledge skill with `inspired_by` attribution.
5. Add or update a lightweight doc note if the absorption is part of a measured round or decision.
6. Verify discovery with `resolve_knowledge_skill_path()` or the relevant skill discovery tests.

## Review Checks

Before completion:

- [ ] The skill has a concrete trigger and a clear non-trigger.
- [ ] The body is procedural, not a research archive.
- [ ] `inspired_by` is present for external patterns.
- [ ] The directory name, `id`, and keywords agree.
- [ ] No code behavior is claimed unless code changed.
- [ ] A small verification command or test was run.
