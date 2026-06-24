"""scripts/codebase_symbols.py — 코드베이스 심볼 추출기 (read-only AST).

주어진 디렉터리의 Python 파일을 표준 ``ast`` 모듈로 분석해 각 모듈의
top-level 클래스·함수 이름을 추출하고 symbols.md 마크다운 문자열로 렌더링한다.

원본 코드는 절대 수정하지 않는다 — 파일은 읽기만 한다.

공개 계약:
- ``extract_symbols(source)`` — 단일 소스 문자열 → ``{"classes": [...], "functions": [...]}``
- ``collect_symbols(directory)`` — 디렉터리 재귀 walk → posix 상대경로 → 심볼 dict
- ``build(directory)`` — collect + render → symbols.md 마크다운 문자열

Usage:
    python scripts/codebase_symbols.py [디렉터리]
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
import tokenize
from pathlib import Path

_EXCLUDED_DIR_NAMES = frozenset(
    {
        ".af_runtime",
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "venv",
    }
)

_CS_TYPE_RE = re.compile(
    r"^\s*(?:\[[^\]]+\]\s*)*"
    r"(?:(?:public|private|protected|internal|static|abstract|sealed|partial|new)\s+)*"
    r"(?:class|interface|struct|enum|record(?:\s+class|\s+struct)?)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
_CS_METHOD_RE = re.compile(
    r"^\s*(?:\[[^\]]+\]\s*)*"
    r"(?:(?:public|private|protected|internal|static|virtual|override|async|sealed|new|extern|unsafe|partial)\s+)+"
    r"(?!(?:class|interface|struct|enum|record)\b)(?:[A-Za-z_][A-Za-z0-9_<>,\[\].?]*|void)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*"
    r"(?:<[^>{};=]*>)?\s*\(",
    re.MULTILINE,
)
_CS_NON_METHOD_NAMES = frozenset(
    {"if", "for", "foreach", "while", "switch", "catch", "using", "lock", "return", "new"}
)


def _is_excluded(path: Path, root: Path) -> bool:
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        return True
    return any(part in _EXCLUDED_DIR_NAMES for part in rel_parts)


def extract_symbols(source: str) -> dict:
    """단일 소스 문자열을 파싱해 top-level 심볼을 추출한다.

    클래스 메서드와 중첩 함수는 제외하고, 모듈 최상위에 정의된
    클래스·함수(async 포함)만 반환한다.

    파싱 불가(SyntaxError) 시 빈 결과를 반환한다.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {"classes": [], "functions": []}

    classes: list[str] = []
    functions: list[str] = []
    for node in tree.body:  # 모듈 최상위 노드만 — 중첩은 보지 않는다
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
    return {"classes": classes, "functions": functions}


def extract_csharp_symbols(source: str) -> dict:
    """Return C# type and method names using conservative declaration patterns."""
    classes = list(dict.fromkeys(_CS_TYPE_RE.findall(source)))
    functions = [
        name for name in _CS_METHOD_RE.findall(source)
        if name not in _CS_NON_METHOD_NAMES
    ]
    return {"classes": classes, "functions": list(dict.fromkeys(functions))}


def _extract_path_symbols(path: Path) -> dict:
    if path.suffix == ".py":
        try:
            with tokenize.open(path) as f:
                source = f.read()
        except (OSError, SyntaxError, UnicodeDecodeError):
            source = ""
        return extract_symbols(source)
    if path.suffix == ".cs":
        try:
            source = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                source = ""
        except OSError:
            source = ""
        return extract_csharp_symbols(source)
    return {"classes": [], "functions": []}


def _git_tracked_candidates(root: Path) -> list[Path] | None:
    """git repo 안이면 추적되는 ``.py``/``.cs`` 파일 경로 목록을 반환한다.

    repo 가 아니거나 git 미설치/오류면 ``None``(→ rglob 폴백). 추적 파일이
    0건이면 빈 리스트가 아니라 ``None`` 으로 폴백 신호를 준다(빈-추적 repo·
    untracked-only 디렉터리가 빈 결과로 죽지 않도록).

    rglob 가 작업트리 전체를 훑으면 untracked 잡파일(dogfood 산출물 등)까지
    수집돼 symbols.md 가 PC마다 달라진다. 추적 파일만 대상으로 해 산출을
    커밋된 소스의 결정적 함수로 만든다(크로스-PC 결정성).
    """
    try:
        probe = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=10,
        )
        if probe.returncode != 0 or probe.stdout.strip() != "true":
            return None
        listed = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--", "*.py", "*.cs"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if listed.returncode != 0:
        return None
    rels = [r for r in listed.stdout.split("\0") if r]
    if not rels:
        return None
    return [root / r for r in rels]


def collect_symbols(directory) -> dict:
    """디렉터리의 ``.py``/``.cs`` 파일을 분석해 posix 상대경로 → 심볼 dict 매핑을 반환한다.

    git repo 안이면 **추적 파일만** 대상으로 한다(untracked 잡파일 배제 →
    크로스-PC 결정성). 비-git 디렉터리(외부 프로젝트)는 재귀 rglob walk 로
    폴백한다. 파싱 불가 파일은 건너뛰지 않고 빈 심볼로 수집한다(크래시 방지).
    키는 OS 무관 posix 상대경로다.
    """
    root = Path(directory)
    result: dict[str, dict] = {}
    tracked = _git_tracked_candidates(root)
    if tracked is not None:
        candidates = sorted(set(tracked))
    else:
        candidates = sorted(
            p for suffix in ("*.py", "*.cs")
            for p in root.rglob(suffix)
        )
    for path in candidates:
        if not path.is_file():
            continue
        if _is_excluded(path, root):
            continue
        rel = path.relative_to(root).as_posix()  # 백슬래시 금지 (Windows 결정성)
        result[rel] = _extract_path_symbols(path)
    return result


def render(symbols: dict) -> str:
    """심볼 매핑을 symbols.md 마크다운 문자열로 렌더링한다 (결정적)."""
    lines = ["# Codebase Symbols", ""]
    for rel in sorted(symbols):
        entry = symbols[rel]
        lines.append(f"## `{rel}`")
        lines.append("")
        classes = entry.get("classes", [])
        functions = entry.get("functions", [])
        if classes:
            lines.append("**Classes:**")
            lines.extend(f"- `{name}`" for name in classes)
            lines.append("")
        if functions:
            lines.append("**Functions:**")
            lines.extend(f"- `{name}`" for name in functions)
            lines.append("")
        if not classes and not functions:
            lines.append("_(no top-level symbols)_")
            lines.append("")
    return "\n".join(lines) + "\n"


def build(directory) -> str:
    """collect + render — symbols.md 마크다운 문자열을 반환한다."""
    return render(collect_symbols(directory))


def main(argv: list[str]) -> int:
    directory = argv[1] if len(argv) > 1 else "."
    sys.stdout.write(build(directory))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
