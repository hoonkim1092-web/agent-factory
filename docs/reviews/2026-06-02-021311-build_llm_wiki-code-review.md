# Code Review: build_llm_wiki

> Source: scripts/build_llm_wiki.py
> Date: 2026-06-02 02:13
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This change writes generated files, invokes `git` via subprocess, and changes parsing behavior.

### Findings

1. [Critical] Generated files are written non-atomically
   - File: `scripts/build_llm_wiki.py:297`
   - Code: `(out_path / fname).write_text(content, encoding="utf-8")`
   - Issue: A crash, Ctrl-C, disk-full event, or concurrent build can leave partially written wiki files. This repeats the known C2/M10 non-atomic write pattern in `docs/code_review/code-review.md`.
   - Suggestion: Write each page to a temp file in the same directory, then `os.replace(tmp_path, final_path)`.

2. [High] `--out` can escape the workspace and overwrite arbitrary files
   - File: `scripts/build_llm_wiki.py:272`
   - Code: `out_path = Path(workspace) / out_dir`
   - Issue: `out_dir` is user-controlled. Values like `..\..\somewhere` or an absolute path can write the generated `index.md`, `architecture.md`, etc. outside the intended workspace. This is especially risky because the script overwrites fixed filenames.
   - Suggestion: Resolve `out_path`, require it to stay under `workspace`, and reject absolute/parent-traversal output paths unless there is an explicit safe mode.

3. [High] Parser drift silently produces empty architecture output
   - File: `scripts/build_llm_wiki.py:68`
   - Code: `sec0_match = re.search(r"^## §0 ", text, re.MULTILINE)`
   - Issue: If `Master_Blueprint.md` changes the §0 heading format, `_parse_blueprint()` silently uses `sec0_text = ""` and `build()` still writes a successful `architecture.md` with empty root/core tables. The new slice makes this failure mode sharper because the parser no longer falls back to scanning the whole document.
   - Suggestion: After parsing, validate that expected rows exist, e.g. root/core counts are non-zero, and raise a contextual error if the §0 section or table headers are not found.

4. [Medium] Source path metadata is OS-dependent
   - File: `scripts/build_llm_wiki.py:24`
   - Code: `_CODE_REVIEW = os.path.join("docs", "code_review", "code-review.md")`
   - Issue: This value is emitted into generated frontmatter as a source identifier. On Windows it becomes `docs\code_review\code-review.md`; on Unix it becomes `docs/code_review/code-review.md`, causing cross-platform generated-doc churn.
   - Suggestion: Keep emitted source IDs as POSIX strings, e.g. `"docs/code_review/code-review.md"`, and convert to `Path` only when reading from disk.

### Comparison with Known Issues

- Repeats known non-atomic file write pattern C2/M10 from `code-review.md`.
- Repeats the silent fallback risk pattern H3 via successful output after parser failure.
- Touches AF’s Windows/Unix path compatibility surface; the generated docs currently encode Windows separators.

### Positive Observations

- `_git()` uses an argv list with `shell=False`, so the subprocess call avoids shell injection.
- Tests cover core parser behavior and confirm source documents are not modified; `python -m pytest tests/test_build_llm_wiki.py -q` passes locally with 17 tests.