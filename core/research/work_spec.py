from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class WorkSpec:
    artifact_type: str = ""          # "game", "webapp", "backend_service", ...
    domain: str = ""                 # "poker", "chess", "ecommerce", ...
    capabilities: list[str] = field(default_factory=list)   # ["multiplayer", "realtime", ...]
    risk_areas: list[str] = field(default_factory=list)     # ["anti_cheat", "randomness", ...]
    constraints: list[str] = field(default_factory=list)    # ["8_players", ...]
    domain_hints: list[str] = field(default_factory=list)   # regex hint results (advisory only)

    def to_dict(self) -> dict:
        return {
            "artifact_type": self.artifact_type,
            "domain": self.domain,
            "capabilities": self.capabilities,
            "risk_areas": self.risk_areas,
            "constraints": self.constraints,
            "domain_hints": self.domain_hints,
        }


class WorkSpecExtractor:
    """사용자 요청 → WorkSpec 구조화.

    LLM 기반 추출을 사용한다. regex domain_hints는 overlay 선택 힌트로만 전달되며
    WorkSpec의 최종 값을 결정하지 않는다.
    """

    _PROMPT = """\
다음 사용자 요청을 분석해 JSON으로 응답하세요.

요청: {request}

출력 스키마 (JSON만 출력, 설명 없음):
{{
  "artifact_type": "game|webapp|backend_service|data_pipeline|mobile_app|cli_tool|library|other",
  "domain": "도메인명 또는 빈 문자열 (예: poker, chess, ecommerce, blog, chat)",
  "capabilities": ["필요한 기술 역량 목록 (예: multiplayer, realtime, auth, payments, search)"],
  "risk_areas": ["주요 위험 영역 (예: anti_cheat, randomness, data_consistency, security)"],
  "constraints": ["명시적 제약 (예: 8_players, mobile_first, offline_support)"],
  "domain_hints": []
}}

규칙:
- artifact_type은 반드시 위 목록 중 하나
- capabilities는 구현에 필요한 기술 역량 (2~8개)
- risk_areas는 이 프로젝트에서 특히 신중해야 할 영역 (1~5개)
- constraints는 사용자가 명시한 제약만 (없으면 [])
- domain_hints는 항상 []로 두세요 (시스템이 채웁니다)
"""

    def extract(self, request: str, domain_hints: list[str] | None = None) -> WorkSpec:
        from core.requirement_llm import execute_requirement_prompt
        import json

        prompt = self._PROMPT.format(request=request)
        try:
            result = execute_requirement_prompt(prompt)
            if not result.get("ok"):
                raise RuntimeError("work_spec_llm_unavailable")
            text = str(result.get("text") or "")
            data = json.loads(_extract_json(text))
            caps = data.get("capabilities") or []
            if isinstance(caps, str):
                caps = [caps]
            spec = WorkSpec(
                artifact_type=str(data.get("artifact_type") or "other").strip(),
                domain=str(data.get("domain") or "").strip(),
                capabilities=[str(c) for c in caps],
                risk_areas=[str(r) for r in (data.get("risk_areas") or [])],
                constraints=[str(c) for c in (data.get("constraints") or [])],
                domain_hints=list(domain_hints or []),
            )
        except Exception:
            spec = WorkSpec(domain_hints=list(domain_hints or []))
        return spec


def _extract_json(text: str) -> str:
    """LLM 응답에서 JSON 블록 추출."""
    import re
    m = re.search(r"\{[\s\S]*\}", text)
    return m.group(0) if m else text
