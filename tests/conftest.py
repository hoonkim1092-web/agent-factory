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
# F16: 글로벌 skills/registry.yaml 오염 차단 (BASE_DIR/SKILLS_DIR 은 conftest 가
# 격리할 수 없으므로 F12 hardening 가드를 활용). RegistryManager._write_registry
# + PreflightEvaluator._update_registry_status 양쪽에서 _env_flag truthy 체크.
os.environ.setdefault("AF_DISABLE_REGISTRY_WRITE", "1")


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


@pytest.fixture(autouse=True)
def _af_isolate_skill_registry_writes(monkeypatch):
    """F16: skills/registry.yaml 글로벌 오염 차단 (매 테스트 setup).

    모듈 top 의 `os.environ.setdefault("AF_DISABLE_REGISTRY_WRITE", "1")` 만으로는
    부족함: TestEnvFlagConvention 같은 테스트가 finally 에서 `os.environ.pop(...)`
    직접 호출 → 후속 테스트(test_project_scope 등) 가 env 미설정 상태에서
    RegistryManager 인스턴스화 → `_normalize_registry_paths → _write_registry`
    가 글로벌 registry 에 leak. monkeypatch.setenv 가 매 테스트 setup 마다
    env 를 강제 set 하고 teardown 에서 원상태로 restore 한다.
    """
    monkeypatch.setenv("AF_DISABLE_REGISTRY_WRITE", "1")


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
