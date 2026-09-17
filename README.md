# Agent Factory

**Project-scoped multi-agent orchestration and verification for AI-assisted software work.**

Agent Factory is a Python-based harness for running role-based AI agents against a project, composing them into repeatable workflows, and putting planning, review, tests, and evidence around agent-generated changes.

It can work with multiple CLI providers, including **Codex CLI, Claude CLI, and Gemini CLI**, while keeping project context, skills, workflows, and runtime state separated by project.

> **Maintenance status — September 2026**
>
> Major feature development is currently paused. This repository is undergoing a maintenance refresh focused on public documentation, repository hygiene, CI recovery, and compatibility validation. This is intentionally not a claim of continuous active development.

## What is implemented

- **Project-scoped execution** — run agents against an explicit project rather than a single global context.
- **Multi-provider CLI support** — provider discovery and adapters for `codex_cli`, `claude_cli`, and `gemini_cli`.
- **Role-based agents** — reusable agent definitions for architecture, planning, research, frontend/backend work, and design-oriented tasks.
- **Workflow orchestration** — YAML workflows can coordinate multiple agents around one task.
- **Planning-first execution** — the system is designed to separate planning/specification from implementation instead of immediately generating code.
- **Skill lifecycle tooling** — commands exist for skill creation, specification, preflight checks, evaluation, and promotion.
- **Review and verification plumbing** — test/review gates, warning registries, evidence-oriented checks, and dogfooding workflows are part of the codebase.
- **Optional autonomous maintenance loops** — nightly start/stop/status/tick commands exist for explicitly enabled unattended runs.
- **Project sync helpers** — Git- and DB-oriented helpers are included for moving project state between environments.

## Quick start

### Requirements

- Python **3.9+**
- One or more supported AI CLIs if you want live model execution
- Provider authentication configured separately for the CLI(s) you use

Create an environment and install dependencies:

```bash
python -m venv .venv
```

macOS / Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python run_factory_cli.py --help
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_factory_cli.py --help
```

### Run one role against a project

```bash
python run_factory_cli.py \
  --project logistics_v1 \
  --role "Backend Architect" \
  --task "Design an order API"
```

### Run a workflow

```bash
python run_factory_cli.py \
  --project logistics_v1 \
  --workflow workflows/two_week_webapp_delivery.yaml \
  --agents "Lilith,Himari" \
  --task "Run a two-week demo plan"
```

Provider availability is detected at runtime. If a supported CLI is not installed or authenticated, live provider-backed tasks may not run.

## Repository map

| Path | Purpose |
| --- | --- |
| `run_factory_cli.py` | Main CLI and subcommand entry point |
| `agent_launcher.py` | Agent, skill, and workflow orchestration |
| `core/` | Orchestration, review, verification, state, and runtime logic |
| `agents/` | Role/agent definitions |
| `skills/` | Reusable skill definitions and skill tooling |
| `workflows/` | Multi-agent workflow definitions |
| `projects/` | Project-scoped configuration and checked-in project data |
| `tests/` | Automated tests |
| `.github/workflows/` | CI configuration |

## Design principles

### 1. Planning before implementation

The harness is designed to make specification and planning explicit before code-writing stages. The goal is not to maximize autonomous code generation; it is to make agent work easier to inspect and verify.

### 2. Evidence over blind autonomy

Review, tests, warnings, and generated evidence are first-class parts of the repository. An agent completing a task is not, by itself, treated as proof that the task is correct.

### 3. Project isolation

Project state is organized under project scopes so different workspaces can keep their own agents, policies, artifacts, runs, and context.

### 4. Provider flexibility

Agent Factory is not intended to depend on a single model vendor. Provider-specific CLIs are treated as execution backends behind a common orchestration layer where possible.

## Safety and secrets

- Never commit `.env`, API keys, access tokens, auth caches, or provider credentials.
- Review generated code before merging or executing it in a sensitive environment.
- Autonomous/nightly modes should be enabled only in a workspace whose permissions and blast radius you understand.
- The repository may contain provider or MCP configuration intended for development environments. Review those permissions before reuse.
- See [`SECURITY.md`](SECURITY.md) for reporting security problems.

## Development and verification

The repository includes a pytest configuration and GitHub Actions CI. The current maintenance refresh is explicitly tracking restoration of a clean CI baseline; do not infer that every historical configuration is currently green.

Typical local checks:

```bash
python -m pytest -m "not slow and not e2e" -q
black --check config core utils
mypy core/ config/ utils/ --ignore-missing-imports
```

Slow and end-to-end tests are marked separately in `pytest.ini`.

## Contributing

Contributions that improve reliability, documentation, provider compatibility, tests, and reproducibility are welcome during the maintenance phase. Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request.

## Project history

This codebase went through substantial iterative development and dogfooding before the current maintenance phase. The Git history contains the implementation and review trail; the current goal is to make the public repository easier to understand, test, and maintain without pretending that feature development never paused.

## License

**No explicit open-source license has been declared for this repository yet.** Until the repository owner adds one, default copyright rules apply. A license decision is tracked as a maintenance item before presenting the project as formally open source.
