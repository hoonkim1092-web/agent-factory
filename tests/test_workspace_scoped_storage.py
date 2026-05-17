"""
tests/test_workspace_scoped_storage.py — get_storage_for / get_store_for 워크스페이스 격리 검증
"""
from __future__ import annotations

import json
import os

import pytest

from core.checkpoint.canonical import Checkpoint
from core.checkpoint.storage import get_storage_for, _workspace_storage_cache
from core.events.run_event import RunEvent, RunEventType, get_store_for, _workspace_store_cache


# --- CheckpointStorage ---

def test_storage_for_writes_under_workspace(tmp_path):
    """get_storage_for(ws)는 ws/runs/ 아래에 checkpoint를 저장해야 한다."""
    ws = str(tmp_path / "ws_a")
    os.makedirs(ws)
    storage = get_storage_for(ws)

    cp = Checkpoint(run_id="run_001", step_id="s1", idempotency_key="k1",
                    worktree_snapshot={}, next_step_cursor="orchestrate",
                    test_acceptance_results={})
    storage.save(cp)

    expected = os.path.join(ws, "runs", "run_001", "canonical_checkpoint.json")
    assert os.path.exists(expected), f"checkpoint 파일이 없음: {expected}"
    with open(expected) as f:
        data = json.load(f)
    assert data["run_id"] == "run_001"


def test_storage_for_isolated_between_workspaces(tmp_path):
    """서로 다른 workspace는 checkpoint를 공유하지 않아야 한다."""
    ws_a = str(tmp_path / "ws_a")
    ws_b = str(tmp_path / "ws_b")
    os.makedirs(ws_a)
    os.makedirs(ws_b)

    get_storage_for(ws_a).save(Checkpoint(run_id="run_shared", step_id="s1", idempotency_key="k1",
                                           worktree_snapshot={}, next_step_cursor="orchestrate",
                                           test_acceptance_results={}))

    loaded = get_storage_for(ws_b).load("run_shared")
    assert loaded is None, "ws_b가 ws_a의 checkpoint를 읽어서는 안 된다"


def test_storage_for_same_workspace_returns_same_instance(tmp_path):
    """같은 workspace 경로에 대해 동일 인스턴스를 반환해야 한다."""
    ws = str(tmp_path / "ws_c")
    os.makedirs(ws)
    a = get_storage_for(ws)
    b = get_storage_for(ws)
    assert a is b


# --- RunEventStore ---

def test_store_for_writes_under_workspace(tmp_path):
    """get_store_for(ws)는 ws/runs/ 아래에 events.jsonl을 저장해야 한다."""
    ws = str(tmp_path / "ws_ev_a")
    os.makedirs(ws)
    store = get_store_for(ws)

    ev = RunEvent(run_id="run_ev_001", event_type=RunEventType.RUN_STARTED, payload={"x": 1})
    store.append(ev)

    expected = os.path.join(ws, "runs", "run_ev_001", "events.jsonl")
    assert os.path.exists(expected), f"events.jsonl이 없음: {expected}"
    with open(expected) as f:
        line = json.loads(f.readline())
    assert line["run_id"] == "run_ev_001"


def test_store_for_isolated_between_workspaces(tmp_path):
    """서로 다른 workspace는 events를 공유하지 않아야 한다."""
    ws_a = str(tmp_path / "ws_ev_a")
    ws_b = str(tmp_path / "ws_ev_b")
    os.makedirs(ws_a)
    os.makedirs(ws_b)

    ev = RunEvent(run_id="run_shared", event_type=RunEventType.RUN_STARTED, payload={})
    get_store_for(ws_a).append(ev)

    events = get_store_for(ws_b).list_events("run_shared")
    assert events == [], "ws_b가 ws_a의 events를 읽어서는 안 된다"


def test_store_for_same_workspace_returns_same_instance(tmp_path):
    """같은 workspace 경로에 대해 동일 인스턴스를 반환해야 한다."""
    ws = str(tmp_path / "ws_ev_c")
    os.makedirs(ws)
    a = get_store_for(ws)
    b = get_store_for(ws)
    assert a is b
