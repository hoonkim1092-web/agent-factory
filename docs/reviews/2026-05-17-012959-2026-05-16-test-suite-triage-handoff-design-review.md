# Design Review: 2026-05-16-test-suite-triage-handoff

> Source: docs/2026-05-16-test-suite-triage-handoff.md
> Date: 2026-05-17 01:29
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [High] Handoff state is stale and cannot be resumed as written
   - Section: "`현재 워킹트리 (미커밋 9개)`", "`테스트 3개만 stage... git commit ...`"
   - Issue: Current repo state does not match the document. The three test changes were already committed in `ae786417` (`fix(tests): repair stale suite...`), and current `git status` shows a different dirty set (`NEXT_STEPS.md`, `core/agent_worker.py`, `core/dynamic_orchestrator.py`, etc.).
   - Suggestion: Add a preflight section: verify `git status --short`, verify `git diff -- tests/...` is non-empty, and abort if commit `ae786417` or later already contains the intended changes.

2. [Critical] `test_sync_wrappers` fix targets deleted `.cmd` wrappers
   - Section: "`test_sync_wrappers` | `@pytest.mark.skipif(sys.platform != \"win32\")` | `.cmd` 래퍼는 Windows 전용"
   - Issue: `start_db.cmd`, `start_sync.cmd`, and `sync.cmd` are not real current files. They were deleted by `ba401c93 feat: .cmd → .py 크로스 플랫폼 전환`. The test still tries to copy them at [tests/test_sync_wrappers.py](/Users/hoon/workTree/agent-factory/tests/test_sync_wrappers.py:10), so it will fail on Windows instead of being skipped.
   - Suggestion: Replace this with tests for `start_db.py`, `start_sync.py`, and the console scripts in [pyproject.toml](/Users/hoon/workTree/agent-factory/pyproject.toml:10). If legacy `.cmd` support is intentionally removed, delete or rewrite `tests/test_sync_wrappers.py`.

3. [High] Mode change from `shadow_reuse` to `enhance` is not “부수 단언”
   - Section: "`test_skill_retrieval_engine` test 2 | 출력 `shadow_reuse`→`enhance` ... mode는 부수 단언"
   - Issue: `mode` controls different production branches in [core/skill_procurer.py](/Users/hoon/workTree/agent-factory/core/skill_procurer.py:970): `enhance` calls `_try_enhance_skill`, while `shadow_reuse` builds/adapts at [core/skill_procurer.py](/Users/hoon/workTree/agent-factory/core/skill_procurer.py:1020). Treating it as incidental misses a behavior change.
   - Suggestion: Add explicit tests for `enhance` routing and enhance failure fallback. Keep reranking tests focused, but cover the downstream branch because the mode is architecturally significant.

4. [Medium] `PYTHONPATH` injection fixes only the test harness, not script usability
   - Section: "`test_text_integrity` | subprocess에 `PYTHONPATH` env 주입"
   - Issue: [scripts/check_changed_text_integrity.py](/Users/hoon/workTree/agent-factory/scripts/check_changed_text_integrity.py:9) imports `core.text_integrity` directly. The proposed test-only `PYTHONPATH` injection proves the test can run, but does not prove the script works when invoked from another repo, hook, subprocess, or frozen/dev environment without that env.
   - Suggestion: Either make the script self-bootstrap the project root into `sys.path`, or document that it must be invoked via repo tooling that sets `PYTHONPATH`. Add a test for the intended real invocation path.

5. [Medium] Runtime artifact cleanup plan omits tracked-file behavior
   - Section: "`data/skill-usage.jsonl`, `skill-eval-report.json`, `skills/new_skill/*.json`을 `.gitignore`에 추가할지 결정"
   - Issue: `.gitignore` alone does not stop churn for files already tracked historically. `git log` shows these artifact paths were committed repeatedly, and current cleanup needs to distinguish untracked ignore from tracked removal.
   - Suggestion: Specify `git ls-files` verification and, if any are tracked, use `git rm --cached` plus `.gitignore`. Also define whether generated skill metadata under `skills/new_skill/` is product data or disposable runtime output.

### Missing from Design

- A current-state guard to prevent replaying an already-applied handoff.
- Windows validation for the `.cmd` wrapper claim, especially after `ba401c93`.
- Downstream tests for `SkillRetrievalEngine.mode == "enhance"` through `SkillProcurer`.
- Frozen-build or packaged invocation expectations for `scripts/check_changed_text_integrity.py`.
- A concrete CI/pre-commit gate design; the document identifies the gap but only plans the immediate test commit.

### Positive Observations

- The document correctly identifies `enhance_confidence=0.70` and `CapabilityGap` in [core/skill_retrieval_engine.py](/Users/hoon/workTree/agent-factory/core/skill_retrieval_engine.py:11) as real current behavior, not an accidental regression.
- It separates test repair from runtime artifact pollution, which is the right ownership split; the issue is that the cleanup plan needs tracked-file handling.