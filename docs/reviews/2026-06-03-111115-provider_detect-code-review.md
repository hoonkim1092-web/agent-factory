# Code Review: provider_detect

> Source: core/provider_detect.py
> Date: 2026-06-03 11:11
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: WARN

### T3 Advisory

t3_required: yes

This change alters provider probing behavior for Tier 3 review fan-out and authentication blocking.

### Findings

1. [High] Installed Gemini/Codex CLIs now trigger live auth/model probes even when API credentials are absent
   - File: `core/provider_detect.py:270`
   - Code: `return _ping_one(provider_id)`
   - Issue: The diff removed the `_PROVIDER_KEY_ENVS` guard, so any installed `gemini_cli` or `codex_cli` is now probed unconditionally. For Gemini, the probe command is `gemini -p ok` (`core/provider_detect.py:53`), which can make a real model/API call or fail due missing credentials. That failure is later treated as `AUTH_EXPIRED`, which `review_runner.detect_blocked_providers()` converts into a Tier 3 block.
   - Suggestion: Restore a credential/session preflight before model-style pings, or add provider-specific non-generative status checks. If no credential/session is configured, return `NOT_INSTALLED` or a non-blocking `UNCONFIGURED`, not `AUTH_EXPIRED`.

2. [High] All non-zero probe failures are still classified as auth expiry
   - File: `core/provider_detect.py:234`
   - Code: `state=ProviderState.AUTH_EXPIRED,`
   - Issue: `subprocess.run()` returning non-zero can mean unsupported command, network failure, quota failure, model error, malformed flags, or CLI crash. After this change, `codex_cli` uses `codex login status`; if that command is unavailable or fails for a non-auth reason, it becomes `AUTH_EXPIRED`. The caller then blocks on it at `core/review_runner.py:61`.
   - Suggestion: Classify stderr/stdout using known auth markers before returning `AUTH_EXPIRED`. Add a separate non-blocking state such as `PROBE_FAILED`, or map unknown failures to `NOT_INSTALLED`/WARN for fan-out purposes.

3. [Medium] Codex ping change regresses the documented hang-safe baseline without compatibility gating
   - File: `core/provider_detect.py:54`
   - Code: `"codex_cli": ["login", "status"],`
   - Issue: `Master_Blueprint.md:116` documents the current baseline as `codex_cli ping: --version (exec stdin hang fix)`, and prior code-review history around `provider_detect.py` specifically called out Codex ping replacement/hang churn. The new command is more semantically useful, but there is no fallback if older/newer Codex CLI builds do not support `login status`, so a CLI-version mismatch can become a false auth block.
   - Suggestion: Probe command support first, or use a two-step fallback: try `codex login status`, and if the command is unknown, fall back to `codex --version` plus mark auth as unknown/non-blocking.

4. [Medium] Tests no longer cover the behavior removed by the diff
   - File: `tests/test_provider_detect.py:97`
   - Code: `monkeypatch.setenv("OPENAI_API_KEY", "test-key")`
   - Issue: The tests still seed API keys, but the production code no longer reads them. There is no regression test for “CLI installed, no API key/session, do not perform costly/blocking model ping,” which is exactly the behavior changed here.
   - Suggestion: Add tests for installed Gemini/Codex with no relevant env/session and assert the desired non-blocking behavior. Also add a test where `codex login status` returns an “unknown command” error and verify it is not classified as `AUTH_EXPIRED`.

### Comparison with Known Issues

- This change intersects known provider-detect risks in `docs/code_review/code-review.md`, especially historical churn around Codex ping replacement and review-gate blocking behavior.
- It repeats a known design concern from prior reviews: unknown probe failures are collapsed into `AUTH_EXPIRED`, which can turn transient or compatibility failures into hard Tier 3 blocks.

### Positive Observations

- The cache write path still uses temp-file plus `os.replace`, avoiding the known non-atomic write pattern.
- The installed-provider detection is still computed once before the thread pool, preserving the prior race-condition fix.