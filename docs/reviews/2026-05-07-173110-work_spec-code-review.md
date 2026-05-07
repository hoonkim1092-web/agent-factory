# Code Review: work_spec

> Source: core/research/work_spec.py
> Date: 2026-05-07 17:31
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

Critic는 diff 없음으로 PASS. Cross Review가 기존 코드를 탐색하여 High 결함 1건을 포함한 3건을 발견했다. diff 부재는 "변경 없음"이지 "결함 없음"이 아니므로 Cross Review 결과를 채택한다.

---

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [High] LLM envelope dict → `_extract_json()` 직접 전달로 silent 빈 WorkSpec 반환
- **Critic**: "not flagged (no diff)"
- **Cross**: `execute_requirement_prompt()`가 `{"ok": True, "text": "..."}` dict를 반환하는데, `_extract_json()`은 string을 기대한다. `except Exception`이 `re.search()` 오류를 삼키고 빈 `WorkSpec`을 반환한다.
- **Judgment**: 강한 증거. `core/requirement_llm.py:272-279`에서 envelope 반환 확인. `core/researcher.py:526-529`, `core/manager.py:146-149`는 모두 `.get("text")`로 먼저 unwrap하는 반면 이 코드만 누락. 오류가 조용히 삼켜져 데이터 손실과 동일한 효과.
- **Action Required**:
  ```python
  result = execute_requirement_prompt(prompt)
  if not result.get("ok"):
      raise RuntimeError("work_spec_llm_unavailable")
  data = safe_json_load(result.get("text") or "{}")
  ```

#### 2. [ACCEPT] [Medium] LLM이 list 대신 scalar string 반환 시 문자 단위 순회
- **Critic**: "not flagged (no diff)"
- **Cross**: `capabilities: "multiplayer"` 같은 scalar 반환 시 `["m", "u", "l", ...]`로 분해되어 `QualityContractBuilder`가 문자별 YAML pack을 조회한다.
- **Judgment**: `work_spec.py:66-68`과 `quality_contract.py:98-103` 코드 흐름상 실재하는 경로. LLM 출력은 비결정적이므로 방어적 처리 필요.
- **Action Required**: list 타입 강제 coercion 추가:
  ```python
  caps = spec.get("capabilities", [])
  if isinstance(caps, str):
      caps = [caps]
  ```

#### 3. [ACCEPT] [Low] `WorkSpecExtractor.extract()` 직접 호출 테스트 없음
- **Critic**: "not flagged (no diff)"
- **Cross**: 기존 테스트는 `WorkSpec` 수동 생성 → `QualityContractBuilder` 경로만 검증. `WorkSpecExtractor`를 통한 end-to-end 경로가 테스트되지 않아 Finding 1·2가 회귀 탐지 없이 잠복한다.
- **Judgment**: Finding 1이 `except Exception` 아래 숨어 있는 이유가 이 테스트 갭 때문이기도 함.
- **Action Required**: `tests/test_work_spec.py` 추가 — envelope 정상, `ok=False`, 빈 JSON, scalar capabilities, domain hint 보존 케이스 포함.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | LLM envelope unwrap 누락 → silent 빈 WorkSpec | High | ACCEPT | Cross |
| 2 | scalar capabilities → 문자 단위 순회 | Medium | ACCEPT | Cross |
| 3 | WorkSpecExtractor 테스트 갭 | Low | ACCEPT | Cross |
| — | Public export 호환성 우려 | — | REJECT | Cross (자체 기각) |

---

### Recommendations

- **즉시**: Finding 1 — `execute_requirement_prompt()` 결과를 `_extract_json()` 전에 `.get("text")`로 unwrap하고 `ok=False` 시 명시적 예외 발생
- **즉시**: Finding 2 — capabilities 필드에 `isinstance(caps, str)` 가드 추가
- **단기**: Finding 3 — `tests/test_work_spec.py` 신규 작성, Finding 1·2 회귀 케이스 포함
- Finding 1·2 픽스 후 af-test-runner로 기존 30개 테스트 통과 여부 재확인