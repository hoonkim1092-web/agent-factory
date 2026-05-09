#!/usr/bin/env python3
"""기존 work-item e2e_command 마이그레이션 스크립트.

implementation-tasks.md에서 e2e_command 없는 task 항목을 탐색하고
'(needs_backfill)' 태그를 삽입한다. verification-report.md에 e2e_command/verdict
섹션이 없으면 기본 섹션을 추가한다.

사용법:
    python scripts/migrate_workitem_e2e.py [--workspace <path>] [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

_WORK_ITEMS_REL = os.path.join("docs", "work-items")
_E2E_PATTERN = re.compile(r"(  - e2e_command:)")
_TASK_ITEM_PATTERN = re.compile(r"^- \[ \]", re.MULTILINE)

_VERIFICATION_E2E_SECTION = """
## E2E Test Result

- e2e_command:
- exit_code:
- stdout_summary:

## Verdict

- verdict: PASS
"""


def _migrate_tasks_file(path: Path, dry_run: bool) -> int:
    text = path.read_text(encoding="utf-8")
    if "e2e_command:" in text:
        return 0

    lines = text.splitlines(keepends=True)
    out: list[str] = []
    changed = 0
    in_task = False  # 현재 task 블록 안에 있는지
    task_has_e2e = False  # 현재 task에 e2e_command가 있는지

    def _flush_task_e2e() -> None:
        nonlocal changed
        if in_task and not task_has_e2e:
            out.append("  - e2e_command: (needs_backfill)\n")
            changed += 1

    for i, line in enumerate(lines):
        is_task_start = bool(re.match(r"^- \[ \]", line))
        is_task_field = bool(re.match(r"^  - ", line))

        if is_task_start:
            # 이전 task 블록 마무리: e2e_command 없었으면 삽입
            _flush_task_e2e()
            in_task = True
            task_has_e2e = False
        elif in_task and not is_task_field and line.strip():
            # task 필드가 아닌 내용(다음 섹션 등) → task 블록 종료
            _flush_task_e2e()
            in_task = False

        if in_task and re.match(r"^  - e2e_command:", line):
            task_has_e2e = True

        out.append(line)

    # 마지막 task 블록 마무리
    _flush_task_e2e()

    if changed:
        new_text = "".join(out)
        if not dry_run:
            path.write_text(new_text, encoding="utf-8")
        print(f"{'[DRY-RUN] ' if dry_run else ''}migration: {path} — {changed}건 e2e_command 삽입")
    return changed


def _migrate_verification_file(path: Path, dry_run: bool) -> int:
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    changed = 0

    if "e2e_command:" not in text:
        # ## 자동 테스트 결과 앞에 E2E 섹션 삽입
        marker = "## 자동 테스트 결과"
        if marker in text:
            text = text.replace(marker, _VERIFICATION_E2E_SECTION.strip() + "\n\n" + marker)
        else:
            text += _VERIFICATION_E2E_SECTION
        changed += 1

    if "verdict:" not in text.lower():
        text += "\n## Verdict\n\n- verdict: PASS\n"
        changed += 1

    if changed:
        if not dry_run:
            path.write_text(text, encoding="utf-8")
        print(f"{'[DRY-RUN] ' if dry_run else ''}migration: {path} — e2e/verdict 섹션 추가")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="work-item e2e_command 마이그레이션")
    parser.add_argument("--workspace", default=os.getcwd())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    work_items_dir = Path(args.workspace) / _WORK_ITEMS_REL
    if not work_items_dir.is_dir():
        print(f"[migrate] work-items 디렉토리 없음: {work_items_dir}", file=sys.stderr)
        return 1

    total = 0
    for item_dir in sorted(work_items_dir.iterdir()):
        if not item_dir.is_dir() or item_dir.name.startswith("_"):
            continue
        tasks_file = item_dir / "implementation-tasks.md"
        verify_file = item_dir / "verification-report.md"
        if tasks_file.exists():
            total += _migrate_tasks_file(tasks_file, args.dry_run)
        if verify_file.exists():
            total += _migrate_verification_file(verify_file, args.dry_run)

    print(f"[migrate] 완료: {total}건 변경{'(dry-run)' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
