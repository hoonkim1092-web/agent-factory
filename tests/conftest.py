import os
import shutil
import uuid
from pathlib import Path

import pytest


os.environ.setdefault("GOOGLE_API_KEY", "test-key")
_TEST_RUNTIME_ROOT = (Path("tests") / "_tmp" / "runtime_project").resolve()
os.environ.setdefault("AGENT_PROJECT_ID", "test_runtime")
os.environ.setdefault("AGENT_PROJECT_ROOT", str(_TEST_RUNTIME_ROOT))
# RunEventStore 기본 경로 — 테스트에서 리포 루트 runs/ 오염 방지
os.environ.setdefault("AF_CHECKPOINT_DIR", str((Path("tests") / "_tmp" / "runs").resolve()))


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_runtime_root():
    try:
        yield
    finally:
        shutil.rmtree(_TEST_RUNTIME_ROOT, ignore_errors=True)
        shutil.rmtree(_TEST_RUNTIME_ROOT.parent, ignore_errors=True)


@pytest.fixture(autouse=True)
def _reset_run_event_store_singleton():
    """각 테스트 전후로 get_default_store() 싱글톤을 리셋해 테스트 간 오염 방지."""
    import core.events.run_event as _rev
    _rev._default_store = None
    yield
    _rev._default_store = None


@pytest.fixture
def tmp_path():
    root = Path(__file__).parent / "_tmp"  # conftest 위치 기준 — CWD 독립
    root.mkdir(parents=True, exist_ok=True)
    base = root / f"af-test-{uuid.uuid4().hex[:8]}"
    base.mkdir(parents=True, exist_ok=True)
    try:
        yield base.resolve()
    finally:
        shutil.rmtree(base, ignore_errors=True)
