#!/usr/bin/env python3
"""Deterministic Tier-3 review classifier.

The classifier is intentionally conservative:
- hard-guard paths always require Tier 3;
- risk tokens in added or deleted diff lines always require Tier 3;
- only Python changes that are AST-equivalent after removing docstrings
  may skip Tier 3 (annotations are preserved as semantic — see
  `_CosmeticAstNormalizer`).
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Literal

try:
    from blast_radius import classify_path
except Exception:  # pragma: no cover - import style differs under pytest/package use
    from scripts.blast_radius import classify_path  # type: ignore


CLASSIFIER_VERSION = "t3-deterministic-v1"
Decision = Literal["require_t3", "skip_t3"]

_RISK_TOKEN_RE = re.compile(
    r"\b("
    r"auth|oauth|jwt|token|secret|credential|password|api[_-]?key|permission|policy|gate|hook|"
    r"subprocess|shell|os\.system|os\.remove|os\.unlink|rmtree|requests|httpx|urllib|"
    r"eval|exec|git\s+(?:reset|push|rebase|checkout|merge)"
    r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class T3Decision:
    decision: Decision
    reason: str
    classifier_version: str
    files: list[str]
    diff_summary: dict[str, int]

    @property
    def t3_required(self) -> bool:
        return self.decision == "require_t3"

    def to_state(self) -> dict[str, object]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "classifier_version": self.classifier_version,
            "files": list(self.files),
            "diff_summary": dict(self.diff_summary),
        }


class _CosmeticAstNormalizer(ast.NodeTransformer):
    """Remove docstrings before comparison.

    Python annotations are runtime-observable via __annotations__ and by
    frameworks such as dataclasses, Pydantic, FastAPI, and CLI/schema builders,
    so annotation changes are treated as semantic.
    """

    def _strip_docstring(self, node: ast.AST) -> ast.AST:
        body = getattr(node, "body", None)
        if (
            isinstance(body, list)
            and body
            and isinstance(body[0], ast.Expr)
            and isinstance(getattr(body[0], "value", None), ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            body.pop(0)
        return node

    def visit_Module(self, node: ast.Module) -> ast.AST:
        self.generic_visit(node)
        return self._strip_docstring(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        self.generic_visit(node)
        return self._strip_docstring(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self.generic_visit(node)
        return self._strip_docstring(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        self.generic_visit(node)
        return self._strip_docstring(node)


def _normalize_path(rel_path: str) -> str:
    norm = rel_path.replace("\\", "/")
    while norm.startswith("./"):
        norm = norm[2:]
    return norm


def _git(args: list[str], workspace: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=5,
    )


def _read_head_file(workspace: str, rel_path: str) -> str | None:
    result = _git(["show", f"HEAD:{rel_path}"], workspace)
    if result.returncode != 0:
        return None
    return result.stdout


def _read_worktree_file(workspace: str, rel_path: str) -> str | None:
    path = os.path.join(workspace, rel_path)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def _git_diff(workspace: str, rel_path: str) -> str:
    result = _git(["diff", "HEAD", "--", rel_path], workspace)
    if result.returncode != 0:
        return ""
    return result.stdout


def _changed_diff_lines(diff_text: str) -> list[str]:
    lines: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith(("+++", "---")):
            continue
        if line.startswith(("+", "-")):
            lines.append(line[1:])
    return lines


def _summarize_diff(diff_texts: list[str]) -> dict[str, int]:
    added = deleted = 0
    for diff_text in diff_texts:
        for line in diff_text.splitlines():
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("+"):
                added += 1
            elif line.startswith("-"):
                deleted += 1
    return {"added": added, "deleted": deleted}


def _risk_tokens_present(diff_texts: list[str]) -> bool:
    for diff_text in diff_texts:
        for line in _changed_diff_lines(diff_text):
            if _RISK_TOKEN_RE.search(line):
                return True
    return False


def _normalized_ast_dump(source: str) -> str | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    tree = _CosmeticAstNormalizer().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.dump(tree, include_attributes=False)


def _is_python_cosmetic_only(before: str, after: str) -> bool:
    before_dump = _normalized_ast_dump(before)
    after_dump = _normalized_ast_dump(after)
    if before_dump is None or after_dump is None:
        return False
    return before_dump == after_dump


def classify_t3_requirement(workspace: str, files: list[str]) -> T3Decision:
    rel_files = sorted({_normalize_path(f) for f in files if f})
    diff_texts = [_git_diff(workspace, f) for f in rel_files]
    diff_summary = _summarize_diff(diff_texts)

    if not rel_files:
        return T3Decision("require_t3", "no-files", CLASSIFIER_VERSION, rel_files, diff_summary)

    for rel_path in rel_files:
        if classify_path(rel_path) == 3:
            return T3Decision(
                "require_t3",
                f"hard-guard-path:{rel_path}",
                CLASSIFIER_VERSION,
                rel_files,
                diff_summary,
            )

    if _risk_tokens_present(diff_texts):
        return T3Decision(
            "require_t3",
            "risk-token-overlay",
            CLASSIFIER_VERSION,
            rel_files,
            diff_summary,
        )

    for rel_path in rel_files:
        if not rel_path.endswith(".py"):
            return T3Decision(
                "require_t3",
                f"non-python-file:{rel_path}",
                CLASSIFIER_VERSION,
                rel_files,
                diff_summary,
            )
        before = _read_head_file(workspace, rel_path)
        after = _read_worktree_file(workspace, rel_path)
        if before is None or after is None:
            return T3Decision(
                "require_t3",
                f"missing-baseline-or-worktree:{rel_path}",
                CLASSIFIER_VERSION,
                rel_files,
                diff_summary,
            )
        if not _is_python_cosmetic_only(before, after):
            return T3Decision(
                "require_t3",
                f"semantic-python-change:{rel_path}",
                CLASSIFIER_VERSION,
                rel_files,
                diff_summary,
            )

    return T3Decision(
        "skip_t3",
        "cosmetic-only-python-ast",
        CLASSIFIER_VERSION,
        rel_files,
        diff_summary,
    )


def record_skip_telemetry(workspace: str, decision: T3Decision) -> None:
    if decision.t3_required:
        return
    queue_dir = os.path.join(workspace, ".af_review_queue")
    os.makedirs(queue_dir, exist_ok=True)
    path = os.path.join(queue_dir, "t3_skip_telemetry.jsonl")
    payload = {
        "timestamp": time.time(),
        "skip_reason": decision.reason,
        "classifier_version": decision.classifier_version,
        "diff_summary": decision.diff_summary,
        "files": decision.files,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _cli() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Deterministic T3 classifier")
    parser.add_argument("--workspace", "-w", default=os.getcwd())
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()

    decision = classify_t3_requirement(args.workspace, args.files)
    print(json.dumps(decision.to_state(), ensure_ascii=False, indent=2))
    return 0 if not decision.t3_required else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
