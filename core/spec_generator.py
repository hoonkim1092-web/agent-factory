"""P2 C2+C3+C4: Domain spec generator — poker 도메인 5종 명세 + ADR + traceability 생성."""

SPEC_FILENAMES: dict[str, str] = {
    "rules": "rules-spec.md",
    "state_machine": "state-machine.md",
    "server_arch": "server-architecture.md",
    "event_protocol": "event-protocol.md",
    "client_view": "client-view.md",
}

_POKER_SPEC_DEFS = [
    (
        "rules",
        "Game Rules Specification",
        lambda task, brief: f"""Generate a Game Rules Specification for: {task}

Include all of the following sections in markdown:
1. Hand Rankings (Royal Flush → High Card, kicker rules)
2. Blind Structure (small blind, big blind, button rotation, blinds increase if tournament)
3. Betting Rules (No-Limit / Pot-Limit / Fixed-Limit options, 4 rounds: preflop/flop/turn/river)
4. All-In Handling (call amount calculation, all-in detection)
5. Side Pot Calculation (main pot, side pot split when player is all-in)
6. Showdown (tie resolution, kicker comparison, split pot)

Context from project brief:
- Constraints: {brief.get("constraints", [])}
- Tech stack: {brief.get("tech_stack", [])}

Return markdown only. Use ## for sections, include concrete rules as bullet lists.""",
    ),
    (
        "state_machine",
        "Game State Machine",
        lambda task, brief: f"""Generate a Game State Machine specification for: {task}

Include all of the following in markdown:
1. State list (e.g. WAITING, PREFLOP, FLOP, TURN, RIVER, SHOWDOWN, POT_DISTRIBUTION, GAME_OVER)
2. Transition table (from_state → event → to_state)
3. Entry/exit actions per state
4. Player-level sub-states (ACTIVE, FOLDED, ALL_IN, SITTING_OUT)

Context: {brief.get("goal", "")}

Return markdown only. Use ## for sections, include a state transition table.""",
    ),
    (
        "server_arch",
        "Server Architecture Specification",
        lambda task, brief: f"""Generate a Server Architecture Specification for a multiplayer poker server: {task}

Include all of the following in markdown:
1. Server Responsibilities (authoritative game state, validation of all player actions)
2. Room/Session Management (max players, reconnection handling)
3. Core Game Loop (event processing, state mutation, broadcast)
4. Server-Authoritative Events list (deal, raise, fold, call, check, showdown)
5. Cheat Prevention (why clients never hold canonical state)

Tech stack context: {brief.get("tech_stack", [])}

Return markdown only. Use ## for sections.""",
    ),
    (
        "event_protocol",
        "Event Protocol Specification",
        lambda task, brief: f"""Generate an Event Protocol Specification for a multiplayer poker game: {task}

Include all of the following in markdown:
1. Client → Server events (JOIN_ROOM, FOLD, CALL, RAISE, CHECK, ALL_IN) with payload schema
2. Server → Client events (GAME_START, DEAL_HAND, BETTING_ROUND_START, PLAYER_ACTION, POT_UPDATE, SHOWDOWN_RESULT, GAME_END) with payload schema
3. Hidden state rule: server MUST NOT send hole cards of other players
4. Error events (INVALID_ACTION, CONNECTION_ERROR)

Return markdown only. Use ## for sections, use code blocks for JSON schemas.""",
    ),
    (
        "client_view",
        "Client View Specification",
        lambda task, brief: f"""Generate a Client View (Hidden State) Specification for a multiplayer poker game: {task}

Include all of the following in markdown:
1. Information Asymmetry Model (what each player sees vs. what is hidden)
2. Own hand: always visible to owner only
3. Other players' hole cards: hidden until showdown
4. Community cards: visible to all after dealt
5. Pot amounts, bet amounts: visible to all
6. Implementation contract: server sends player-specific views, never global state

Return markdown only. Use ## for sections.""",
    ),
]


class SpecGenerator:
    """포커 도메인 5종 명세를 LLM으로 생성한다."""

    def generate(self, brief: dict) -> dict[str, str]:
        domain = (brief.get("research_plan") or {}).get("domain", "")
        if domain != "poker":
            return {}
        task_input = str(brief.get("original_request") or brief.get("goal") or "")
        results: dict[str, str] = {}
        for key, title, prompt_fn in _POKER_SPEC_DEFS:
            results[key] = self._call_llm(prompt_fn(task_input, brief), title)
        return results

    def _call_llm(self, prompt: str, title: str) -> str:
        from core.requirement_llm import execute_document_prompt
        try:
            result = execute_document_prompt(prompt)
            if result.get("ok"):
                text = str(result.get("text") or "").strip()
                if text:
                    return text
        except Exception:
            pass
        return f"# {title}\n\n(spec generation unavailable)\n"


def _call_llm_raw(prompt: str) -> str:
    """LLM 호출 성공 시 텍스트, 실패 시 "" 반환 (fallback 판단은 호출자 책임)."""
    from core.requirement_llm import execute_document_prompt
    try:
        result = execute_document_prompt(prompt)
        if result.get("ok"):
            text = str(result.get("text") or "").strip()
            if text:
                return text
    except Exception:
        pass
    return ""


class AdrGenerator:
    """P2 C3: 도메인 결정 ADR을 LLM으로 생성한다."""

    def generate(self, brief: dict, claims: list[dict], sources: list[dict]) -> str:
        domain = (brief.get("research_plan") or {}).get("domain", "")
        if not domain:
            return ""
        slug = str(brief.get("original_request") or brief.get("goal") or domain)[:60]
        date_str = __import__("datetime").date.today().isoformat()

        evidence_block = self._format_evidence(claims, sources)
        prompt = f"""Generate an Architecture Decision Record (ADR) in markdown for the following domain: {domain}
Project: {slug}

Evidence collected:
{evidence_block}

Produce the ADR in exactly this structure:
# Decision: Rule baseline selection for {domain}

- **Date**: {date_str}
- **Status**: Accepted

## Decision
<one sentence — which ruleset/standard was selected as baseline>

## Alternatives Considered
1. <alternative 1> — <one-line pro/con>
2. <alternative 2> — <one-line pro/con>
3. <alternative 3> — <one-line pro/con>

## Rationale
- <bullet: why the chosen baseline was selected, grounded in evidence>
- <bullet: specific reference to source coverage or authority>

## Evidence References
<list each claim_id and its source_id>

Return markdown only."""
        llm_result = _call_llm_raw(prompt)
        return llm_result if llm_result else self._fallback_adr(domain, date_str, claims, sources)

    def _format_evidence(self, claims: list[dict], sources: list[dict]) -> str:
        lines = []
        for s in sources[:5]:
            lines.append(f"  Source {s.get('source_id','?')}: {s.get('title') or s.get('url','')}")
        for c in claims[:8]:
            lines.append(f"  Claim {c.get('claim_id','?')} ({c.get('source_id','?')}): {c.get('claim','')[:120]}")
        return "\n".join(lines) if lines else "(no evidence)"

    def _fallback_adr(self, domain: str, date_str: str, claims: list[dict], sources: list[dict]) -> str:
        evidence_refs = "\n".join(
            f"- claim_id: {c.get('claim_id','?')} (source_id: {c.get('source_id','?')})"
            for c in claims[:6]
        ) or "- (no claims recorded)"
        return f"""# Decision: Rule baseline selection for {domain}

- **Date**: {date_str}
- **Status**: Accepted

## Decision
Use the most authoritative available ruleset as the baseline for {domain}.

## Alternatives Considered
1. Official tournament rules — authoritative but complex
2. Informal house rules — accessible but non-standard
3. Training/strategy guides — strategy focus, not rule authority

## Rationale
- Selected based on source authority and coverage breadth
- Sources referenced: {len(sources)}
- Claims collected: {len(claims)}

## Evidence References
{evidence_refs}
"""


class TraceabilityGenerator:
    """P2 C4: claim_id ↔ spec_section ↔ task_id 매핑 traceability.md 생성."""

    _SPEC_KEYWORDS: dict[str, list[str]] = {
        "rules-spec.md": ["rule", "hand", "blind", "bet", "all-in", "side pot", "showdown", "ranking"],
        "state-machine.md": ["state", "transition", "preflop", "flop", "turn", "river", "waiting"],
        "server-architecture.md": ["server", "session", "room", "broadcast", "authoritative", "cheat"],
        "event-protocol.md": ["event", "protocol", "payload", "client", "message", "join", "fold", "call"],
        "client-view.md": ["view", "hidden", "asymmetry", "hole card", "community", "pot"],
    }

    _TASK_KEYWORDS: dict[str, list[str]] = {
        "rule": ["rule", "hand", "ranking", "blind", "bet"],
        "state": ["state", "machine", "transition", "phase"],
        "server": ["server", "backend", "room", "session", "auth"],
        "protocol": ["protocol", "event", "message", "websocket", "api"],
        "ui": ["ui", "view", "client", "frontend", "display", "render"],
    }

    def generate(self, brief: dict, claims: list[dict], task_board: dict) -> str:
        if not claims:
            return ""
        slug = str(brief.get("original_request") or brief.get("goal") or "")[:60]
        tasks = [t for t in (task_board.get("tasks") or []) if isinstance(t, dict)]
        rows = []
        for claim in claims:
            cid = claim.get("claim_id", "?")
            sid = claim.get("source_id", "?")
            claim_text = str(claim.get("claim") or "").lower()
            spec_sec = self._match_spec(claim_text)
            task_id = self._match_task(claim_text, tasks)
            rows.append((cid, sid, spec_sec, task_id))

        table_lines = ["| claim_id | source_id | spec_section | task_id |",
                       "|----------|-----------|--------------|---------|"]
        for cid, sid, spec_sec, tid in rows:
            table_lines.append(f"| {cid} | {sid} | {spec_sec} | {tid} |")

        return f"# Traceability — {slug}\n\n" + "\n".join(table_lines) + "\n"

    def _match_spec(self, claim_text: str) -> str:
        best, best_score = "rules-spec.md", 0
        for filename, keywords in self._SPEC_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in claim_text)
            if score > best_score:
                best, best_score = filename, score
        return best

    def _match_task(self, claim_text: str, tasks: list[dict]) -> str:
        for task in tasks:
            desc = str(task.get("description") or task.get("name") or "").lower()
            if any(kw in claim_text and kw in desc for kw_list in self._TASK_KEYWORDS.values() for kw in kw_list):
                return str(task.get("task_id") or "")
        return tasks[0].get("task_id", "T001") if tasks else "T001"
