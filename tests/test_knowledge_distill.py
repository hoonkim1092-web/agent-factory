"""STAGE 2 검증 — 증류기(distill) + originating_pc 포인터.

설계 §5 STAGE2 / §7 INV-K4·K5 / §9 검증:
  - secret 마스킹(가짜 토큰 주입→마스킹)
  - 정밀참조 verbatim 추출·보존(INV-K5 — LLM paraphrase 로부터 보호)
  - 멀티프로바이더 동일 산출(control_plane_llm SSOT → 렌더 결정론)
  - session_bridge details 에 originating_pc(F3)
"""
from __future__ import annotations

import json
from pathlib import Path

from core.knowledge.distill import (
    distill_session,
    extract_precise_refs,
    mask_secrets,
)
from core.knowledge.note import KnowledgeNote

REPO_ROOT = Path(__file__).resolve().parents[1]


class _FakeLLM:
    """generate_json 이 고정 dict 를 반환하는 가짜 LLM (provider 무관 결정론 검증용)."""

    def __init__(self, payload: dict):
        self._payload = payload
        self.prompts: list[str] = []

    def generate_json(self, prompt: str, output_schema=None) -> dict:
        self.prompts.append(prompt)
        return self._payload


_SAMPLE = {
    "summary": "RSE 라우터 CoT 프롬프트 채택",
    "decisions": ["임계 0.85→0.82", "CoT 프롬프트로 변동성 감소"],
    "rejections": ["스킬화 기각 — control-plane 호출이라 레이어 다름"],
    "patterns": ["빈-scope 변동성은 프롬프트로 해결 가능"],
}


# ---------------------------------------------------------------------------
# secret 마스킹
# ---------------------------------------------------------------------------
def test_mask_secrets_known_prefixes():
    text = "token=sk-ABCD1234EFGH5678IJKL and ghp_abcdefghijklmnopqrstuvwxyz0123456789"
    masked = mask_secrets(text)
    assert "sk-ABCD1234EFGH5678IJKL" not in masked
    assert "ghp_abcdefghijklmnopqrstuvwxyz0123456789" not in masked
    assert "[REDACTED]" in masked


def test_mask_secrets_label_value_keeps_label():
    masked = mask_secrets('api_key = "s3cr3tVALUE12345"')
    assert "s3cr3tVALUE12345" not in masked
    assert "api_key" in masked  # 라벨은 보존
    assert "[REDACTED]" in masked


def test_mask_secrets_hyphenated_modern_keys():
    """sk-proj-/sk-ant- 형태 현대 API 키도 마스킹 (af-critic BLOCK#1)."""
    masked = mask_secrets("use sk-proj-abcdefghijklmnopqrst and sk-ant-api03-abcdefghijklmnop")
    assert "sk-proj-abcdefghijklmnopqrst" not in masked
    assert "sk-ant-api03-abcdefghijklmnop" not in masked


def test_mask_secrets_json_serialized_label():
    """JSON 직렬화 형태 "api_key": "값" 도 마스킹 (af-critic BLOCK#2)."""
    masked = mask_secrets('config: {"api_key": "s3cr3tVALUE12345", "x": 1}')
    assert "s3cr3tVALUE12345" not in masked
    assert "api_key" in masked


def test_mask_secrets_aws_and_bearer():
    masked = mask_secrets("AKIAIOSFODNN7EXAMPLE Bearer abcdefghij1234567890XYZ")
    assert "AKIAIOSFODNN7EXAMPLE" not in masked
    assert "abcdefghij1234567890XYZ" not in masked


def test_mask_secrets_pem_block():
    pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIxxxxx\n-----END RSA PRIVATE KEY-----"
    masked = mask_secrets(pem)
    assert "MIIxxxxx" not in masked
    assert "[REDACTED]" in masked


def test_mask_secrets_preserves_precise_refs():
    """commit/file:line 은 secret 이 아니므로 마스킹되지 않아야 함."""
    text = "fix in note.py:178, commit 0848fc74, INV-K5"
    masked = mask_secrets(text)
    assert "note.py:178" in masked
    assert "0848fc74" in masked
    assert "INV-K5" in masked


# ---------------------------------------------------------------------------
# 정밀참조 verbatim 추출 (INV-K5)
# ---------------------------------------------------------------------------
def test_extract_precise_refs_verbatim_ordered_deduped():
    text = "INV-K5 보고 note.py:178 수정, commit 0848fc74. 다시 INV-K5, note.py:178."
    refs = extract_precise_refs(text)
    assert "INV-K5" in refs
    assert "note.py:178" in refs
    assert "0848fc74" in refs
    # 중복 제거
    assert refs.count("INV-K5") == 1
    assert refs.count("note.py:178") == 1


def test_extract_refs_preserves_path_prefix():
    """경로 prefix 보존 — Windows(\\)·Unix(/) 둘 다 (af-critic WARN#4)."""
    assert "core/knowledge/note.py:178" in extract_precise_refs("fix core/knowledge/note.py:178")
    assert "core\\distill.py:55" in extract_precise_refs("see core\\distill.py:55 here")


def test_extract_refs_hex_requires_digit():
    """숫자 없는 hex 영단어는 commit 으로 오추출 안 함 (af-critic WARN#3)."""
    refs = extract_precise_refs("the deadbeef facade and 0848fc74")
    assert "0848fc74" in refs
    assert "deadbeef" not in refs


# ---------------------------------------------------------------------------
# distill_session
# ---------------------------------------------------------------------------
def test_distill_empty_events_returns_empty():
    assert distill_session([], workspace=str(REPO_ROOT)) == []


def test_distill_produces_session_note_roundtrips():
    events = [
        {"text": "임계 0.85→0.82 결정 (note.py:178, commit 0848fc74, INV-K5)", "file": "x.jsonl", "line": 12},
        {"text": "스킬화는 기각했다", "file": "x.jsonl", "line": 40},
    ]
    llm = _FakeLLM(_SAMPLE)
    notes = distill_session(events, workspace=str(REPO_ROOT), provider_id="claude", llm=llm)
    assert len(notes) == 1
    note = notes[0]
    assert note.type == "session"
    assert "RSE 라우터 CoT" in note.body
    assert "임계 0.85→0.82" in note.body
    assert "스킬화 기각" in note.body
    # round-trip
    assert KnowledgeNote.from_md(note.to_md()) == note


def test_distill_preserves_verbatim_refs_in_body_INV_K5():
    """LLM 이 정밀참조를 누락/변형해도, 본문 정밀참조 섹션엔 verbatim 으로 박힌다."""
    events = [{"text": "수정: note.py:178, commit 0848fc74, INV-K5", "file": "s.jsonl", "line": 3}]
    # LLM payload 는 정밀참조를 전혀 언급 안 함 (paraphrase 위험 시뮬레이션)
    llm = _FakeLLM({"summary": "수정함", "decisions": [], "rejections": [], "patterns": []})
    note = distill_session(events, workspace=str(REPO_ROOT), llm=llm)[0]
    assert "`note.py:178`" in note.body
    assert "`0848fc74`" in note.body
    assert "`INV-K5`" in note.body


def test_distill_masks_secret_in_event_text():
    """이벤트 본문의 토큰이 노트 본문(평문 vault)에 새지 않아야 함."""
    events = [{"text": 'export OPENAI=sk-DEADBEEF1234567890abcd then ran', "file": "s.jsonl", "line": 1}]
    llm = _FakeLLM({"summary": "환경 설정", "decisions": [], "rejections": [], "patterns": []})
    note = distill_session(events, workspace=str(REPO_ROOT), llm=llm)[0]
    assert "sk-DEADBEEF1234567890abcd" not in note.body


def test_distill_multiprovider_identical_body():
    """control_plane_llm SSOT → 같은 LLM 산출이면 provider 무관 본문 동일(INV-K4)."""
    events = [{"text": "결정 X (a1b2c3d)", "file": "s.jsonl", "line": 5}]
    body_a = distill_session(events, workspace=str(REPO_ROOT), provider_id="claude", llm=_FakeLLM(_SAMPLE))[0].body
    body_b = distill_session(events, workspace=str(REPO_ROOT), provider_id="codex", llm=_FakeLLM(_SAMPLE))[0].body
    assert body_a == body_b


def test_distill_llm_failure_graceful():
    """LLM 이 예외/비-dict 반환해도 노트는 생성된다(정밀참조+포인터만으로라도)."""
    class _Boom:
        def generate_json(self, prompt, output_schema=None):
            raise RuntimeError("provider down")

    events = [{"text": "작업함 INV-K5", "file": "s.jsonl", "line": 2}]
    notes = distill_session(events, workspace=str(REPO_ROOT), llm=_Boom())
    assert len(notes) == 1
    assert "`INV-K5`" in notes[0].body


# ---------------------------------------------------------------------------
# S2-2 — session_bridge details.originating_pc (F3)
# ---------------------------------------------------------------------------
def test_write_memory_entries_includes_originating_pc(tmp_path):
    from scripts.session_bridge import get_provider, write_memory_entries

    provider = get_provider("claude")
    events = [{"text": "테스트 결정", "file": "s.jsonl", "line": 7, "timestamp": "2026-06-23T00:00:00Z"}]
    n = write_memory_entries(tmp_path, events, user_key="u", provider=provider)
    assert n == 1
    written = list(tmp_path.glob("*.json"))
    assert len(written) == 1
    record = json.loads(written[0].read_text(encoding="utf-8"))
    assert "originating_pc" in record["details"]
    assert record["details"]["originating_pc"]  # non-empty
