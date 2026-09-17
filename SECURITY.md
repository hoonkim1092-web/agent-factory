# Security Policy

## Reporting a vulnerability

Please do **not** open a public issue containing exploitable details, credentials, tokens, private endpoints, or authentication material.

Use GitHub's private vulnerability reporting flow from the repository's **Security** tab when it is available. If that option is unavailable, contact the maintainer through the GitHub profile and share only the minimum information needed to establish a private reporting channel.

A useful report includes:

- affected component and revision;
- reproduction steps or a minimal proof of concept;
- expected versus observed behavior;
- likely impact;
- any suggested mitigation, if known.

## Scope

Security-sensitive areas include provider authentication, subprocess/CLI execution, MCP configuration, autonomous or nightly execution, repository write operations, project synchronization, local runtime state, and any handling of secrets or generated code.

## Operational guidance

Agent Factory can invoke external AI CLIs and automation tooling. Before running it in a sensitive environment:

- review provider and MCP permissions;
- use the least-privileged credentials practical;
- keep `.env`, tokens, auth caches, and local state out of Git;
- review generated commands and code before execution or merge;
- limit the filesystem and repository scope available to autonomous workflows.

No historical configuration should be assumed safe for a new environment without review.
