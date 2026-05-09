# Code Review: spec_generator

> Source: core/spec_generator.py
> Date: 2026-05-06 19:39
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

두 리뷰어가 독립적으로 확인한 silent exception swallowing이 Cross Review의 "placeholder 영구화 + 존재 여부만 체크하는 gate" 증거와 결합되어 Critical 수준의 데이터 무결성 문제를 형성한다. 한번 placeholder 파일이 저장되면 수동 삭제 없이는 복구 불가능하며, 파이프라인은 이를 정상 명세로 간주한다.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [Critical] Placeholder specs persist silently and block all future regeneration

- **Critic**: "`_call_llm`의 `except Exception: pass`가 모든 예외를 삼키고 `(spec generation unavailable)` placeholder를 반환. caller가 성공/실패를 구분할 방법 없음."
- **Cross**: "동일 문제 확인 + 추가 증거: `core/project_pipeline.py:847-848`이 `generate()` 반환값을 그대로 파일로 저장하고, `_verify_domain_spec()`은 파일 존재 여부만 체크함. 결과: placeholder 파일이 한번 저장되면 이후 실행에서 재생성을 건너뜀."
- **Judgment**: Critic Finding 1 + Cross Finding 3이 동일 결함. Cross가 추가한 "영구화" 경로가 단순 High를 Critical로 격상시킨다. 실패 → placeholder 저장 → gate 통과 → 이후 모든 실행이 같은 파일을 정상으로 간주하는 단방향 데이터 오염 사이클이다.
- **Action Required**:
  1. `_call_llm`의 `except Exception` 블록에 `logger.warning` 추가 + 실패 키 누락(또는 `None` 값) 처리
  2. `_verify_domain_spec()`이 파일 내용에서 `(spec generation unavailable)` 포함 여부를 검사하도록 수정
  3. 또는 실패 spec을 파일로 저장하지 않음 (generate() 반환 전 필터링)

---

#### 2. [ACCEPT] [High] One partial spec file satisfies the entire domain-spec gate

- **Critic**: "not flagged"
- **Cross**: "`_verify_domain_spec()`이 `docs/specs/<slug>-*.md` 파일이 하나라도 있으면 true 반환. `SPEC_FILENAMES`에 정의된 5개 파일 전체 존재를 검증하지 않음. 테스트(`test_research_system_regression.py:375-377`)도 1개 파일로 gate 통과를 단언하여 불완전 커버리지를 고정함."
- **Judgment**: Cross만 플래그했지만 코드 라인 증거와 테스트 증거가 명확하다. Finding 1과 결합 시 시스템이 5개 중 1개만 생성(나머지 4개 placeholder)해도 gate 통과가 가능하다.
- **Action Required**: `_verify_domain_spec()`을 `SPEC_FILENAMES.values()` 전체 파일 존재 + 내용 비어있지 않음으로 강화. 1개만 있을 때 `False` 반환하는 회귀 테스트 추가.

---

#### 3. [ACCEPT] [Medium] Generated specs not consumed by downstream work-item generation

- **Critic**: "not flagged"
- **Cross**: "`SpecGenerator.generate()` 결과가 `docs/specs`에 저장되지만, `generate_work_items()`는 `project_brief`, `role_plan`, `task_board`만 사용(`core/work_item_generator.py:535, 575, 648`). `docs/specs`를 역으로 읽는 경로 없음."
- **Judgment**: Cross 단독이지만 코드 경로 증거가 구체적이다. 명세를 생성해도 다운스트림 품질에 영향이 없는 현재 구조는 dead code에 준한다.
- **Action Required**: `generate_work_items()`에 `domain_specs` 파라미터 추가 후 프롬프트에 포함하거나, `project_brief["domain_specs"]` 경유로 전달. 또는 설계 의도(파일 아카이브 용도)라면 주석으로 명기.

---

#### 4. [ACCEPT] [Medium] `core/spec_generator.py` not registered in `af.spec` hiddenimports

- **Critic**: "CLAUDE.md 필수 규칙 위반. frozen 빌드에서 `ModuleNotFoundError: No module named 'core.spec_generator'` 런타임 크래시 발생."
- **Cross**: "not flagged"
- **Judgment**: Critic 단독이지만 CLAUDE.md 규칙이 명시적이고("새 `core/*.py` 파일은 `af.spec` `hiddenimports`에 반드시 추가") 영향이 명확하다.
- **Action Required**: `af.spec` hiddenimports 목록에 `"core.spec_generator"` 추가.

---

#### 5. [ACCEPT] [Medium] `task_input` has no length limit — token overflow silently absorbed

- **Critic**: "`original_request`가 전체 대화 기록일 경우 5개 LLM 프롬프트에 전부 삽입. token limit 초과 예외는 Finding 1의 `except Exception: pass`에 흡수되어 5개 명세 전부 placeholder."
- **Cross**: "not flagged"
- **Judgment**: Finding 1이 수정되더라도 token overflow 자체는 별도 방어가 필요하다. Finding 1과 독립적 결함이며, `task_input`이 무제한으로 커지는 경로는 실제로 존재한다.
- **Action Required**: `task_input = str(...)[:2000]` 상한 적용 (또는 토큰 수 추정 체크).

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Placeholder specs persist + gate passes on existence only | Critical | ACCEPT | Both |
| 2 | Partial spec satisfies domain-spec gate | High | ACCEPT | Cross |
| 3 | Specs not consumed downstream | Medium | ACCEPT | Cross |
| 4 | `core/spec_generator.py` missing from `af.spec` hiddenimports | Medium | ACCEPT | Critic |
| 5 | `task_input` length unbounded | Medium | ACCEPT | Critic |

---

### Recommendations

- **즉시 수정 (BLOCK 해제 조건)**: Finding 1 — `_call_llm` 예외 로깅 + 실패 spec 저장 방지 또는 `_verify_domain_spec` 내용 검사 추가
- **같은 PR**: Finding 2 — `_verify_domain_spec` 전체 파일명 검증 + 회귀 테스트
- **같은 PR**: Finding 4 — `af.spec` hiddenimports 등록
- **후속 PR 가능**: Finding 3 — `domain_specs` 다운스트림 연결 (설계 변경 동반)
- **후속 PR 가능**: Finding 5 — `task_input` 상한 (`[:2000]`)