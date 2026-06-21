# CoT 프롬프트 변동성 개선 설계

날짜: 2026-06-21  
상태: Draft  
대상 파일: `core/right_sized_router.py`  
관련 측정: `docs/2026-06-21-cot-variability-measurement-results.md`

---

## §1 배경 및 문제

`right_sized_router.py`의 빈-scope 분류 경로(`_classify_empty_scope`)는 LLM에게 task를 보내고
`isolation/required_stages/review_depth/confidence/reason` JSON을 받는 control-plane 호출이다.

### §1.1 현재 증상 (실측 근거)

`_build_empty_scope_prompt`(현재 버전)로 claude_cli를 10회 호출할 때:
- 동일 simple 태스크에서 conf 0.55~0.82 (표준편차 0.108)
- simple README task에서 `['research', 'implement']` stages 반환 → `research ∉ LIGHT_STAGES` → is_light()=False → 잘못된 full 라우팅 (3/5 회)
- 0.85 임계에서 simple task의 light 진입 30% (이상적: 100%)

### §1.2 원인

`control_plane_llm.py:114` CLI 경로에 temperature 제어 불가(claude_cli는 temp 플래그 미노출 = 구조적 한계).  
현재 프롬프트는 "## Rules" 섹션에 규칙만 나열 → LLM이 규칙 적용 순서를 즉흥적으로 결정 → 변동.

---

## §2 해법: CoT 프롬프트 + 임계 하향

### §2.1 CoT 프롬프트 구조

규칙 나열 → "Step 1~4 단계별 추론 후 JSON" 구조로 교체.

```
Step 1 — Leaf check (YES/NO)
Step 2 — Stage necessity (per-stage 명시 기준)
Step 3 — Scope uncertainty
Step 4 — Decision (confidence 배정 기준)
→ JSON 출력
```

**적용 함수**: `_build_empty_scope_prompt` + `_build_prompt` 양쪽.
- `_build_empty_scope_prompt`: 빈-scope 전용, 불확실성 강조 유지
- `_build_prompt`: scope 파일 있는 경우, tier hint 섹션 유지

### §2.2 임계 하향: 0.85 → 0.82

| | claude_cli | codex_cli |
|---|---|---|
| light min (CoT) | 0.920 | 0.860 |
| full max (CoT) | 0.750 | 0.720 |
| 임계 0.85 margin | 0.07 / 미충족 | **0.01** ⚠️ |
| **임계 0.82 margin** | **0.10** / 0.07 | **0.04** / 0.10 |

codex light min=0.86이 0.85 임계에서 margin=0.01로 위험. 0.82로 하향 시 양 프로바이더 모두 충분한 safety margin.

**변경 상수**: `_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD: float = 0.85` → `0.82`

---

## §3 불변식

- **INV-A**: scope 있는 경로(`_build_prompt`, `changed_files` 비어있지 않을 때) 동작 무변경.  
  `is_light()` 조건에서 `ROUTE_MARKER_SCOPE_UNCERTAIN` 없으면 `_LIGHT_CONFIDENCE_THRESHOLD=0.70` 그대로 사용.
- **INV-B**: `_validate_raw`/`_fallback_decision` 로직 미변경.
- **INV-C**: 모든 단계에서 LLM 실패 → fallback_decision (기존 보장 유지).
- **INV-D**: `_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD`는 단일 SSOT — `is_light()`에서만 참조.

---

## §4 구현 명세

### §4.1 `_build_empty_scope_prompt` CoT화

현재:
```python
return f"""...
## Rules
- Pure leaf implementation (add a single function, no API/contract changes):
    required_stages should be [{light_list}] only.
- If design, review, or cross-review is genuinely needed, include them.
- If the scope is unclear or the task involves multiple files/systems, set confidence < 0.5.
- Tier hint is unavailable — rely on task semantics only.
"""
```

변경 후: `## Step-by-step reasoning` + `## Output` + `## Additional rules` 구조.

```python
return f"""...
## Step-by-step reasoning (follow these steps before outputting JSON)

Step 1 — Leaf check:
  Is this a PURE LEAF implementation? Criteria: adds/changes a single function with NO API
  or contract changes, affects at most 1–2 files, no design decisions needed.
  Answer: YES or NO

Step 2 — Stage necessity:
  Which stages are GENUINELY needed?
  - research: only if external knowledge or API discovery is needed
  - design: only if architecture or interface decisions must be made first
  - plan: almost always needed before implementation
  - implement: needed if any code changes
  - test: needed if any code changes
  - review: needed if non-trivial logic or potential regressions
  - cross_review: needed if cross-cutting concerns or system boundaries

Step 3 — Scope uncertainty:
  Without explicit file paths, how certain are you?
  If vague or covers multiple systems, confidence MUST be < 0.5.

Step 4 — Decision:
  Pure-leaf (YES in Step 1) + clear description → confidence ≥ 0.82.
  Ambiguous or multi-system → confidence < 0.60.

## Output (JSON block only — no text before or after)
```json
{{
  "isolation": <one of {list(ISOLATION_LEVELS)}>,
  "required_stages": [<subset of [{stage_list}] in execution order>],
  "review_depth": <"none" | "standard" | "deep">,
  "confidence": <float 0.0–1.0>,
  "reason": "<1-2 sentences summarizing your conclusion>"
}}
```

## Additional rules
- Pure leaf (YES in Step 1): required_stages = [{light_list}] only.
- Multi-system or design-heavy: include design/review/cross_review as needed.
"""
```

### §4.2 `_build_prompt` CoT화

동일한 Step 1~4 + JSON + Additional rules 구조 추가.  
단, scope 파일이 있으므로 Step 1 내 "files section"에서 단서 활용.  
Tier hint advisory 라인 유지.

### §4.3 상수 변경

```python
# before
_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD: float = 0.85

# after
_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD: float = 0.82
```

---

## §5 테스트 명세

### §5.1 변경 대상 테스트

`tests/test_right_sized_router.py`:
- `_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD` 상수를 0.82로 참조하는 assertion 업데이트
- `is_light()` 임계 검증 케이스: conf=0.82 → True, conf=0.81 → False (scope_uncertain marker 있을 때)
- 기존 `test_empty_scope_*` 케이스 회귀 확인

`tests/test_rse_router_decoupling.py`:
- 함수명 `test_is_light_with_marker_uses_085_threshold` → `test_is_light_with_marker_uses_082_threshold`
- docstring·인라인 주석의 "0.85" → "0.82" 갱신 (미래 유지보수자 오인 방지)

### §5.2 추가 테스트 불필요 케이스

CoT 프롬프트 문자열 자체는 유닛 테스트 대상 아님 (LLM 응답은 monkeypatch 처리).  
프롬프트 포맷 오류는 `_validate_raw` → `_fallback_decision` 기존 경로가 방어.

---

## §6 블루프린트 업데이트

- §3 `right_sized_router` 서브섹션: `_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD` 값 갱신
- §12 변경 이력: 커밋 + 날짜

---

## §7 구현 순서

1. `core/right_sized_router.py`:
   - `_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD` 0.85 → 0.82
   - `_build_empty_scope_prompt` CoT화
   - `_build_prompt` CoT화
2. `tests/test_right_sized_router.py`:
   - 임계 0.82 기준 테스트 업데이트
3. Blueprint §3/§12 갱신 (같은 커밋)
4. 3-Tier: af-critic → af-cross-review → af-test-runner
