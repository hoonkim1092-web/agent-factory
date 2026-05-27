# Code Review: planner

> Source: core/planner.py
> Date: 2026-05-24 00:19
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: WARN

### T3 Advisory

t3_required: yes

This is a new `core/*.py` behavior module that changes planning semantics and frozen-build surface.

### Findings

1. [High] Verification can run before investigation-only prerequisites
   - File: `core/planner.py:186`
   - Code: `depends_on=list(impl_ids),`
   - Issue: `_build_verification_step()` only depends on implementation steps. If the plan has research-gap investigation steps and verification commands but no scope items, the verification step has no dependencies and a DAG executor can run it before the research gap is resolved. That contradicts the module contract: investigation → implementation → verification.
   - Suggestion: Pass all prior step IDs into verification, e.g. `depends_on=list(investigation_ids + impl_ids)`.

2. [Medium] Nested `core/` modules get no test requirement
   - File: `core/planner.py:78`
   - Code: `if p.suffix == ".py" and p.parent.name in ("core", "scripts"):`
   - Issue: AF has many nested modules like `core/providers/session_adapter.py`, `core/hooks/checkpoint.py`, and `core/control/supervisor.py`. This condition returns `None` for those, so implementation steps for nested core changes omit expected test guidance.
   - Suggestion: Check top-level path parts instead: `if p.suffix == ".py" and p.parts and p.parts[0] in {"core", "scripts"}`.

3. [Medium] Whitespace-prefixed manual checks become executable commands
   - File: `core/planner.py:88`
   - Code: `if not v.command.startswith("#"):`
   - Issue: The planner filters comment-style verification commands only when `#` is the first character. A command like `"  # Resolve gap before implementation"` is included in `verification_requirements` and the verification step’s commands, which can later be treated as executable work.
   - Suggestion: Normalize first: `command = v.command.strip()` and include only `command and not command.startswith("#")`.

4. [Medium] Research-gap resolution check can be fooled by boilerplate tokens
   - File: `core/planner.py:120`
   - Code: `risk_tokens = set(_WORD_RE.findall(risk.description.lower()))`
   - Issue: The comparison includes boilerplate words from `"Unanswered research question: ..."`. A scope item such as `core/research_question.py` can intersect on `research` or `question` and incorrectly mark an unrelated gap as resolved.
   - Suggestion: Strip the known prefix before tokenizing and ignore generic stop words, or carry the raw gap text separately from `PremortomRisk`.

### Comparison with Known Issues

- The new `core.planner` hidden import is present in `af.spec`, so the known `af.spec missing` pattern is addressed.
- I did not see non-atomic writes, shell subprocess construction, thread joins, shared async state, or cache growth in `core/planner.py`.
- The command handling is adjacent to AF’s known shell/Windows risk area: planner stores verification commands from premortem verbatim, so filtering needs to be stricter before a later runner executes them.

### Positive Observations

- `PlanStep` and `ExecutablePlan` use dataclass default factories, avoiding shared mutable defaults.
- The tests cover serialization, step ordering, dependencies, command collection, and hidden verification command storage; `pytest -q tests/test_planner.py` passes: `35 passed`.