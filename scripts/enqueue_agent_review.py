#!/usr/bin/env python3
"""
scripts/enqueue_agent_review.py
=================================
PostToolUse hook에서 호출.
.py 파일 편집 시 교차검증 대기 큐에 추가한다.

마커 파일: .af_review_queue/pending_agent_review.json
- 편집된 파일 목록을 누적
- check_pending_review.py가 일정 시간 후 확인

항상 exit 0 — hook 차단 방지.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time

MARKER_DIR = ".af_review_queue"
MARKER_PATH = os.path.join(MARKER_DIR, "pending_agent_review.json")

# 교차검증 대상 파일 패턴
_REVIEW_PREFIXES = ("core/",)
_REVIEW_EXACT = ("model_utils.py", "run_factory_cli.py")


def _is_review_target(filepath: str) -> bool:
    if not filepath.endswith(".py"):
        return False
    for prefix in _REVIEW_PREFIXES:
        if filepath.startswith(prefix):
            return True
    basename = os.path.basename(filepath)
    return basename in _REVIEW_EXACT


def _detect_workspace() -> str:
    import subprocess
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return os.getcwd()


def main() -> None:
    if len(sys.argv) < 2:
        return

    filepath = sys.argv[1]

    # 절대경로 → 상대경로 변환
    workspace = _detect_workspace()
    try:
        rel = os.path.relpath(os.path.abspath(filepath), workspace)
    except ValueError:
        rel = filepath
    rel = rel.replace("\\", "/")

    if not _is_review_target(rel):
        return

    marker = os.path.join(workspace, MARKER_PATH)
    marker_dir = os.path.join(workspace, MARKER_DIR)

    # 기존 마커 읽기
    data = {"files": [], "created_at": time.time()}
    if os.path.exists(marker):
        try:
            with open(marker, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"files": [], "created_at": time.time()}

    # 파일 추가 (중복 방지)
    if rel not in data.get("files", []):
        data.setdefault("files", []).append(rel)
        # created_at은 첫 파일 추가 시점 유지, 새 파일 추가 시 갱신
        data["updated_at"] = time.time()

    # 저장 (atomic write — tempfile + os.replace)
    try:
        os.makedirs(marker_dir, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix=".pending_", dir=marker_dir, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, marker)
        except Exception:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            raise
    except Exception:
        pass


if __name__ == "__main__":
    main()
