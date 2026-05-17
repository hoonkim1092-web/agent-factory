"""
tests/test_agent_worker.py — agent_worker.py atomic write + corrupt-result 시나리오 검증
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile


def _write_task(tmp_dir: str, task: dict) -> str:
    path = os.path.join(tmp_dir, "task.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(task, fh)
    return path


def _run_worker(task_path: str, result_path: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "core/agent_worker.py", "--task-file", task_path, "--result-file", result_path],
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_worker_writes_result_atomically(tmp_path):
    """result.json이 원자적으로 기록되고 유효한 JSON이어야 한다."""
    task = {
        "project_root": "",
        "role": "test_role",
        "agent_data": {},
        "subtask": "noop",
        "run_id": "run_test",
        "workspace": str(tmp_path),
        "runtime_workspace": str(tmp_path),
        "task_id": "t1",
        "broker_address": "",
    }
    task_path = _write_task(str(tmp_path), task)
    result_path = str(tmp_path / "result.json")

    # AgentRunner 임포트 실패 환경에서도 worker_exception 결과로 종료해야 한다
    proc = _run_worker(task_path, result_path)

    assert os.path.exists(result_path), "result.json이 생성돼야 한다"
    with open(result_path, encoding="utf-8") as fh:
        data = json.load(fh)  # 유효한 JSON이어야 한다
    assert "ok" in data


def test_worker_bad_task_json(tmp_path):
    """task.json이 corrupt이면 sys.exit(1)로 종료해야 한다."""
    task_path = str(tmp_path / "task.json")
    with open(task_path, "w") as fh:
        fh.write("{invalid json}")
    result_path = str(tmp_path / "result.json")

    proc = _run_worker(task_path, result_path)

    assert proc.returncode == 1


def test_worker_missing_tmp_files_cleanup(tmp_path):
    """원자적 write 이후 .tmp 잔여 파일이 없어야 한다."""
    task = {
        "project_root": "",
        "role": "test_role",
        "agent_data": {},
        "subtask": "noop",
        "run_id": "run_test",
        "workspace": str(tmp_path),
        "runtime_workspace": str(tmp_path),
        "task_id": "t2",
        "broker_address": "",
    }
    task_path = _write_task(str(tmp_path), task)
    result_path = str(tmp_path / "result.json")

    _run_worker(task_path, result_path)

    tmp_files = [f for f in os.listdir(tmp_path) if f.endswith(".tmp")]
    assert tmp_files == [], f".tmp 잔여 파일이 있어서는 안 된다: {tmp_files}"
