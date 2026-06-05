"""
tests/test_coding_conventions.py
==================================
코딩 컨벤션 강제 정적 검사.

CLAUDE.md 필수 규칙 두 가지를 자동으로 검출한다:

1. 타입 SSOT — 같은 이름의 dataclass/TypedDict/Protocol을 여러 파일에 재정의 금지.
2. 절대경로 하드코딩 금지 — open/Path/os.path.* 등 파일 조작 함수 인자에
   /Users/, /home/, C:\\, /root/ 같은 절대경로 리터럴 전달 금지.
"""
from __future__ import annotations

import ast
import glob
import os
import re
from collections import defaultdict
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# 경로 설정
# ─────────────────────────────────────────────────────────────

_ROOT = Path(__file__).parent.parent
_CORE_GLOB = str(_ROOT / "core" / "**" / "*.py")
_SCRIPTS_GLOB = str(_ROOT / "scripts" / "*.py")


def _iter_py_files(*globs: str):
    for pattern in globs:
        yield from sorted(glob.glob(pattern, recursive=True))


# ─────────────────────────────────────────────────────────────
# Rule 1: 타입 SSOT — 중복 타입 이름 금지
# ─────────────────────────────────────────────────────────────

# 기존 코드에서 도메인이 달라 정당하게 공존하는 grandfathered 예외 목록.
# 새 예외를 추가하려면 사용자 승인 필요.
KNOWN_TYPE_DUPLICATES: frozenset[str] = frozenset({
    "RouteDecision",      # express_router(레거시·미사용) + right_sized_router(활성)
    "LedgerEntry",        # evolution_ledger + control/run_ledger (도메인 상이)
    "VerificationResult", # cross_verification + research_verifier (도메인 상이)
    "StrategyLedger",     # memory_system/strategy_ledger + ise_strategy_ledger (도메인 상이)
})


def _is_type_def(node: ast.ClassDef) -> bool:
    """dataclass 데코레이터 또는 TypedDict/Protocol/NamedTuple 상속 여부 판정."""
    for deco in node.decorator_list:
        deco_name = ""
        if isinstance(deco, ast.Name):
            deco_name = deco.id
        elif isinstance(deco, ast.Call) and isinstance(deco.func, ast.Name):
            deco_name = deco.func.id
        elif isinstance(deco, ast.Attribute):
            deco_name = deco.attr
        if deco_name == "dataclass":
            return True
    for base in node.bases:
        base_name = ""
        if isinstance(base, ast.Name):
            base_name = base.id
        elif isinstance(base, ast.Attribute):
            base_name = base.attr
        if base_name in ("TypedDict", "Protocol", "NamedTuple"):
            return True
    return False


def _collect_type_defs(filepath: str) -> list[tuple[str, int]]:
    """파일 내 타입 정의 (클래스명, 라인번호) 목록 반환."""
    try:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return []
    return [
        (node.name, node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and _is_type_def(node)
    ]


def test_no_duplicate_type_names():
    """같은 이름의 타입이 여러 파일에 재정의되지 않아야 한다.

    KNOWN_TYPE_DUPLICATES에 없는 중복이 발견되면 FAIL.
    기존 예외(grandfathered) 목록에 추가하려면 사용자 승인 필요.
    """
    name_to_files: dict[str, list[str]] = defaultdict(list)

    for filepath in _iter_py_files(_CORE_GLOB):
        rel = os.path.relpath(filepath, str(_ROOT))
        for name, _line in _collect_type_defs(filepath):
            name_to_files[name].append(rel)

    violations = {}
    for name, files in name_to_files.items():
        if len(files) > 1 and name not in KNOWN_TYPE_DUPLICATES:
            violations[name] = files

    assert not violations, (
        "타입 SSOT 위반 — 동일 타입 이름이 여러 파일에 재정의됨:\n"
        + "\n".join(
            f"  {name}: " + ", ".join(files)
            for name, files in sorted(violations.items())
        )
        + "\n\n해결: 한 파일에서만 선언하고 나머지는 import. "
        "부득이한 예외는 KNOWN_TYPE_DUPLICATES에 등록(사용자 승인 필요)."
    )


# ─────────────────────────────────────────────────────────────
# Rule 2: 절대경로 하드코딩 금지
# ─────────────────────────────────────────────────────────────

_ABS_PATH_RE = re.compile(r"^(/Users/|/home/|/root/|/opt/|C:\\\\|C:/)", re.IGNORECASE)

# 파일 조작 관련 함수 이름 집합 (attribute name 기준)
_PATH_FUNC_NAMES: frozenset[str] = frozenset({
    "open",
    "Path",
    "join",       # os.path.join
    "exists",     # os.path.exists
    "isfile",     # os.path.isfile
    "isdir",      # os.path.isdir
    "abspath",    # os.path.abspath
    "realpath",   # os.path.realpath
    "makedirs",   # os.makedirs
    "mkdir",      # os.mkdir / Path.mkdir
    "listdir",    # os.listdir
    "rmdir",      # os.rmdir
    "remove",     # os.remove
    "unlink",     # Path.unlink
    "rename",     # os.rename
    "copy",       # shutil.copy
    "copyfile",   # shutil.copyfile
    "move",       # shutil.move
    "rmtree",     # shutil.rmtree
})


def _func_name(call_node: ast.Call) -> str:
    """Call 노드에서 함수 이름 추출 (속성 접근이면 마지막 attr)."""
    func = call_node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _collect_abspath_violations(filepath: str) -> list[tuple[int, str]]:
    """파일 조작 함수 인자에 절대경로 리터럴이 있는 (라인번호, 경로값) 목록 반환."""
    try:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return []

    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _func_name(node) not in _PATH_FUNC_NAMES:
            continue
        # 위치 인자 + 키워드 인자 전부 검사
        args = list(node.args) + [kw.value for kw in node.keywords]
        for arg in args:
            if (
                isinstance(arg, ast.Constant)
                and isinstance(arg.value, str)
                and _ABS_PATH_RE.match(arg.value)
            ):
                violations.append((arg.lineno, arg.value))

    return violations


def test_no_hardcoded_abspath():
    """파일 조작 함수 인자에 절대경로 리터럴을 사용하지 않아야 한다.

    검사 대상: core/**/*.py, scripts/*.py
    패턴: /Users/, /home/, /root/, /opt/, C:\\, C:/
    """
    all_violations: list[str] = []

    for filepath in _iter_py_files(_CORE_GLOB, _SCRIPTS_GLOB):
        rel = os.path.relpath(filepath, str(_ROOT))
        for lineno, path_val in _collect_abspath_violations(filepath):
            all_violations.append(f"  {rel}:{lineno}  →  {path_val!r}")

    assert not all_violations, (
        "절대경로 하드코딩 금지 위반:\n"
        + "\n".join(all_violations)
        + "\n\n해결: os.getcwd(), Path(__file__).parent, 환경변수, 파라미터로 교체."
    )
