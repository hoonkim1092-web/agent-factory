# Code Review: dynamic_orchestrator

> Source: core/dynamic_orchestrator.py
> Date: 2026-06-04 23:03
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

`t3_required: yes`

Provider routing and cross-validation behavior are meaningfully changed.

### Findings

1. [High] `review_provider` is stored but never used during execution
   - File: `core/project_task_board.py:1151`, `core/project_task_board.py:808`
   - Code:
     ```python
     "review_provider": review_provider,
     ```
     ```python
     chosen.append({
         "assigned_role": role,
         "subtask_instruction": ...,
         "task_id": ...,
     })
     ```
   - Issue: `review_provider` has no consumer outside task creation/tests. `next_board_tasks()` drops it, and `AgentRunner` selects providers from role-based routing. The change therefore does not actually route cross-validation to the selected provider.
   - Suggestion: Propagate `review_provider` through dispatch and make `AgentRunner` explicitly prioritize it.

2. [High] SDK provider IDs are incompatible with CLI routing IDs
   - File: `core/dynamic_orchestrator.py:841`, `core/providers/registry.py:312`
   - Code:
     ```python
     provider_id=str(result.get("provider_id") or result.get("reason") or "")
     ```
     ```python
     candidates = [p for p in available if p != author_provider]
     ```
   - Issue: Successful API executions return IDs such as `anthropic`, `openai`, and `gemini`, while routing expects `claude_cli`, `codex_cli`, and `gemini_cli`. For an `anthropic` author, `claude_cli` is considered different and may be selected, violating cross-provider validation.
   - Suggestion: Normalize execution provider IDs into one canonical provider/vendor namespace before comparison.

3. [High] FSA decomposition success passes a human-readable reason as a provider ID
   - File: `core/dynamic_orchestrator.py:954`, `core/fsa_loop.py:342`
   - Code:
     ```python
     provider_id=str(fsa_result.get("provider_id") or fsa_result.get("reason") or "")
     ```
     ```python
     success_result = {
         "ok": True,
         "reason": "FSA 태스크 분해 후 전체 성공",
     }
     ```
   - Issue: FSA decomposition success has no `provider_id`, so the success message becomes the author provider. Routing then treats every available provider as different and can select the actual author again.
   - Suggestion: Track providers used by FSA subtasks and return a canonical `provider_id`; never use `reason` as provider identity.

4. [High] Cross-validation eligibility uses installed providers instead of active providers
   - File: `core/project_task_board.py:1122`, `core/providers/registry.py:311`
   - Code:
     ```python
     available = detect_installed_cli_providers()
     if available_count >= 2:
     ```
     ```python
     available = detect_available_cli_providers()
     ```
   - Issue: A cross-validation task is created when two CLIs are installed even if only one is configured for the run. `pick_review_provider()` then returns the same active provider, defeating independent validation.
   - Suggestion: Use `detect_available_cli_providers()` consistently for both eligibility and selection.

### Comparison with Known Issues

- The change targets the documented multi-provider/provider-policy area, but does not complete provider routing.
- It repeats the known provider integration problem where configured, installed, CLI, and API provider identities are inconsistently handled.
- The previously documented `dynamic_orchestrator` state-lock issue is not reintroduced.

### Positive Observations

- `provider_id` was added consistently to all direct successful `AgentRunner` backend paths.
- The focused tests pass: `12 passed`, and `git diff --check` reports no whitespace errors.