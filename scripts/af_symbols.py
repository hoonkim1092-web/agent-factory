"""af symbols — 외부 Python 프로젝트의 코드 심볼 인덱스 생성.

주어진 디렉터리를 read-only AST로 분석해 심볼 목록을
``<디렉터리>/.af_index/symbols.md`` 에 쓴다.

새 파싱 로직 없음 — scripts.codebase_symbols.build(directory)를 그대로 재사용한다.

Usage:
    python scripts/af_symbols.py <디렉터리>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_AF_ROOT = Path(__file__).resolve().parent.parent
# codebase_symbols는 scripts/ 내 동위 모듈 — AF root가 sys.path에 있어야 import 가능
if str(_AF_ROOT) not in sys.path:
    sys.path.insert(0, str(_AF_ROOT))

from scripts.codebase_symbols import build  # noqa: E402

_INDEX_DIR_NAME = ".af_index"
_INDEX_FILE_NAME = "symbols.md"


def build_symbols_index(directory) -> Path:
    """디렉터리의 심볼 인덱스를 ``<directory>/.af_index/symbols.md`` 에 쓰고 경로를 반환한다.

    .af_index 디렉터리가 없으면 만든다. 인덱스 내용은 codebase_symbols.build()로
    생성하며, 생성 자신(.af_index/symbols.md)을 심볼로 잡지 않도록 디렉터리 생성보다
    먼저 내용을 계산한다. ``directory`` 는 str 또는 Path 모두 허용한다.
    """
    root = Path(directory)
    content = build(root)  # mkdir 전에 계산 — 자기 자신을 인덱싱하지 않도록
    index_dir = root / _INDEX_DIR_NAME
    index_dir.mkdir(parents=True, exist_ok=True)
    index_path = index_dir / _INDEX_FILE_NAME
    index_path.write_text(content, encoding="utf-8")
    return index_path


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        prog="af symbols",
        description="외부 Python 프로젝트의 코드 심볼 인덱스 생성 (read-only AST)",
    )
    parser.add_argument("path", help="대상 프로젝트 디렉터리 경로")
    args = parser.parse_args(argv)

    root = Path(args.path)
    if not root.is_dir():
        print(f"[af symbols] 디렉터리 없음: {root}", file=sys.stderr)
        return 1

    index_path = build_symbols_index(root)
    print(f"[af symbols] 저장됨: {index_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
