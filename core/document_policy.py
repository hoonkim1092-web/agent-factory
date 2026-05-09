"""문서 품질 정책 — 금지 토큰 스캔 및 입력 계약 정의."""
from __future__ import annotations

import re

FORBIDDEN_TOKENS: list[str] = [
    "(edit required)",
    "(auto-generate needed)",
    "TODO: ",
]

# 입력 계약: 문서 유형별로 우선 참조하는 brief 키
INPUT_CONTRACT: dict[str, list[str]] = {
    "plan": ["deliverables", "outcomes", "metrics", "goal", "background_context"],
    "spec": ["user_stories", "user_flows", "io_contracts", "data_model", "constraints"],
    "design": ["components", "flows", "architecture_style", "tech_stack", "modules"],
}


COMPLETION_CRITERIA: dict[str, object] = {
    "artifact_files_exist": True,
    "forbidden_tokens_absent": FORBIDDEN_TOKENS,
    "e2e_command_exit_code": 0,
    "verification_report_verdict_not": "BLOCK",
}


def scan_forbidden_tokens(text: str, exempt: bool = False) -> list[str]:
    """텍스트에서 금지 토큰 목록을 반환한다.

    exempt=True이면 스캔을 건너뛰고 빈 리스트를 반환한다
    (frontmatter qa_exempt_forbidden_tokens: true 문서에 사용).
    """
    if exempt:
        return []
    found: list[str] = []
    for token in FORBIDDEN_TOKENS:
        if token in text:
            found.append(token)
    return found


def parse_frontmatter_exempt(text: str) -> bool:
    """문서 첫머리 YAML frontmatter에서 qa_exempt_forbidden_tokens 플래그를 읽는다."""
    if not text.startswith("---"):
        return False
    end = text.find("\n---", 3)
    if end == -1:
        return False
    frontmatter = text[3:end]
    return bool(re.search(r"^\s*qa_exempt_forbidden_tokens\s*:\s*true\s*$", frontmatter, re.MULTILINE))


def jaccard_similarity(a: str, b: str) -> float:
    """두 문자열 섹션의 Jaccard 유사도를 반환한다.

    토큰화: 소문자 변환 → 비알파벳/숫자/한글 문자 공백 치환 → 공백 분리.
    """
    def tokenize(s: str) -> set[str]:
        s = s.lower()
        s = re.sub(r"[^a-z0-9가-힣]+", " ", s)
        return {t for t in s.split() if t}

    set_a = tokenize(a)
    set_b = tokenize(b)
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)
