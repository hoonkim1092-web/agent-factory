# Code Review: build_llm_wiki

> Source: scripts/build_llm_wiki.py
> Date: 2026-06-02 02:26
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This change affects generated file writes, subprocess-backed metadata, and parsing behavior.

### Findings

1. [High] `--out` can escape the workspace and overwrite files outside the repo
   - File: `scripts/build_llm_wiki.py:274`
   - Code: `out_path = Path(workspace) / out_dir`
   - Issue: `out_dir` is CLI/user-controlled. Absolute paths or `..` traversal can cause the script to create/replace `index.md`, `architecture.md`, etc. outside the intended workspace.
   - Suggestion: Resolve `out_path` and reject it unless it is under the resolved workspace, or explicitly document and gate external output paths.

2. [High] Blueprint parser failure still writes successful but incomplete wiki output
   - File: `scripts/build_llm_wiki.py:69`
   - Code: `sec0_match = re.search(r"^## §0 ", text, re.MULTILINE)`
   - Issue: The new §0 slice depends on an exact heading. If the heading format drifts, the script only prints a warning, then writes `architecture.md` with empty root/core tables. That creates stale-looking generated docs while returning success.
   - Suggestion: Treat missing §0, missing root rows, or missing core rows as a build error with context, unless an explicit `--allow-empty` mode is added.

3. [Medium] Multi-file wiki generation is not atomic as a set
   - File: `scripts/build_llm_wiki.py:298`
   - Code: `for fname, content in pages.items():`
   - Issue: Each file is now atomically replaced, which fixes the per-file corruption issue, but the five-page wiki can still be left in a mixed generation if the process fails after replacing only some files.
   - Suggestion: Write all pages into a staging directory first, then swap/commit the complete set, or include a generation manifest and only publish it after all page replacements succeed.

4. [Medium] Cleanup failure is silently swallowed
   - File: `scripts/build_llm_wiki.py:306`
   - Code: `except OSError: pass`
   - Issue: If temp-file cleanup fails, the original exception is re-raised, but the leaked temp file is hidden. This repeats the known silent-fallback pattern in a cleanup path and can accumulate `.tmp` files during repeated failures.
   - Suggestion: Log cleanup failure to `stderr` with the temp path while preserving the original exception.

### Comparison with Known Issues

- The prior non-atomic direct write issue from `code-review.md` C2/M10 is addressed per file via `tempfile.mkstemp()` and `os.replace()`.
- The change still has a related consistency gap: the generated wiki set is not committed atomically.
- The parser behavior still resembles the known silent-fallback pattern: malformed source structure produces successful output with missing content.

### Positive Observations

- The direct `write_text()` path was replaced with temp-file plus `os.replace()`, which materially improves crash safety for individual files.
- Source metadata paths were changed to POSIX-style strings, reducing Windows/Unix generated-doc churn.