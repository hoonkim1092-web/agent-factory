# Code Review: context_scanner

> Source: core/control/context_scanner.py
> Date: 2026-05-14 17:07
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

(provider error: Reading prompt from stdin...
OpenAI Codex v0.130.0
--------
workdir: D:\hoonProJect\worktrees\agent-factory
model: gpt-5.5
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: medium
reasoning summaries: none
session id: 019e2586-b7b0-7422-b0e9-7c28b3d37a8a
--------
user
You are an independent code change critic for the Agent Factory project.
Your job is to find bugs, security issues, and design flaws in code changes.

## Input

You will receive:
1. A git diff showing c)