#!/usr/bin/env python3
"""plan/spec/design의 Goals 섹션 간 Jaccard 유사도를 측정한다 (GH 기준 ≤ 0.4).

사용법:
    python scripts/measure_goal_overlap.py docs/work-items/<slug>/
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def _extract_goals_section(text: str) -> str:
    m = re.search(r"^##\s+Goals?\s*\n(.*?)(?=^##|\Z)", text, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _tokenize(s: str) -> set[str]:
    s = s.lower()
    s = re.sub(r"[^a-z0-9가-힣]+", " ", s)
    return {t for t in s.split() if t}


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta and not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def main() -> int:
    if len(sys.argv) < 2:
        print("사용법: measure_goal_overlap.py <work-item-dir>")
        return 1

    work_dir = Path(sys.argv[1])
    plan_path = work_dir / "feature-plan.md"
    spec_path = work_dir / "feature-spec.md"
    design_path = work_dir / "implementation-design.md"

    missing = [p for p in (plan_path, spec_path, design_path) if not p.exists()]
    if missing:
        for p in missing:
            print(f"파일 없음: {p}")
        return 1

    plan_goals = _extract_goals_section(plan_path.read_text(encoding="utf-8"))
    spec_goals = _extract_goals_section(spec_path.read_text(encoding="utf-8"))
    design_goals = _extract_goals_section(design_path.read_text(encoding="utf-8"))

    pairs = [
        ("plan vs spec", plan_goals, spec_goals),
        ("plan vs design", plan_goals, design_goals),
        ("spec vs design", spec_goals, design_goals),
    ]

    threshold = 0.4
    fail = False
    for label, a, b in pairs:
        score = _jaccard(a, b)
        status = "PASS" if score <= threshold else "FAIL"
        if status == "FAIL":
            fail = True
        print(f"{status} {label}: Jaccard={score:.3f} (threshold={threshold})")

    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
