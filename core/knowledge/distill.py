"""STAGE 2 — 세션 raw events → 증류된 KnowledgeNote (provider-neutral LLM).

설계: docs/2026-06-23-knowledge-library-evolution-design.md §5 STAGE2 / §7 INV-K4·K5 / §12.7

이 모듈은 session_bridge 의 260자 truncate(§2.3)를 대체/보강하는 '증류' 로직이다:
- LLM 호출은 control_plane_llm SSOT 경유 → 어느 프로바이더(claude/codex/gemini)든
  동일 코드 경로 (INV-K4 멀티프로바이더).
- 정밀참조(commit/file:line/INV명)는 LLM 요약에 맡기지 않고 raw 에서 **결정론적
  verbatim 추출**해 노트에 박는다 (INV-K5 — LLM paraphrase 로부터 보호).
- 평문 vault 보호를 위해 입력·출력 양쪽에 secret/token 마스킹 (§5 STAGE2 제약).

배선(session_adapter.py:690 발화점 교체/보강)은 별도 슬라이스 — 이 모듈은 순수 로직.
"""
from __future__ import annotations

import re
import socket
from typing import Any, Protocol

from core.knowledge.note import KnowledgeNote, new_note

# 증류 프롬프트에 넣을 raw 본문 상한 (토큰 폭주 방지). 최근 이벤트 우선.
_MAX_PROMPT_CHARS = 24000
_REDACTED = "[REDACTED]"


# ---------------------------------------------------------------------------
# secret/token 마스킹 (평문 vault 보호)
# ---------------------------------------------------------------------------
# 라벨 기반(api_key=..., token: ...) + 알려진 prefix(sk-/ghp_/xox.-/AKIA/PEM).
# 보수적: commit 해시·file:line 같은 정밀참조는 건드리지 않는다(verbatim 추출 대상).
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    # -----BEGIN ... PRIVATE KEY----- 블록
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
    # OpenAI(sk-/sk-proj-/sk-ant-) / GitHub / Slack / AWS access key 등 알려진 prefix 토큰.
    # sk- 는 하이픈 포함 현대 키(sk-proj-…, sk-ant-api03-…)도 잡도록 하이픈 허용.
    re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9\-]{15,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{16,}", re.IGNORECASE),
    # 라벨=값 형태: (api_key|token|secret|…) [:=] "값". JSON 직렬화("api_key": "값")도
    # 잡도록 라벨/값 사이 선택적 따옴표·공백 허용.
    re.compile(
        r"(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|token|secret|password|passwd|pwd)\b"
        r"(['\"]?\s*[:=]\s*['\"]?)"
        r"([A-Za-z0-9_\-./+]{8,})['\"]?",
    ),
)


def mask_secrets(text: str) -> str:
    """텍스트에서 흔한 secret/token 패턴을 [REDACTED] 로 치환한다.

    라벨=값 패턴은 라벨·구분자는 보존하고 값만 마스킹한다(가독성).
    """
    if not text:
        return text
    result = text
    for pat in _SECRET_PATTERNS:
        if pat.groups >= 3:  # 라벨=값 형태 (라벨/구분자 보존, 값만 마스킹)
            result = pat.sub(lambda m: f"{m.group(1)}{m.group(2)}{_REDACTED}", result)
        else:
            result = pat.sub(_REDACTED, result)
    return result


# ---------------------------------------------------------------------------
# 정밀참조 verbatim 추출 (INV-K5) — LLM 요약에 맡기지 않는다
# ---------------------------------------------------------------------------
_REF_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bINV-[A-Za-z0-9]+\b"),                          # INV-K5, INV-O1 ...
    # 경로 prefix(/ 또는 \\) 보존: core/x.py:5, core\x.py:5, note.py:178
    re.compile(r"(?:[\w.\-]+[/\\])*[\w.\-]+\.[A-Za-z]{1,6}:\d+"),
    # git commit (short/full) — 일반 영단어(deadbeef 등) 오탐 줄이려 숫자 1개 이상 요구
    re.compile(r"\b(?=[0-9a-f]*[0-9])[0-9a-f]{7,40}\b"),
)


def extract_precise_refs(text: str) -> list[str]:
    """raw 에서 commit/file:line/INV명을 verbatim·중복제거 추출 (패턴 그룹 순서: INV→file:line→commit).

    secret 마스킹 후 텍스트에 적용하면 마스킹된 토큰이 commit 으로 오추출되지 않는다.
    """
    seen: set[str] = set()
    refs: list[str] = []
    for pat in _REF_PATTERNS:
        for m in pat.finditer(text):
            ref = m.group(0)
            if ref not in seen:
                seen.add(ref)
                refs.append(ref)
    return refs


# ---------------------------------------------------------------------------
# LLM 증류
# ---------------------------------------------------------------------------
class _LLMLike(Protocol):
    def generate_json(self, prompt: str, output_schema: type | None = ...) -> dict: ...


_distill_llm: _LLMLike | None = None


def _get_distill_llm() -> _LLMLike:
    """control_plane_llm SSOT 지연 싱글턴 (right_sized_router._get_router_llm 패턴)."""
    global _distill_llm
    if _distill_llm is None:
        from core.control_plane_llm import ControlPlaneLLM

        _distill_llm = ControlPlaneLLM()
    return _distill_llm


def _events_text(events: list[dict]) -> str:
    """events 의 text 를 시간순으로 연결 (상한 초과 시 최근 우선)."""
    parts = [str(e.get("text") or "").strip() for e in events]
    joined = "\n\n".join(p for p in parts if p)
    if len(joined) > _MAX_PROMPT_CHARS:
        joined = joined[-_MAX_PROMPT_CHARS:]
    return joined


def build_distill_prompt(masked_text: str, refs: list[str]) -> str:
    """provider-neutral 증류 프롬프트 (CoT). JSON 계약 반환 지시."""
    ref_block = "\n".join(f"- {r}" for r in refs) if refs else "(없음)"
    return (
        "당신은 개발 세션 트랜스크립트에서 '나중에 맥락을 잇는 데 필요한 것'만 증류하는 도구다.\n"
        "raw 대화에서 다음을 추출하라:\n"
        "1) 내린 결정(decisions) — 무엇을·왜\n"
        "2) 기각/포기한 선택(rejections) — 무엇을·왜 안 했나\n"
        "3) 재사용 가능한 패턴/교훈(patterns)\n"
        "4) 한 줄 요약(summary)\n\n"
        "규칙:\n"
        "- 단계별로 먼저 생각한 뒤 JSON 만 출력한다.\n"
        "- 정밀참조(커밋 해시·file:line·INV명)는 절대 요약·변형하지 말고, 언급한다면 원문 그대로 인용하라.\n"
        "- 추측 금지. 트랜스크립트에 없는 내용 지어내지 마라.\n\n"
        f"아래는 트랜스크립트에서 결정론적으로 추출한 정밀참조 목록(verbatim, 변형 금지):\n{ref_block}\n\n"
        "출력 JSON 스키마:\n"
        '{"summary": "한 줄", "decisions": ["..."], "rejections": ["..."], "patterns": ["..."]}\n\n'
        "=== 트랜스크립트 (secret 마스킹됨) ===\n"
        f"{masked_text}\n"
        "=== 끝 ===\n"
    )


def _render_body(data: dict, refs: list[str], pointer: dict[str, Any]) -> str:
    """증류 dict + verbatim refs + raw 포인터 → 노트 본문 마크다운."""

    def _bullets(items: Any) -> str:
        if not isinstance(items, list) or not items:
            return "_(없음)_"
        return "\n".join(f"- {str(it).strip()}" for it in items if str(it).strip())

    summary = str(data.get("summary") or "").strip() or "_(요약 없음)_"
    ref_lines = "\n".join(f"- `{r}`" for r in refs) if refs else "_(없음)_"
    return (
        f"{summary}\n\n"
        f"## 결정 (Decisions)\n{_bullets(data.get('decisions'))}\n\n"
        f"## 기각 (Rejections)\n{_bullets(data.get('rejections'))}\n\n"
        f"## 패턴 (Patterns)\n{_bullets(data.get('patterns'))}\n\n"
        f"## 정밀 참조 (verbatim, INV-K5)\n{ref_lines}\n\n"
        f"## raw 포인터 (§3.3 — 원문은 originating PC 에만)\n"
        f"- originating_pc: {pointer.get('originating_pc', 'unknown')}\n"
        f"- session_file: {pointer.get('session_file', '')}\n"
        f"- lines: {pointer.get('line_start', 0)}-{pointer.get('line_end', 0)}\n"
    )


def _pointer(events: list[dict], source_machine: str) -> dict[str, Any]:
    """raw 포인터 3요소 {originating_pc, session_file, line} (§3.3 / F3)."""
    session_file = ""
    lines: list[int] = []
    for e in events:
        f = str(e.get("file") or "")
        if f:
            session_file = f  # 마지막(최근) 세션 파일
        try:
            lines.append(int(e.get("line") or 0))
        except (TypeError, ValueError):
            continue
    return {
        "originating_pc": source_machine,
        "session_file": session_file,
        "line_start": min(lines) if lines else 0,
        "line_end": max(lines) if lines else 0,
    }


def distill_session(
    events: list[dict],
    *,
    workspace: str = ".",
    provider_id: str = "",
    llm: _LLMLike | None = None,
    title: str | None = None,
) -> list[KnowledgeNote]:
    """세션 raw events → 증류된 KnowledgeNote 목록 (MVP: session 노트 1건).

    - secret 마스킹(입력) → 정밀참조 verbatim 추출 → LLM 증류 → 본문 렌더 →
      secret 마스킹(출력, 방어적) → new_note(자동 스탬프).
    - events 가 비면 [] 반환.
    """
    if not events:
        return []

    masked_text = mask_secrets(_events_text(events))
    if not masked_text.strip():
        return []
    refs = extract_precise_refs(masked_text)

    engine = llm if llm is not None else _get_distill_llm()
    prompt = build_distill_prompt(masked_text, refs)
    try:
        data = engine.generate_json(prompt)
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}

    try:
        machine = socket.gethostname() or "unknown"
    except Exception:
        machine = "unknown"

    pointer = _pointer(events, machine)
    body = mask_secrets(_render_body(data, refs, pointer))

    # title 도 마스킹 (LLM summary → frontmatter + 파일명 slug 로 흐르므로 방어적 일관)
    raw_title = title or (str(data.get("summary") or "").strip()[:60]) or f"세션 증류 — {provider_id or 'unknown'}"
    note_title = mask_secrets(raw_title)
    note = new_note(note_title, body, "session", workspace=workspace)
    return [note]
