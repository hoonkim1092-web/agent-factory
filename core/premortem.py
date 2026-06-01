"""Premortem: repo-aware failure prediction converted into verification requirements.

§17 Step 5 — Add repo-context Premortem after Spec.

Takes a CompiledSpec and produces a PremortomResult: a list of risks each
mapped to concrete verification steps.  Detectors fire on scope/risk_hints/
assumptions/gaps rather than on generic heuristics.
"""
from __future__ import annotations

import ast
import os
import re
import shlex
from dataclasses import dataclass, field
from typing import Any

from core.spec_compiler import CompiledSpec


@dataclass
class VerificationStep:
    command: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {"command": self.command, "description": self.description}


@dataclass
class PremortomRisk:
    id: str
    description: str
    category: str
    verification: list[VerificationStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "category": self.category,
            "verification": [v.to_dict() for v in self.verification],
        }


@dataclass
class PremortomResult:
    risks: list[PremortomRisk] = field(default_factory=list)
    spec_intent: str = ""

    def has_risks(self) -> bool:
        return bool(self.risks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_intent": self.spec_intent,
            "risks": [r.to_dict() for r in self.risks],
        }


# ---------------------------------------------------------------------------
# Pattern helpers
# ---------------------------------------------------------------------------

_CORE_PY_RE = re.compile(r"\bcore/\S+\.py\b")
_CLI_ENTRY_RE = re.compile(r"\brun_factory_cli\.py\b|\baf\.spec\b")
_DOGFOOD_RE = re.compile(r"\bdogfood\b|\bworktree\b", re.I)
_DESTRUCTIVE_RE = re.compile(r"destructive|delete|drop|reset|force", re.I)


def _any_match(pattern: re.Pattern, items: list[str]) -> bool:
    return any(pattern.search(item) for item in items)


# ---------------------------------------------------------------------------
# Risk detectors
# ---------------------------------------------------------------------------

def _detect_blueprint_sync_risk(scope: list[str], risk_hints: list[str]) -> PremortomRisk | None:
    """core/*.py changes must be reflected in Master_Blueprint.md."""
    if not _any_match(_CORE_PY_RE, scope + risk_hints):
        return None
    files = [s for s in scope if _CORE_PY_RE.search(s)]
    if files:
        compile_step = VerificationStep(
            command=f"python -m py_compile {' '.join(shlex.quote(f) for f in files)}",
            description="No syntax errors in changed core modules.",
        )
    else:
        compile_step = VerificationStep(
            command="# py_compile: no core/*.py in scope — verify changed modules manually",
            description="No concrete scope target; confirm core module compiles without errors.",
        )
    return PremortomRisk(
        id="R1",
        description="core/*.py change may require Master_Blueprint.md synchronization.",
        category="blueprint_sync",
        verification=[
            compile_step,
            VerificationStep(
                command="grep -n '<module>' Master_Blueprint.md",
                description="Blueprint §3 section updated for changed module.",
            ),
            VerificationStep(
                command="# Blueprint commit check deferred to FINALIZE (P2 artifact tracking handles this)",
                description="Master_Blueprint.md is listed in plan artifacts and will be committed in FINALIZE.",
            ),
        ],
    )


def _detect_packaging_risk(scope: list[str], risk_hints: list[str]) -> PremortomRisk | None:
    """New core module or CLI entry may be missing from af.spec hiddenimports."""
    all_items = scope + risk_hints
    if not (_any_match(_CORE_PY_RE, all_items) or _any_match(_CLI_ENTRY_RE, all_items)):
        return None
    return PremortomRisk(
        id="R2",
        description="New core module or CLI entry may be missing from af.spec hiddenimports.",
        category="packaging",
        verification=[
            VerificationStep(
                command="grep 'hiddenimports' af.spec",
                description="af.spec hiddenimports includes new module.",
            ),
            VerificationStep(
                command="python run_factory_cli.py --help",
                description="CLI entry point loads without import errors.",
            ),
        ],
    )


def _detect_workspace_risk(scope: list[str], risk_hints: list[str]) -> PremortomRisk | None:
    """Dogfood or worktree execution may pollute the current workspace."""
    if not _any_match(_DOGFOOD_RE, scope + risk_hints):
        return None
    return PremortomRisk(
        id="R3",
        description="Dogfood or worktree execution may pollute the current workspace.",
        category="workspace",
        verification=[
            VerificationStep(
                command="git status --short",
                description="No unexpected dirty files outside allowed runtime/worktree paths.",
            ),
            VerificationStep(
                command="python scripts/test_gap_analyzer.py --workspace .",
                description="Runtime state isolation checks pass.",
            ),
        ],
    )


def _detect_destructive_risk(approval_policy: str, constraints: list[str]) -> PremortomRisk | None:
    """Destructive operations require explicit approval enforcement."""
    combined = approval_policy + " " + " ".join(constraints)
    if not _DESTRUCTIVE_RE.search(combined):
        return None
    return PremortomRisk(
        id="R4",
        description="Destructive operations present; approval policy must be enforced.",
        category="approval",
        verification=[
            VerificationStep(
                command="grep -rn 'require_human\\|approval_policy' core/",
                description="Approval gate is wired into the execution path.",
            ),
        ],
    )


def _detect_existing_pattern_risk(
    research_findings: list[dict],
    scope: list[str],
) -> PremortomRisk | None:
    """Existing code patterns found in research that overlap with scope files.

    R10 fires when at least one research finding path is also in the implementation
    scope — the new code must extend those files consistently.
    """
    finding_paths = {f.get("path", "") for f in research_findings if f.get("path")}
    overlap = sorted(finding_paths & set(scope))
    if not overlap:
        return None
    paths_str = " ".join(shlex.quote(p) for p in overlap)
    return PremortomRisk(
        id="R10",
        description=f"Existing code patterns found in scope: {', '.join(overlap)}. New implementation must extend consistently.",
        category="pattern_consistency",
        verification=[
            VerificationStep(
                command=f"python -m py_compile {paths_str}",
                description="Scope files still compile after modification.",
            ),
            VerificationStep(
                command=f"# Review patterns in {paths_str} before implementing",
                description="New code follows naming and style conventions in existing scope files.",
            ),
        ],
    )


def _detect_scope_file_risk(scope: list[str]) -> list[PremortomRisk]:
    """Detect scope file paths that do not exist on disk (e.g. typo paths).

    Returns a single R11 risk listing all missing paths, or an empty list if
    scope is empty or every path exists.
    """
    if not scope:
        return []
    missing = [f for f in scope if not os.path.exists(f)]
    if not missing:
        return []
    missing_str = ", ".join(missing)
    return [PremortomRisk(
        id="R11",
        description=f"Scope file(s) not found on disk: {missing_str}. Possible typo in path.",
        category="scope_file",
        verification=[
            VerificationStep(
                command=f"# Verify paths: {missing_str}",
                description="Confirm scope paths exist or correct typos before implementation.",
            ),
        ],
    )]


_BACKTICK_FUNC_RE = re.compile(r"`(\w+)\(\)`")


def _detect_duplicate_function_risk(intent: str, scope: list[str]) -> PremortomRisk | None:
    """Backtick-named functions in intent that already exist in scope .py files are R13."""
    func_names = _BACKTICK_FUNC_RE.findall(intent)
    if not func_names:
        return None
    duplicates: list[tuple[str, str]] = []
    for path in scope:
        if not path.endswith(".py"):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
        except OSError:
            continue
        for name in func_names:
            if re.search(rf"^def {re.escape(name)}\b", content, re.MULTILINE):
                duplicates.append((name, path))
    if not duplicates:
        return None
    desc_parts = ", ".join(f"`{name}` in {path}" for name, path in duplicates)
    return PremortomRisk(
        id="R13",
        description=f"Function(s) named in intent already exist in scope: {desc_parts}.",
        category="duplicate_function",
        verification=[
            VerificationStep(
                command=f"# Review existing definitions: {desc_parts}",
                description="Confirm intent is to overwrite/extend, not accidentally duplicate.",
            ),
        ],
    )


def _detect_stale_test_risk(scope: list[str]) -> PremortomRisk | None:
    """Scope .py files with no corresponding tests/test_<stem>.py are R12.

    Skips files whose basename already starts with 'test_' (they are tests).
    """
    stale = []
    for path in scope:
        if not path.endswith(".py"):
            continue
        basename = os.path.basename(path)
        if basename.startswith("test_"):
            continue
        stem = os.path.splitext(basename)[0]
        test_path = os.path.join("tests", f"test_{stem}.py")
        if not os.path.exists(test_path):
            stale.append(path)
    if not stale:
        return None
    stale_str = ", ".join(stale)
    return PremortomRisk(
        id="R12",
        description=f"No test file found for scope file(s): {stale_str}.",
        category="stale_test",
        verification=[
            VerificationStep(
                command=f"# Add or verify tests for: {stale_str}",
                description="Ensure tests/test_<stem>.py exists for each scope .py file.",
            ),
        ],
    )


def _detect_conflicting_import_risk(intent: str, scope: list[str]) -> PremortomRisk | None:
    """Backtick-named functions in intent that are already imported in scope .py files are R14."""
    func_names = _BACKTICK_FUNC_RE.findall(intent)
    if not func_names:
        return None
    conflicts: list[tuple[str, str]] = []
    for path in scope:
        if not path.endswith(".py"):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
        except OSError:
            continue
        for name in func_names:
            direct = re.search(rf"^import\s+{re.escape(name)}\b", content, re.MULTILINE)
            from_import = re.search(
                rf"^from\s+\S+\s+import\s+[^\n]*\b{re.escape(name)}\b",
                content,
                re.MULTILINE,
            )
            if direct or from_import:
                conflicts.append((name, path))
    if not conflicts:
        return None
    desc_parts = ", ".join(f"`{name}` in {path}" for name, path in conflicts)
    return PremortomRisk(
        id="R14",
        description=f"Function name(s) in intent conflict with existing imports in scope: {desc_parts}.",
        category="conflicting_import",
        verification=[
            VerificationStep(
                command=f"# Review import conflicts: {desc_parts}",
                description="Rename the new function or remove the conflicting import to avoid shadowing.",
            ),
        ],
    )


_LONG_FUNCTION_THRESHOLD = 50  # lines


def _detect_long_function_risk(scope: list[str]) -> list[PremortomRisk]:
    """Scope .py files containing functions longer than the threshold are R15.

    Each qualifying (function, file) pair becomes a separate entry in the
    returned risk's description.  Returns an empty list if nothing trips the
    threshold.
    """
    findings: list[tuple[str, str, int]] = []  # (func_name, path, line_count)
    for path in scope:
        if not path.endswith(".py"):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                source = fh.read()
            tree = ast.parse(source, filename=path)
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            end_line = getattr(node, "end_lineno", None)
            if end_line is None:
                continue
            length = end_line - node.lineno + 1
            if length > _LONG_FUNCTION_THRESHOLD:
                findings.append((node.name, path, length))
    if not findings:
        return []
    desc_parts = ", ".join(
        f"`{name}` in {path} ({lines} lines)" for name, path, lines in findings
    )
    return [
        PremortomRisk(
            id="R15",
            description=f"Scope contains function(s) exceeding {_LONG_FUNCTION_THRESHOLD} lines: {desc_parts}.",
            category="long_function",
            verification=[
                VerificationStep(
                    command=f"# Review long functions: {desc_parts}",
                    description=(
                        "Consider splitting functions above the threshold before adding more code."
                    ),
                ),
            ],
        )
    ]


_COMPLEXITY_THRESHOLD = 10


def _detect_complexity_risk(scope: list[str]) -> list[PremortomRisk]:
    """Scope .py files containing functions with cyclomatic-style complexity > threshold are R16.

    Complexity = 1 + count of branching nodes (If, For, While, ExceptHandler,
    BoolOp extra values, comprehension ifs) within each function body.
    Returns an empty list if nothing trips the threshold.
    """
    findings: list[tuple[str, str, int]] = []  # (func_name, path, complexity)
    for path in scope:
        if not path.endswith(".py"):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                source = fh.read()
            tree = ast.parse(source, filename=path)
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            complexity = 1
            # Use an explicit DFS stack that prunes nested FunctionDef subtrees.
            # ast.walk() flattens the entire subtree, so a plain `continue` on a
            # nested FunctionDef node skips that node but still yields all of its
            # descendants, double-counting their branches in the outer function's
            # complexity.  The stack-based traversal below never enqueues children
            # of a nested FunctionDef, so inner branches are excluded entirely.
            stack = list(ast.iter_child_nodes(node))
            while stack:
                child = stack.pop()
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Nested function — do not descend; it is counted separately
                    # when ast.walk(tree) visits it as its own top-level node.
                    continue
                if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                    complexity += 1
                elif isinstance(child, ast.BoolOp):
                    complexity += len(child.values) - 1
                elif isinstance(child, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
                    for generator in child.generators:
                        complexity += len(generator.ifs)
                stack.extend(ast.iter_child_nodes(child))
            if complexity > _COMPLEXITY_THRESHOLD:
                findings.append((node.name, path, complexity))
    if not findings:
        return []
    desc_parts = "; ".join(
        f"`{name}` in {path} (complexity {n})" for name, path, n in findings
    )
    return [
        PremortomRisk(
            id="R16",
            description=f"Complex function(s) in scope: {desc_parts}. Consider refactoring before extending.",
            category="complexity",
            verification=[
                VerificationStep(
                    command=shlex.join(["grep", "-n", f"def {name}", path]),
                    description=f"Locate `{name}` in {path} for refactoring consideration.",
                )
                for name, path, _ in findings
            ],
        )
    ]


def _detect_assumption_risks(assumptions: list[dict], start: int = 5) -> list[PremortomRisk]:
    """Low-confidence assumptions become explicit risks (R5, R6, …).

    *start* is the first ID number to use — callers can pass a higher value to
    guarantee uniqueness when other fixed risks occupy lower IDs.
    """
    risks: list[PremortomRisk] = []
    counter = start
    for a in assumptions:
        if str(a.get("confidence", "")).lower() in ("low", "unknown", ""):
            stmt = str(a.get("statement") or a.get("id") or "unknown assumption")
            risks.append(PremortomRisk(
                id=f"R{counter}",
                description=f"Low-confidence assumption: {stmt}",
                category="assumption",
                verification=[
                    VerificationStep(
                        command="# Validate assumption before proceeding",
                        description=f"Confirm or refute: {stmt}",
                    ),
                ],
            ))
            counter += 1
    return risks


def _detect_gap_risks(gaps: list[str], start: int = 20) -> list[PremortomRisk]:
    """Unanswered research questions become explicit risks (R20, R21, …).

    *start* is the first ID number to use — callers can pass a higher value
    to guarantee uniqueness when assumption risks have consumed R5…R(start-1).
    """
    risks: list[PremortomRisk] = []
    counter = start
    for gap in gaps:
        risks.append(PremortomRisk(
            id=f"R{counter}",
            description=f"Unanswered research question: {gap}",
            category="research_gap",
            verification=[
                VerificationStep(
                    command="# Resolve gap before implementation",
                    description=f"Find or generate evidence for: {gap}",
                ),
            ],
        ))
        counter += 1
    return risks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_premortem(spec: CompiledSpec) -> PremortomResult:
    """Produce a PremortomResult from a CompiledSpec.

    Detectors fire when their trigger condition matches scope, risk_hints,
    constraints, approval_policy, assumptions, or gaps.
    """
    risks: list[PremortomRisk] = []

    r = _detect_blueprint_sync_risk(spec.scope, spec.risk_hints)
    if r:
        risks.append(r)

    r = _detect_packaging_risk(spec.scope, spec.risk_hints)
    if r:
        risks.append(r)

    r = _detect_workspace_risk(spec.scope, spec.risk_hints)
    if r:
        risks.append(r)

    r = _detect_destructive_risk(spec.approval_policy, spec.constraints)
    if r:
        risks.append(r)

    r = _detect_existing_pattern_risk(spec.research_findings, spec.scope)
    if r:
        risks.append(r)

    # R11=scope_file, R12=stale_test, R13=duplicate_function, R14=conflicting_import,
    # R15=long_function; R16=complexity; assumptions start at R17.
    risks.extend(_detect_scope_file_risk(spec.scope))
    r = _detect_stale_test_risk(spec.scope)
    if r:
        risks.append(r)
    r = _detect_duplicate_function_risk(spec.intent, spec.scope)
    if r:
        risks.append(r)
    r = _detect_conflicting_import_risk(spec.intent, spec.scope)
    if r:
        risks.append(r)
    risks.extend(_detect_long_function_risk(spec.scope))
    risks.extend(_detect_complexity_risk(spec.scope))
    assumption_risks = _detect_assumption_risks(spec.assumptions, start=17)
    risks.extend(assumption_risks)
    gap_start = max(22, 17 + len(assumption_risks))
    risks.extend(_detect_gap_risks(spec.gaps, start=gap_start))

    return PremortomResult(risks=risks, spec_intent=spec.intent)
