"""STAGE 2 S2-3 검증 — 증류 배선(session_adapter 발화점 → vault).

설계 §5 STAGE2 산출물 / §7 INV-K1·K3·K4 / NEXT_STEPS S2-3:
  - run_bridge 가 수집한 raw events 를 반환 (이중 cursor 회피), CLI stdout 엔 제외
  - _distill_to_vault: events → KnowledgeNote 를 repo_root/docs/wiki/knowledge 에 best-effort 기록
  - 두 발화점 모두 동일 코드로 산출 (INV-K4 멀티프로바이더):
      · :691 handle_hook_event SessionEnd (claude/gemini hook 경로)
      · :583 finalize_cli_session codex_cli (codex 경로 — hook 미경유)
  - 증류 실패가 세션 수명주기 hook 을 죽이지 않음 (best-effort)
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import core.providers.session_adapter as sa
from core.providers.session_adapter import (
    _distill_to_vault,
    finalize_cli_session,
    handle_hook_event,
)

_SAMPLE = {
    "summary": "RSE 라우터 CoT 채택",
    "decisions": ["임계 0.85→0.82"],
    "rejections": ["스킬화 기각"],
    "patterns": ["빈-scope 변동성 프롬프트로 해결"],
}


class _FakeLLM:
    def __init__(self, payload: dict):
        self._payload = payload

    def generate_json(self, prompt: str, output_schema=None) -> dict:
        return self._payload


def _patch_distill_llm(monkeypatch, payload: dict = _SAMPLE) -> None:
    monkeypatch.setattr(
        "core.knowledge.distill._get_distill_llm",
        lambda: _FakeLLM(payload),
    )


def _vault_notes(repo_root: Path) -> list[Path]:
    return list((repo_root / "docs" / "wiki" / "knowledge" / "session").glob("*.md"))


_EVENTS = [
    {"file": "sess.jsonl", "line": 3, "timestamp": "", "text": "[assistant] 커밋 abc1234 에서 INV-K5 결정"},
]


# ---------------------------------------------------------------------------
# _distill_to_vault 헬퍼 (공유 코드)
# ---------------------------------------------------------------------------
def test_distill_to_vault_writes_session_note(tmp_path, monkeypatch):
    _patch_distill_llm(monkeypatch)
    repo_root = tmp_path / "repo"

    _distill_to_vault(_EVENTS, repo_root, "claude_cli")

    notes = _vault_notes(repo_root)
    assert len(notes) == 1
    body = notes[0].read_text(encoding="utf-8")
    # 정밀참조 verbatim 보존 (INV-K5) — 결정론 추출이라 LLM 무관하게 본문에 박힘.
    assert "abc1234" in body
    assert "INV-K5" in body


def test_distill_to_vault_empty_events_noop(tmp_path, monkeypatch):
    _patch_distill_llm(monkeypatch)
    repo_root = tmp_path / "repo"

    _distill_to_vault([], repo_root, "claude_cli")

    # 빈 events → vault 디렉터리조차 만들지 않음.
    assert not (repo_root / "docs").exists()


def test_distill_to_vault_swallows_distill_failure(tmp_path, monkeypatch):
    """증류 실패가 hook 을 죽이면 안 됨 — 예외를 삼키고 노트 0건."""
    def _boom(*args, **kwargs):
        raise RuntimeError("distill exploded")

    monkeypatch.setattr("core.knowledge.distill.distill_session", _boom)
    repo_root = tmp_path / "repo"

    # 예외가 전파되지 않아야 한다.
    _distill_to_vault(_EVENTS, repo_root, "claude_cli")

    assert _vault_notes(repo_root) == []


# ---------------------------------------------------------------------------
# :691 handle_hook_event SessionEnd (claude/gemini hook 경로, production caller)
# ---------------------------------------------------------------------------
def test_handle_hook_event_distills_on_session_end(tmp_path, monkeypatch):
    _patch_distill_llm(monkeypatch)
    workspace = tmp_path / "ws"
    workspace.mkdir(parents=True, exist_ok=True)
    repo_root = tmp_path / "repo"
    transcript = tmp_path / "sessions" / "claude" / "t.jsonl"
    transcript.parent.mkdir(parents=True, exist_ok=True)
    transcript.write_text("{}\n", encoding="utf-8")

    captured: dict = {}

    def fake_run_bridge(provider_id, repo_root, sessions_root=None, bootstrap_limit=120, max_write=240):
        return {"ok": True, "written": 1, "events": list(_EVENTS)}

    monkeypatch.setattr("core.providers.session_adapter.run_bridge", fake_run_bridge)

    handle_hook_event(
        "claude",
        {
            "hook_event_name": "SessionEnd",
            "session_id": "s1",
            "transcript_path": str(transcript),
        },
        workspace=str(workspace),
        run_id="run_1",
        repo_root=str(repo_root),
    )

    # 노트는 workspace 가 아니라 repo_root vault 에 안착 (INV-K1).
    assert len(_vault_notes(repo_root)) == 1
    assert not (workspace / "docs" / "wiki" / "knowledge").exists()

    # events 는 state.bridge_result 에 누출되지 않음 (pop 으로 비대화 방지).
    state_path = workspace / ".af_runtime" / "cli_sessions" / "claude_cli_run_1.json"
    assert state_path.exists(), "state file should be written"
    blob = json.loads(state_path.read_text(encoding="utf-8"))
    assert blob["bridge_result"]["ok"] is True
    assert "events" not in blob["bridge_result"]


def test_handle_hook_event_no_distill_on_non_end_event(tmp_path, monkeypatch):
    _patch_distill_llm(monkeypatch)
    workspace = tmp_path / "ws"
    workspace.mkdir(parents=True, exist_ok=True)
    repo_root = tmp_path / "repo"

    def fake_run_bridge(*a, **k):
        raise AssertionError("run_bridge must not fire on UserPromptSubmit")

    monkeypatch.setattr("core.providers.session_adapter.run_bridge", fake_run_bridge)

    handle_hook_event(
        "claude",
        {"hook_event_name": "UserPromptSubmit", "session_id": "s1", "message": "hi"},
        workspace=str(workspace),
        run_id="run_1",
        repo_root=str(repo_root),
    )

    assert _vault_notes(repo_root) == []


# ---------------------------------------------------------------------------
# :583 finalize_cli_session codex_cli (codex 경로 — hook 미경유, INV-K4 parity)
# ---------------------------------------------------------------------------
def test_finalize_cli_session_distills_for_codex(tmp_path, monkeypatch):
    _patch_distill_llm(monkeypatch)
    workspace = tmp_path / "ws"
    workspace.mkdir(parents=True, exist_ok=True)
    repo_root = tmp_path / "repo"
    state_path = tmp_path / "state.json"
    state_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr("core.providers.session_adapter._repo_root", lambda: repo_root)

    def fake_run_bridge(provider_id, repo_root, sessions_root=None, bootstrap_limit=120, max_write=240):
        return {"ok": True, "written": 1, "events": list(_EVENTS)}

    monkeypatch.setattr("core.providers.session_adapter.run_bridge", fake_run_bridge)

    request = SimpleNamespace(provider_id="codex_cli", workspace=str(workspace))
    prepared = {"state_path": str(state_path), "env": {}}
    finalize_cli_session(request, prepared, {"ok": True})

    assert len(_vault_notes(repo_root)) == 1
    blob = json.loads(state_path.read_text(encoding="utf-8"))
    assert "events" not in (blob.get("bridge_result") or {})
