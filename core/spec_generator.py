"""P2 C2: Domain spec generator — poker 도메인 5종 명세 생성."""

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
