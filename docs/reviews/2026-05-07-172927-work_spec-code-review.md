# Code Review: work_spec

> Source: core/research/work_spec.py
> Date: 2026-05-07 17:29
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

Cross Review가 Strong evidence 2건을 제시. Critic은 diff 미제공으로 N/A. 규칙 2(단독 flagging + 강한 증거)에 따라 둘 다 ACCEPT.

---

### Aggregated Findings (2 total)

#### 1. [ACCEPT] [High] WorkSpecExtractor가 LLM envelope dict를 string으로 넘겨 silent empty spec 반환

- **Critic**: "not flagged (diff 미제공)"
- **Cross**: "`execute_requirement_prompt()` 반환값이 `{"ok": True, "text": ...}` dict인데, `_extract_json()`에 dict 그대로 전달 → exception → 빈 `WorkSpec` silent return. `researcher.py:611` `QualityContractBuilder.build()`까지 전파돼 artifact/capability pack 전체 스킵, base/domain-hint fallback만 남음."
- **Judgment**: `core/requirement_llm.py:272` 반환 타입과 `work_spec.py:61` 호출 지점 불일치. 빈 spec이 상위 컨트랙트 빌드를 조용히 무력화하므로 High. diff 없음에도 Cross가 라인 번호와 전파 경로까지 추적했고 반박 근거가 없다.
- **Action Required**: `work_spec.py:61` 부근에서 envelope 언팩 처리:
  ```python
  result = execute_requirement_prompt(prompt)
  if not result.get("ok"):
      raise RuntimeError("work_spec_llm_unavailable")
  data = safe_json_load(result.get("text") or "{}")
  ```
  + `execute_requirement_prompt`를 `{"ok": True, "text": valid_json}`으로 패치하는 단위 테스트 추가.

#### 2. [ACCEPT] [Medium] LLM 반환 pack key가 정규화 없이 파일명으로 직행 — lookup miss

- **Critic**: "not flagged (diff 미제공)"
- **Cross**: "`artifact_type`/`domain`/`capabilities`/`risk_areas`는 `str(...).strip()`만 적용. `quality_contract.py:91,99,113`에서 그대로 팩 파일명 조회 → `"real-time"` 같은 LLM 출력이 `realtime.yaml`을 찾지 못함. `safe_id()`는 이미 `core/utils.py:56` 존재."
- **Judgment**: 실제 팩 미스로 이어지는 경계 정규화 결함. 기존 테스트는 이미 정규화된 값으로 `WorkSpec`을 직접 생성하므로 이 경계가 완전히 미커버. Cross 증거 명확.
- **Action Required**: `WorkSpecExtractor`에서 팩 ID를 `safe_id()` (혹은 동등 로컬 헬퍼)로 정규화한 뒤 `WorkSpec`에 넣기. `"real-time"` → `"realtime"` 류 케이스 테스트 추가. 빈 문자열 보존 처리 포함.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | WorkSpecExtractor envelope 파싱 오류 → silent empty spec | High | ACCEPT | Cross |
| 2 | LLM pack key 미정규화 → 파일명 lookup miss | Medium | ACCEPT | Cross |

---

### Recommendations

- Finding 1 우선 수정: envelope 언팩은 1~2줄 변경이지만 quality contract 전체 동작에 직결. 테스트 없으면 재발 가능성 높음.
- Finding 2는 Finding 1 수정 직후 같은 PR에 묶는 것이 적절 — 같은 `WorkSpecExtractor` 경계이므로 컨텍스트 중복 없음.
- Critic에게 실제 diff를 전달하는 파이프라인 점검 필요 — `(no diff for core/research/work_spec.py)` 는 리뷰 게이트의 half-coverage를 의미함.