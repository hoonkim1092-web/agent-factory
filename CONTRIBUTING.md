# Contributing to Agent Factory

Thanks for helping improve Agent Factory. The project is currently in a maintenance-focused phase, so small, reviewable changes that improve reliability and reproducibility are preferred over broad rewrites.

## Good contribution targets

- Fixing reproducible bugs
- Restoring or improving automated tests and CI
- Improving setup, troubleshooting, and architecture documentation
- Improving Codex / Claude / Gemini CLI compatibility without hard-coding one provider
- Removing generated runtime artifacts from source control
- Making review, verification, and failure evidence easier to inspect

## Before opening a pull request

1. Start from the current default branch.
2. Keep the change focused and explain why it is needed.
3. Add or update tests when behavior changes.
4. Run the relevant local checks when possible:

```bash
python -m pytest -m "not slow and not e2e" -q
black --check config core utils
mypy core/ config/ utils/ --ignore-missing-imports
```

5. Do not commit generated run output, local state, credentials, `.env` files, auth caches, API keys, access tokens, or machine-specific secrets.

## Pull request notes

A useful PR description should include:

- what changed;
- why it changed;
- how it was verified;
- known limitations or follow-up work;
- whether the change affects provider permissions, autonomous execution, or external services.

For large architectural changes, open an issue first so the intended behavior and migration path can be discussed before implementation.

## Generated files

Agent Factory can create runtime logs, runs, state, evaluation output, and other local artifacts. These generally should not be committed. If a generated artifact is necessary as a test fixture, keep it minimal and document why it belongs in source control.

## Security

Do not report credentials, authentication material, or exploitable security findings in a public issue. Follow `SECURITY.md` instead.
