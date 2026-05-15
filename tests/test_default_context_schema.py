"""F8 회귀 테스트 — default context schema sanity.

Round 4 dogfooding에서 발견된 차단성 마찰:
체크인된 `projects/default/context_schema.yaml`과 bootstrap 템플릿
`core/projects/default/context_schema.yaml`에 리터럴 `missing_key`가
required_keys에 박혀 있었음 → `agent_runner.py:945`에서 빌드된 ctx
(`agent`, `data_dir`, `artifacts_dir` 보유)와 매칭되지 않아 validation 실패.

P4.5x fix: 두 YAML에서 sentinel 제거. 본 테스트는 회귀 방지.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


DEFAULT_SCHEMA_PATHS = [
    REPO_ROOT / "core" / "projects" / "default" / "context_schema.yaml",
    REPO_ROOT / "projects" / "default" / "context_schema.yaml",
]


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


class TestDefaultSchemaNoSentinel:
    def test_bootstrap_template_no_missing_key(self):
        schema = _load(DEFAULT_SCHEMA_PATHS[0])
        reqs = schema.get("required_keys") or []
        assert "missing_key" not in reqs, (
            "Bootstrap template still contains 'missing_key' sentinel — "
            "would cause every fresh default project to fail context validation."
        )

    def test_default_project_no_missing_key(self):
        schema = _load(DEFAULT_SCHEMA_PATHS[1])
        reqs = schema.get("required_keys") or []
        assert "missing_key" not in reqs, (
            "projects/default/context_schema.yaml still contains 'missing_key'."
        )

    def test_canonical_required_keys_match_runner_ctx(self):
        # agent_runner.py:945 builds ctx with exactly these keys.
        # bootstrap 템플릿이 이들만 요구해야 함.
        schema = _load(DEFAULT_SCHEMA_PATHS[0])
        reqs = set(schema.get("required_keys") or [])
        expected = {"agent", "data_dir", "artifacts_dir"}
        assert expected.issubset(reqs), (
            f"bootstrap schema missing canonical keys; have={reqs} expected⊇{expected}"
        )


class TestSchemaValidatesCanonicalCtx:
    """validate_context_with_schema가 agent_runner의 ctx로 통과하는지 회귀 검증."""

    def test_default_schema_accepts_runner_ctx(self, tmp_path, monkeypatch):
        # validate_context_with_schema는 CONTEXT_SCHEMA_PATH를 직접 읽는다.
        # 기본 default project 환경을 흉내내기 위해 PROJECT_ROOT/AGENT_PROJECT_ROOT
        # 우회 대신 monkeypatch로 config_paths.CONTEXT_SCHEMA_PATH를 default 템플릿
        # 위치로 가리키고 호출한다.
        from core import config_paths
        from core.dashboard import validate_context_with_schema

        monkeypatch.setattr(
            config_paths,
            "CONTEXT_SCHEMA_PATH",
            str(DEFAULT_SCHEMA_PATHS[0]),
            raising=True,
        )

        # agent_runner.py:945의 ctx 구조 재현
        ctx = {
            "agent": {"name": "test", "role_spec": "General"},
            "data_dir": str(tmp_path / "data"),
            "artifacts_dir": str(tmp_path / "artifacts"),
            "workspace": str(tmp_path),
            "project_id": "default",
            "task_input": "test task",
            "task_id": "test_id",
        }

        ok, msg = validate_context_with_schema(ctx)
        assert ok, f"canonical runner ctx failed default schema validation: {msg}"
