# Code Review: agent_runner

> Source: core/agent_runner.py
> Date: 2026-06-04 23:07
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

`t3_required: yes`

Meaningful multi-provider routing and review-gate behavior changed.

### Findings

1. [High] Selected review provider is never used during execution
   - File: `core/project_task_board.py:1143`
   - Code: `"review_provider": review_provider,`
   - Issue: `review_provider` is written to the board but has no reader anywhere under `core/`. Cross-validation agents therefore execute through normal routing, potentially using the author provider.
   - Suggestion: Propagate `task_meta["review_provider"]` into `AgentRunner.run()` as an explicit provider override and verify the executed result matches it.

2. [High] Native and CLI provider IDs are incompatible
   - File: `core/agent_runner.py:1279`
   - Code: `"provider_id": "openai",`
   - Issue: Native results use `openai`, `anthropic`, and `gemini`, while `pick_review_provider()` compares against `codex_cli`, `claude_cli`, and `gemini_cli`. For example, an `anthropic` author can be reviewed by `claude_cli`, violating cross-provider validation.
   - Suggestion: Introduce canonical provider-family IDs and compare families when excluding the author provider.

3. [High] OpenAI and Anthropic success paths skip post-execute hooks
   - File: `core/agent_runner.py:1291`
   - Code:
     ```python
     _flush_trace(result)
     return result
     ```
   - Issue: Unlike CLI and Gemini success paths, OpenAI and Anthropic return without `bus.run_post_execute()`. Checkpoint, code-review documentation, tracing, and memory hooks are skipped.
   - Suggestion: Run `result = bus.run_post_execute(agent_state, result)` before trace flushing and returning on both native paths.

4. [Medium] Tests mock away the routing behavior being changed
   - File: `tests/test_inject_review_tasks_e2e_command.py:105`
   - Code: `patch("core.providers.registry.pick_review_provider", side_effect=_fake_pick)`
   - Issue: Tests only verify that a string reaches a mocked picker. They do not detect native/CLI ID mismatches or prove `review_provider` affects execution.
   - Suggestion: Add integration tests covering native-provider authors and actual cross-validator dispatch.

### Comparison with Known Issues

- Repeats the documented multi-provider fragmentation concerns around `agent_runner.py` and the provider registry.
- The skipped post-execute hooks are consistent with the documented provider-event/hook integration gap.
- No direct regression of the known atomic-write or cache issues was found.

### Positive Observations

- `provider_id` was added consistently to all successful execution result variants.
- Worker result serialization preserves the new field without schema changes.
- Verification: `53 passed`; `git diff --check` passed.