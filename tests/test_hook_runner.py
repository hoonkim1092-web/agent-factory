"""tests/test_hook_runner.py — Phase 2 v7 신규.

§5.4 v7 정정: hook_events.log line이 정확히 5 segment로 split되는 split-invariant
회귀 보호. spec prose ("hardcoded payload만 사용") 단언이 미래 caller drift를
falsifiable하게 차단할 수 없으므로 test로 enforce.

회귀 케이스:
- §5.4 caller `warn_only_suppressed` (round_count + agents_present JSON 페이로드)
- §5.5 caller `verdict_fallback` (subagent_type + content snippet 페이로드)
"""
from __future__ import annotations

import importlib
import json
import os
from pathlib import Path

import pytest


@pytest.fixture()
def hook_runner_mod(tmp_path, monkeypatch):
    """hook_runner를 reload하고 _project_root를 tmp_path로 패치."""
    import scripts.hook_runner as m
    importlib.reload(m)
    monkeypatch.setattr(m, "_project_root", lambda: str(tmp_path))
    return m


def _read_log_lines(workspace: Path) -> list[str]:
    log_path = workspace / ".af_review_queue" / "hook_events.log"
    assert log_path.exists(), "hook_events.log 누락"
    return [
        line.rstrip("\n")
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_log_hook_event_split_invariant(hook_runner_mod, tmp_path):
    """hook_events.log line은 정확히 5 segment로 split되어야 한다.

    line format = `f"{ts}|{builtin}|{file}|{exit_code}|{error}\n"`
    payload value에 `|`가 들어가면 split 결과가 깨진다.

    v7 정정 (v6 cross-review #3 valid): spec 단언만으로는 미래 caller drift를
    차단할 수 없음 — test로 enforce.
    """
    # §5.4 caller — warn_only_suppressed
    hook_runner_mod._log_hook_event(
        "warn_only_suppressed",
        "1",
        0,
        error=json.dumps({"agents_present": ["af-test-runner", "af-critic", "af-cross-review"]}),
    )
    # §5.5 caller — verdict_fallback (no-verdict-line case)
    hook_runner_mod._log_hook_event(
        "verdict_fallback",
        "af-cross-review",
        0,
        error=f"no-verdict-line:{'예시 본문 텍스트'!r}",
    )
    # §5.5 caller — verdict_fallback (exception case)
    hook_runner_mod._log_hook_event(
        "verdict_fallback",
        "af-cross-review",
        1,
        error="ImportError(scripts.review_gate) — fallback path",
    )

    lines = _read_log_lines(tmp_path)
    assert len(lines) == 3, f"3 line 예상, 실제 {len(lines)}"

    for idx, line in enumerate(lines):
        segments = line.split("|")
        assert len(segments) == 5, (
            f"line {idx} segment 수가 5가 아님 ({len(segments)}): {line!r}"
        )
        ts, builtin, file_arg, exit_code, error = segments
        assert ts, "timestamp 비어있음"
        assert builtin in ("warn_only_suppressed", "verdict_fallback")
        assert exit_code in ("0", "1")


def test_log_hook_event_split_invariant_with_payload_pipe_documented(hook_runner_mod, tmp_path):
    """문서화 — payload value에 `|` 가 들어가면 segment 수가 5를 초과한다.

    이 테스트는 회귀가 아니라 invariant 위반 검출 시 어떤 일이 발생하는지
    명시적으로 보여준다. 현재 정규 caller는 hardcoded payload만 사용하므로 안전.
    Phase 3+ JSON-only line format 전환 후보 (§10 F10).
    """
    # 의도적으로 `|` 포함 payload — 정규 caller가 이렇게 호출하면 안 됨
    hook_runner_mod._log_hook_event(
        "test_invariant_violation",
        "demo|with|pipe",
        0,
        error="payload|with|pipe",
    )
    lines = _read_log_lines(tmp_path)
    segments = lines[-1].split("|")
    # 5를 초과하면 split이 깨진 것 — 이를 검출해야 함을 spec-level에서 보장
    assert len(segments) > 5, (
        "이 케이스는 invariant 위반을 의도적으로 발생시킴 — "
        "정규 caller는 hardcoded payload만 사용해야 함"
    )
